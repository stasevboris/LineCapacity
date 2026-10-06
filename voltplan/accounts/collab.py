from __future__ import annotations

import secrets
import time
from pathlib import Path

from . import tiers
from .projects import Projects, clean_title
from .security import Refused, normal_email
from .storage import Store
from .users import User, Users

ROLES = ("editor", "reader")
FILE_LIMIT = 5 * 1024 * 1024
BODY_LIMIT = 4000
BLOCKED = {".exe", ".bat", ".cmd", ".com", ".msi", ".msp", ".mst", ".ps1", ".psm1", ".psd1", ".vbs", ".vbe", ".js",
           ".jse", ".wsf", ".wsh", ".hta", ".scr", ".dll", ".cpl", ".ocx", ".sys", ".drv", ".jar", ".sh", ".reg",
           ".lnk", ".pif", ".inf", ".scf", ".url", ".appx", ".appxbundle", ".msix", ".msixbundle", ".application",
           ".gadget", ".chm", ".iso", ".img", ".vhd", ".vhdx"}
EXECUTABLE_HEADERS = (b"MZ", b"\x7fELF", b"#!")


def pair(one: int, two: int) -> tuple[int, int]:
    return (one, two) if one < two else (two, one)


def safe_file_name(name: str) -> str:
    base = Path(name or "").name.strip()
    cleaned = "".join(ch for ch in base if ch.isalnum() or ch in " .-_()")[:120].strip().rstrip(". ")
    if not cleaned:
        raise Refused("У файла нет имени")
    if Path(cleaned).suffix.lower() in BLOCKED:
        raise Refused("Исполняемые файлы передавать нельзя")
    return cleaned


class Collab:
    def __init__(self, store: Store, users: Users, projects: Projects) -> None:
        self.store = store
        self.users = users
        self.projects = projects

    def notify(self, user_id: int, kind: str, text: str, link: str = "") -> None:
        with self.store.writing(self.store.work) as db:
            db.execute("INSERT INTO notifications (user_id, kind, text, link, created) VALUES (?, ?, ?, ?, ?)",
                       (user_id, kind, text, link, time.time()))

    def team_role(self, team_id: int, user_id: int) -> str | None:
        row = self.store.work.execute("SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
                                      (team_id, user_id)).fetchone()
        return row["role"] if row else None

    def team(self, team_id: int) -> dict:
        row = self.store.work.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
        if row is None:
            raise Refused("Команда не найдена", 404)
        members = self.store.work.execute("SELECT user_id, role FROM team_members WHERE team_id = ?",
                                          (team_id,)).fetchall()
        names = self.users.names([m["user_id"] for m in members])
        return {"id": row["id"], "name": row["name"], "owner": row["owner_id"],
                "members": [{**names.get(m["user_id"], {"id": m["user_id"]}), "role": m["role"]} for m in members]}

    def team_name(self, team_id: int | None) -> str | None:
        if team_id is None:
            return None
        row = self.store.work.execute("SELECT name FROM teams WHERE id = ?", (team_id,)).fetchone()
        return row["name"] if row else None

    def create_team(self, user: User, name: str) -> dict:
        tiers.require(user, "teams")
        title = clean_title(name, "Название команды")
        with self.store.writing(self.store.work) as db:
            team_id = db.execute("INSERT INTO teams (name, owner_id, created) VALUES (?, ?, ?)",
                                 (title, user.id, time.time())).lastrowid
            db.execute("INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'owner')", (team_id, user.id))
        self.store.audit(user.id, "команда создана", title)
        return self.team(team_id)

    def teams(self, user: User) -> list[dict]:
        rows = self.store.work.execute("SELECT team_id FROM team_members WHERE user_id = ?", (user.id,)).fetchall()
        return [self.team(row["team_id"]) for row in rows]

    def require_owner(self, user: User, team_id: int) -> None:
        team = self.team(team_id)
        if team["owner"] != user.id:
            raise Refused("Это может сделать только владелец команды", 403)

    def set_role(self, user: User, team_id: int, member: int, role: str) -> dict:
        self.require_owner(user, team_id)
        if role not in ROLES:
            raise Refused("Роль: editor (редактор) или reader (читатель)")
        if member == user.id or self.team_role(team_id, member) is None:
            raise Refused("Участник не найден", 404)
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE team_members SET role = ? WHERE team_id = ? AND user_id = ?", (role, team_id, member))
        return self.team(team_id)

    def remove_member(self, user: User, team_id: int, member: int) -> dict:
        if member != user.id:
            self.require_owner(user, team_id)
        elif self.team(team_id)["owner"] == user.id:
            raise Refused("Владелец не может выйти из своей команды — её можно только распустить", 409)
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM team_members WHERE team_id = ? AND user_id = ?", (team_id, member))
        return self.team(team_id)

    def disband(self, user: User, team_id: int) -> None:
        self.require_owner(user, team_id)
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM team_members WHERE team_id = ?", (team_id,))
            db.execute("DELETE FROM project_shares WHERE team_id = ?", (team_id,))
            db.execute("UPDATE invitations SET status = 'cancelled' WHERE team_id = ? AND status = 'waiting'",
                       (team_id,))
            db.execute("DELETE FROM teams WHERE id = ?", (team_id,))

    def invite(self, user: User, email: str, team_id: int | None = None, role: str = "reader") -> dict:
        address = normal_email(email)
        if address == user.email:
            raise Refused("Нельзя пригласить самого себя")
        target = self.users.find(address)
        if team_id is not None:
            self.require_owner(user, team_id)
            if role not in ROLES:
                raise Refused("Роль: editor (редактор) или reader (читатель)")
            if target and self.team_role(team_id, target.id):
                raise Refused("Этот пользователь уже в команде", 409)
        elif target and self.are_friends(user.id, target.id):
            raise Refused("Этот пользователь уже у вас в друзьях", 409)
        waiting = self.store.work.execute(
            "SELECT 1 FROM invitations WHERE from_user = ? AND to_email = ? AND team_id IS ? AND status = 'waiting'",
            (user.id, address, team_id)).fetchone()
        if waiting:
            raise Refused("Такое приглашение уже отправлено и ждёт ответа", 409)
        with self.store.writing(self.store.work) as db:
            invitation_id = db.execute(
                "INSERT INTO invitations (from_user, to_email, team_id, role, created) VALUES (?, ?, ?, ?, ?)",
                (user.id, address, team_id, role, time.time())).lastrowid
        if target:
            what = f"в команду «{self.team(team_id)['name']}»" if team_id else "в друзья"
            self.notify(target.id, "invitation", f"{user.name} приглашает вас {what}", "/collab#invitations")
        return self.invitation(invitation_id)

    def invitation(self, invitation_id: int) -> dict:
        row = self.store.work.execute("SELECT * FROM invitations WHERE id = ?", (invitation_id,)).fetchone()
        if row is None:
            raise Refused("Приглашение не найдено", 404)
        sender = self.users.names([row["from_user"]]).get(row["from_user"])
        team = self.team_name(row["team_id"])
        return {"id": row["id"], "from": sender, "to": row["to_email"],
                "team": team, "team_id": row["team_id"], "role": row["role"], "status": row["status"],
                "created": row["created"]}

    def invitations(self, user: User) -> dict:
        incoming = self.store.work.execute("SELECT id FROM invitations WHERE to_email = ? ORDER BY created DESC",
                                           (user.email,)).fetchall()
        outgoing = self.store.work.execute("SELECT id FROM invitations WHERE from_user = ? ORDER BY created DESC",
                                           (user.id,)).fetchall()
        return {"incoming": [self.invitation(row["id"]) for row in incoming],
                "outgoing": [self.invitation(row["id"]) for row in outgoing]}

    def answer(self, user: User, invitation_id: int, accept: bool) -> dict:
        invitation = self.invitation(invitation_id)
        if invitation["to"] != user.email:
            raise Refused("Приглашение не найдено", 404)
        if invitation["status"] != "waiting":
            raise Refused("На приглашение уже ответили", 409)
        if invitation["from"] is None or (invitation["team_id"] and invitation["team"] is None):
            raise Refused("Приглашение больше не действует", 409)
        sender = invitation["from"]["id"]
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE invitations SET status = ? WHERE id = ?",
                       ("accepted" if accept else "declined", invitation_id))
            if accept and invitation["team_id"]:
                db.execute("INSERT OR REPLACE INTO team_members (team_id, user_id, role) VALUES (?, ?, ?)",
                           (invitation["team_id"], user.id, invitation["role"]))
            if accept:
                db.execute("INSERT OR IGNORE INTO friends (one, two, created) VALUES (?, ?, ?)",
                           (*pair(sender, user.id), time.time()))
        verdict = "принял(а)" if accept else "отклонил(а)"
        self.notify(sender, "answer", f"{user.name} {verdict} ваше приглашение", "/collab#invitations")
        return self.invitation(invitation_id)

    def friends(self, user: User) -> list[dict]:
        rows = self.store.work.execute("SELECT one, two FROM friends WHERE one = ? OR two = ?",
                                       (user.id, user.id)).fetchall()
        others = [row["two"] if row["one"] == user.id else row["one"] for row in rows]
        names = self.users.names(others)
        return [names[other] for other in others if other in names]

    def unfriend(self, user: User, other: int) -> None:
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM friends WHERE one = ? AND two = ?", pair(user.id, other))

    def are_friends(self, one: int, two: int) -> bool:
        return self.store.work.execute("SELECT 1 FROM friends WHERE one = ? AND two = ?",
                                       pair(one, two)).fetchone() is not None

    def share(self, user: User, project_id: int, team_id: int) -> dict:
        self.projects.require(user, project_id, "owner")
        if self.team_role(team_id, user.id) is None:
            raise Refused("Открыть проект можно только своей команде", 403)
        with self.store.writing(self.store.work) as db:
            db.execute("INSERT OR IGNORE INTO project_shares (project_id, team_id) VALUES (?, ?)",
                       (project_id, team_id))
        name = self.projects.get(user, project_id)["name"]
        for member in self.team(team_id)["members"]:
            if member["id"] != user.id:
                self.notify(member["id"], "share", f"Команде открыт проект «{name}»", f"/app?project={project_id}")
        return self.shares(user, project_id)

    def unshare(self, user: User, project_id: int, team_id: int) -> dict:
        self.projects.require(user, project_id, "owner")
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM project_shares WHERE project_id = ? AND team_id = ?", (project_id, team_id))
        return self.shares(user, project_id)

    def shares(self, user: User, project_id: int) -> dict:
        self.projects.require(user, project_id)
        rows = self.store.work.execute("SELECT team_id FROM project_shares WHERE project_id = ?",
                                       (project_id,)).fetchall()
        return {"project": project_id, "teams": [self.team(row["team_id"]) for row in rows]}

    def _can_write(self, user: User, to_user: int | None, team_id: int | None) -> None:
        if (to_user is None) == (team_id is None):
            raise Refused("Укажите получателя: друга или команду")
        if to_user is not None and not self.are_friends(user.id, to_user):
            raise Refused("Писать можно только друзьям", 403)
        if team_id is not None and self.team_role(team_id, user.id) is None:
            raise Refused("Писать в команду могут только её участники", 403)

    def send(self, user: User, body: str, to_user: int | None = None, team_id: int | None = None,
             file_name: str | None = None, content: bytes | None = None) -> dict:
        self._can_write(user, to_user, team_id)
        text = (body or "").strip()
        if len(text) > BODY_LIMIT:
            raise Refused(f"Сообщение должно быть не длиннее {BODY_LIMIT} знаков")
        stored = None
        name = None
        if content is not None:
            name = safe_file_name(file_name or "")
            if content.startswith(EXECUTABLE_HEADERS):
                raise Refused("Исполняемые файлы передавать нельзя")
            if len(content) > FILE_LIMIT:
                raise Refused("Файл больше 5 МБ", 413)
            stored = f"{secrets.token_hex(12)}{Path(name).suffix.lower()}"
            (self.store.files / stored).write_bytes(content)
        if not text and stored is None:
            raise Refused("Пустое сообщение")
        with self.store.writing(self.store.work) as db:
            message_id = db.execute(
                "INSERT INTO messages (from_user, to_user, team_id, body, file_name, file_path, created) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", (user.id, to_user, team_id, text, name, stored, time.time())).lastrowid
        if to_user:
            receivers, text = [to_user], f"{user.name} пишет вам"
        else:
            team = self.team(team_id)
            receivers = [m["id"] for m in team["members"] if m["id"] != user.id]
            text = f"{user.name} пишет в команду «{team['name']}»"
        for receiver in receivers:
            self.notify(receiver, "message", text, "/collab#chat")
        return self.message(message_id)

    def message(self, message_id: int) -> dict:
        row = self.store.work.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        sender = self.users.names([row["from_user"]]).get(row["from_user"])
        return {"id": row["id"], "from": sender, "to_user": row["to_user"], "team_id": row["team_id"],
                "body": row["body"], "file": row["file_name"], "created": row["created"]}

    def history(self, user: User, with_user: int | None = None, team_id: int | None = None) -> list[dict]:
        if team_id is not None:
            if self.team_role(team_id, user.id) is None:
                raise Refused("Переписка команды доступна только её участникам", 403)
            rows = self.store.work.execute("SELECT id FROM messages WHERE team_id = ? ORDER BY id", (team_id,))
        elif with_user is not None:
            rows = self.store.work.execute(
                "SELECT id FROM messages WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?) "
                "ORDER BY id", (user.id, with_user, with_user, user.id))
        else:
            raise Refused("Укажите собеседника или команду")
        return [self.message(row["id"]) for row in rows.fetchall()]

    def file(self, user: User, message_id: int) -> tuple[str, bytes]:
        row = self.store.work.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if row is None or row["file_path"] is None:
            raise Refused("Файл не найден", 404)
        allowed = (row["to_user"] == user.id or row["from_user"] == user.id
                   or (row["team_id"] is not None and self.team_role(row["team_id"], user.id) is not None))
        if not allowed:
            raise Refused("Файл не найден", 404)
        return row["file_name"], (self.store.files / row["file_path"]).read_bytes()

    def notifications(self, user: User) -> dict:
        rows = self.store.work.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 100", (user.id,)).fetchall()
        items = [{"id": r["id"], "kind": r["kind"], "text": r["text"], "link": r["link"], "seen": bool(r["seen"]),
                  "created": r["created"]} for r in rows]
        return {"unseen": sum(1 for item in items if not item["seen"]), "items": items}

    def mark_seen(self, user: User, ids: list[int] | None = None) -> dict:
        with self.store.writing(self.store.work) as db:
            if ids:
                db.executemany("UPDATE notifications SET seen = 1 WHERE user_id = ? AND id = ?",
                               [(user.id, item) for item in ids])
            else:
                db.execute("UPDATE notifications SET seen = 1 WHERE user_id = ?", (user.id,))
        return self.notifications(user)
