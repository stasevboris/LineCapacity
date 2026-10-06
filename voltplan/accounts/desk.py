from __future__ import annotations

import time

from .security import Refused
from .storage import Store
from .users import User, Users

TEXT_LIMIT = 500


class Desk:
    def __init__(self, store: Store, users: Users, notify) -> None:
        self.store = store
        self.users = users
        self.notify = notify

    @staticmethod
    def require(user: User) -> None:
        if not user.is_admin:
            raise Refused("Раздел доступен только администратору", 403)

    def people(self, admin: User, query: str = "") -> list[dict]:
        self.require(admin)
        wanted = query.strip().lower()
        rows = self.store.credentials.execute("SELECT id, email FROM credentials ORDER BY id").fetchall()
        found = []
        for row in rows:
            profile = self.store.work.execute("SELECT * FROM profiles WHERE user_id = ?", (row["id"],)).fetchone()
            if profile is None:
                continue
            if wanted and wanted not in row["email"] and wanted not in profile["name"].lower():
                continue
            user = self.users.get(row["id"])
            projects = self.store.work.execute("SELECT COUNT(*) FROM projects WHERE owner_id = ?",
                                               (row["id"],)).fetchone()[0]
            found.append({**user.public(), "stored_tier": profile["tier"], "created": profile["created"],
                          "last_login": profile["last_login"], "projects": projects})
        return found

    def set_tier(self, admin: User, user_id: int, tier: str, until: float | None) -> dict:
        self.require(admin)
        target = self.users.get(user_id)
        if target is None:
            raise Refused("Пользователь не найден", 404)
        if tier != "demo" and until is not None and until <= time.time():
            raise Refused("Срок действия тарифа должен быть в будущем")
        changed = self.users.set_tier(user_id, tier, until)
        self.store.audit(admin.id, "тариф изменён администратором", f"{target.email}: {tier}")
        self.notify(user_id, "tier", f"Администратор изменил ваш тариф: {tier}", "/account#payments")
        return changed.public()

    def set_admin(self, admin: User, user_id: int, flag: bool) -> dict:
        self.require(admin)
        if user_id == admin.id and not flag:
            raise Refused("Нельзя снять права администратора с самого себя", 409)
        if self.users.get(user_id) is None:
            raise Refused("Пользователь не найден", 404)
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE profiles SET is_admin = ? WHERE user_id = ?", (int(flag), user_id))
        target = self.users.get(user_id)
        self.store.audit(admin.id, "права администратора " + ("выданы" if flag else "сняты"), target.email)
        return target.public()

    def journal(self, admin: User, query: str = "", limit: int = 200) -> list[dict]:
        self.require(admin)
        rows = self.store.work.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?",
                                       (min(limit, 1000),)).fetchall()
        names = self.users.names([row["user_id"] for row in rows if row["user_id"]])
        wanted = query.strip().lower()
        found = []
        for row in rows:
            who = names.get(row["user_id"], {})
            record = {"id": row["id"], "user": who.get("email", ""), "action": row["action"],
                      "details": row["details"], "created": row["created"]}
            text = " ".join(str(value) for value in record.values()).lower()
            if not wanted or wanted in text:
                found.append(record)
        return found

    def broadcast(self, admin: User, text: str, user_id: int | None = None) -> dict:
        self.require(admin)
        message = " ".join((text or "").split())
        if not message:
            raise Refused("Текст уведомления не может быть пустым")
        if len(message) > TEXT_LIMIT:
            raise Refused(f"Уведомление должно быть не длиннее {TEXT_LIMIT} знаков")
        if user_id is not None:
            if self.users.get(user_id) is None:
                raise Refused("Пользователь не найден", 404)
            targets = [user_id]
        else:
            targets = [row["user_id"] for row in self.store.work.execute("SELECT user_id FROM profiles").fetchall()]
        for target in targets:
            self.notify(target, "admin", message, "")
        self.store.audit(admin.id, "уведомление разослано", f"получателей: {len(targets)}")
        return {"sent": len(targets)}

    def payments(self, admin: User) -> list[dict]:
        self.require(admin)
        rows = self.store.work.execute("SELECT * FROM payments ORDER BY created DESC LIMIT 300").fetchall()
        names = self.users.names([row["user_id"] for row in rows])
        return [{"id": row["id"], "user": names.get(row["user_id"], {}).get("email", ""), "tier": row["tier"],
                 "amount_usd": row["amount_cents"] / 100, "provider": row["provider"], "status": row["status"],
                 "card": row["pan_masked"], "created": row["created"]} for row in rows]
