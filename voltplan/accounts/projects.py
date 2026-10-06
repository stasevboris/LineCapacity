from __future__ import annotations

import json
import time

from ..calc import settings as calc_settings
from ..scheme.editor import EditError
from ..scheme.model import Scheme
from . import tiers
from .security import Refused
from .storage import Store
from .users import User, Users

NAME_MAX = 120
RANK = {"reader": 1, "editor": 2, "owner": 3}
NOT_FOUND = "Проект не найден или нет доступа"


def clean_title(name: str, what: str = "Название") -> str:
    value = " ".join((name or "").split())
    if not value:
        raise Refused(f"{what} не может быть пустым")
    if len(value) > NAME_MAX:
        raise Refused(f"{what} должно быть не длиннее {NAME_MAX} знаков")
    return value


def scheme_text(scheme: Scheme | dict | None) -> str:
    if scheme is None:
        return ""
    model = scheme if isinstance(scheme, Scheme) else Scheme.model_validate(scheme)
    return model.model_dump_json()


class Projects:
    def __init__(self, store: Store, users: Users) -> None:
        self.store = store
        self.users = users

    def owner(self, project_id: int) -> User:
        row = self.store.work.execute("SELECT owner_id FROM projects WHERE id = ?", (project_id,)).fetchone()
        owner = self.users.get(row["owner_id"]) if row else None
        if owner is None:
            raise Refused(NOT_FOUND, 404)
        return owner

    def role(self, user_id: int, project_id: int) -> str | None:
        project = self.store.work.execute("SELECT owner_id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if project is None:
            return None
        if project["owner_id"] == user_id:
            return "owner"
        rows = self.store.work.execute(
            "SELECT tm.role FROM project_shares ps JOIN team_members tm ON tm.team_id = ps.team_id "
            "WHERE ps.project_id = ? AND tm.user_id = ?", (project_id, user_id)).fetchall()
        roles = ["editor" if row["role"] in ("owner", "editor") else "reader" for row in rows]
        return max(roles, key=RANK.get) if roles else None

    def require(self, user: User, project_id: int, needed: str = "reader") -> str:
        role = self.role(user.id, project_id)
        if role is None:
            raise Refused(NOT_FOUND, 404)
        if RANK[role] < RANK[needed]:
            words = {"editor": "Сохранять изменения может только владелец или редактор",
                     "owner": "Это действие доступно только владельцу проекта"}
            raise Refused(words[needed], 403)
        return role

    def count_own(self, user: User) -> int:
        return self.store.work.execute("SELECT COUNT(*) FROM projects WHERE owner_id = ? AND archived = 0",
                                       (user.id,)).fetchone()[0]

    def check_room(self, user: User) -> None:
        tier = tiers.effective(user)
        if self.count_own(user) >= tier.projects:
            raise Refused(f"В тарифе «{tier.title}» можно вести не больше {tier.projects} проектов. Уберите лишние "
                          "в архив или смените тариф.", 403)

    def create(self, user: User, name: str, scheme: Scheme | dict | None = None) -> dict:
        title = clean_title(name)
        text = scheme_text(scheme)
        fit(user, text)
        now = time.time()
        with self.store.writing(self.store.work) as db:
            self.check_room(user)
            project_id = db.execute("INSERT INTO projects (owner_id, name, created, updated) VALUES (?, ?, ?, ?)",
                                    (user.id, title, now, now)).lastrowid
            db.execute("INSERT INTO variants (project_id, name, is_main, scheme, created, updated) "
                       "VALUES (?, 'Основной', 1, ?, ?, ?)", (project_id, text, now, now))
        self.store.audit(user.id, "проект создан", title)
        return self.get(user, project_id)

    def summary(self, row, role: str) -> dict:
        owner = self.store.credentials.execute("SELECT email FROM credentials WHERE id = ?",
                                               (row["owner_id"],)).fetchone()
        variants = self.store.work.execute("SELECT COUNT(*) FROM variants WHERE project_id = ?",
                                           (row["id"],)).fetchone()[0]
        return {"id": row["id"], "name": row["name"], "role": role, "archived": bool(row["archived"]),
                "owner": owner["email"] if owner else "", "variants": variants, "created": row["created"],
                "updated": row["updated"]}

    def listing(self, user: User, archived: bool = False) -> list[dict]:
        rows = self.store.work.execute(
            "SELECT DISTINCT p.* FROM projects p LEFT JOIN project_shares ps ON ps.project_id = p.id "
            "LEFT JOIN team_members tm ON tm.team_id = ps.team_id "
            "WHERE (p.owner_id = ? OR tm.user_id = ?) AND p.archived = ? ORDER BY p.updated DESC",
            (user.id, user.id, int(archived))).fetchall()
        return [self.summary(row, self.role(user.id, row["id"])) for row in rows]

    def get(self, user: User, project_id: int) -> dict:
        role = self.require(user, project_id)
        row = self.store.work.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        data = self.summary(row, role)
        data["variants"] = self.variants(project_id)
        data["settings"] = json.loads(row["settings"] or "{}")
        return data

    def variants(self, project_id: int) -> list[dict]:
        rows = self.store.work.execute(
            "SELECT id, name, is_main, updated, scheme = '' AS empty FROM variants WHERE project_id = ? "
            "ORDER BY is_main DESC, id",
            (project_id,)).fetchall()
        return [{"id": row["id"], "name": row["name"], "main": bool(row["is_main"]), "empty": bool(row["empty"]),
                 "updated": row["updated"]} for row in rows]

    def variant_summary(self, row) -> dict:
        return {"variant": row["id"], "name": row["name"], "main": bool(row["is_main"]),
                "scheme": json.loads(row["scheme"]) if row["scheme"] else None}

    def _variant(self, project_id: int, variant_id: int | None):
        if variant_id is None:
            row = self.store.work.execute("SELECT * FROM variants WHERE project_id = ? AND is_main = 1",
                                          (project_id,)).fetchone()
        else:
            row = self.store.work.execute("SELECT * FROM variants WHERE project_id = ? AND id = ?",
                                          (project_id, variant_id)).fetchone()
        if row is None:
            raise Refused("Вариант не найден", 404)
        return row

    def scheme(self, user: User, project_id: int, variant_id: int | None = None) -> dict:
        self.require(user, project_id)
        return self.variant_summary(self._variant(project_id, variant_id))

    def save(self, user: User, project_id: int, scheme: Scheme | dict, variant_id: int | None = None) -> dict:
        self.require(user, project_id, "editor")
        row = self._variant(project_id, variant_id)
        text = scheme_text(scheme)
        fit(self.owner(project_id), text)
        now = time.time()
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE variants SET scheme = ?, updated = ? WHERE id = ?", (text, now, row["id"]))
            db.execute("UPDATE projects SET updated = ? WHERE id = ?", (now, project_id))
        return self.get(user, project_id)

    def rename(self, user: User, project_id: int, name: str) -> dict:
        self.require(user, project_id, "owner")
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE projects SET name = ?, updated = ? WHERE id = ?",
                       (clean_title(name), time.time(), project_id))
        return self.get(user, project_id)

    def archive(self, user: User, project_id: int, archived: bool) -> dict:
        self.require(user, project_id, "owner")
        with self.store.writing(self.store.work) as db:
            current = db.execute("SELECT archived FROM projects WHERE id = ?", (project_id,)).fetchone()["archived"]
            if current and not archived:
                self.check_room(user)
            db.execute("UPDATE projects SET archived = ?, updated = ? WHERE id = ?",
                       (int(archived), time.time(), project_id))
        return self.get(user, project_id)

    def delete(self, user: User, project_id: int) -> None:
        self.require(user, project_id, "owner")
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM scenarios WHERE project_id = ?", (project_id,))
            db.execute("DELETE FROM variants WHERE project_id = ?", (project_id,))
            db.execute("DELETE FROM project_shares WHERE project_id = ?", (project_id,))
            db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.store.audit(user.id, "проект удалён", str(project_id))

    def count_variants(self, project_id: int) -> int:
        return self.store.work.execute("SELECT COUNT(*) FROM variants WHERE project_id = ?",
                                       (project_id,)).fetchone()[0]

    def add_variant(self, user: User, project_id: int, name: str, source: int | None = None) -> dict:
        self.require(user, project_id, "editor")
        title = clean_title(name, "Название варианта")
        tier = tiers.effective(self.owner(project_id))
        if self.count_variants(project_id) >= tier.variants:
            raise Refused(f"В тарифе «{tier.title}» у проекта может быть не больше {tier.variants} вариантов", 403)
        base = self._variant(project_id, source)
        now = time.time()
        with self.store.writing(self.store.work) as db:
            variant_id = db.execute(
                "INSERT INTO variants (project_id, name, is_main, scheme, created, updated) VALUES (?, ?, 0, ?, ?, ?)",
                (project_id, title, base["scheme"], now, now)).lastrowid
            db.execute("UPDATE projects SET updated = ? WHERE id = ?", (now, project_id))
        return self.scheme(user, project_id, variant_id)

    def rename_variant(self, user: User, project_id: int, variant_id: int, name: str) -> dict:
        self.require(user, project_id, "editor")
        self._variant(project_id, variant_id)
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE variants SET name = ?, updated = ? WHERE id = ?",
                       (clean_title(name, "Название варианта"), time.time(), variant_id))
        return self.get(user, project_id)

    def delete_variant(self, user: User, project_id: int, variant_id: int) -> dict:
        self.require(user, project_id, "editor")
        row = self._variant(project_id, variant_id)
        if row["is_main"]:
            raise Refused("Основной вариант удалить нельзя", 409)
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM variants WHERE id = ?", (variant_id,))
        return self.get(user, project_id)

    def settings(self, user: User, project_id: int) -> dict:
        self.require(user, project_id)
        row = self.store.work.execute("SELECT settings FROM projects WHERE id = ?", (project_id,)).fetchone()
        return json.loads(row["settings"] or "{}")

    def save_settings(self, user: User, project_id: int, values: dict) -> dict:
        self.require(user, project_id, "editor")
        cleaned = checked_settings(values)
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE projects SET settings = ?, updated = ? WHERE id = ?",
                       (json.dumps(cleaned), time.time(), project_id))
        return cleaned

    def scenarios(self, user: User, project_id: int) -> list[dict]:
        self.require(user, project_id)
        rows = self.store.work.execute("SELECT * FROM scenarios WHERE project_id = ? ORDER BY id",
                                       (project_id,)).fetchall()
        return [scenario_view(row) for row in rows]

    def add_scenario(self, user: User, project_id: int, name: str, values: dict, period: int,
                     min_load: bool) -> list[dict]:
        self.require(user, project_id, "editor")
        title = clean_title(name, "Название сценария")
        if period not in (0, 1, 2):
            raise Refused("Период: 0 — лето, 1 — зима, 2 — оба")
        tier = tiers.effective(self.owner(project_id))
        if self.store.work.execute("SELECT COUNT(*) FROM scenarios WHERE project_id = ?",
                                   (project_id,)).fetchone()[0] >= tier.scenarios:
            raise Refused(f"В тарифе «{tier.title}» в проекте может быть не больше {tier.scenarios} сценариев", 403)
        with self.store.writing(self.store.work) as db:
            db.execute("INSERT INTO scenarios (project_id, name, settings, period, min_load, created) "
                       "VALUES (?, ?, ?, ?, ?, ?)",
                       (project_id, title, json.dumps(checked_settings(values)), period, int(min_load), time.time()))
        return self.scenarios(user, project_id)

    def update_scenario(self, user: User, project_id: int, scenario_id: int, name: str, values: dict, period: int,
                        min_load: bool) -> list[dict]:
        self.require(user, project_id, "editor")
        self._scenario(project_id, scenario_id)
        if period not in (0, 1, 2):
            raise Refused("Период: 0 — лето, 1 — зима, 2 — оба")
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE scenarios SET name = ?, settings = ?, period = ?, min_load = ? WHERE id = ?",
                       (clean_title(name, "Название сценария"), json.dumps(checked_settings(values)), period,
                        int(min_load), scenario_id))
        return self.scenarios(user, project_id)

    def delete_scenario(self, user: User, project_id: int, scenario_id: int) -> list[dict]:
        self.require(user, project_id, "editor")
        self._scenario(project_id, scenario_id)
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
        return self.scenarios(user, project_id)

    def _scenario(self, project_id: int, scenario_id: int):
        row = self.store.work.execute("SELECT * FROM scenarios WHERE project_id = ? AND id = ?",
                                      (project_id, scenario_id)).fetchone()
        if row is None:
            raise Refused("Сценарий не найден", 404)
        return row


def fit(owner: User, text: str) -> None:
    if not text:
        return
    data = json.loads(text)
    tiers.check_size(owner, len(data.get("poles", [])), len(data.get("consumers", [])))


def checked_settings(values: dict | None) -> dict:
    try:
        cleaned = calc_settings.clean(values)
        calc_settings.build(cleaned)
    except EditError as error:
        raise Refused(str(error)) from None
    return cleaned


def scenario_view(row) -> dict:
    return {"id": row["id"], "name": row["name"], "settings": json.loads(row["settings"] or "{}"),
            "period": row["period"], "min_load": bool(row["min_load"])}
