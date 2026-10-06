from __future__ import annotations

import secrets
import sqlite3
import time
from dataclasses import dataclass

from .security import Refused, check_new_password, new_salt, normal_email, password_hash, password_matches
from .storage import Store

FAILURES_BEFORE_PAUSE = 5
PAUSE_SECONDS = 300
NAME_MAX = 80


@dataclass
class User:
    id: int
    email: str
    name: str
    tier: str
    tier_until: float | None
    is_admin: bool
    language: str
    stamp: str
    created: float

    def public(self) -> dict:
        return {"id": self.id, "email": self.email, "name": self.name, "tier": self.tier,
                "tier_until": self.tier_until, "is_admin": self.is_admin, "language": self.language,
                "created": self.created}


def clean_name(name: str) -> str:
    value = " ".join((name or "").split())
    if len(value) > NAME_MAX:
        raise Refused(f"Имя должно быть не длиннее {NAME_MAX} знаков")
    return value


class Users:
    def __init__(self, store: Store) -> None:
        self.store = store

    def _profile(self, user_id: int) -> sqlite3.Row | None:
        return self.store.work.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()

    def get(self, user_id: int) -> User | None:
        credential = self.store.credentials.execute("SELECT id, email FROM credentials WHERE id = ?",
                                                    (user_id,)).fetchone()
        profile = self._profile(user_id)
        if credential is None or profile is None:
            return None
        tier = profile["tier"]
        if tier != "demo" and profile["tier_until"] is not None and profile["tier_until"] <= time.time():
            tier = "demo"
        return User(id=credential["id"], email=credential["email"], name=profile["name"], tier=tier,
                    tier_until=profile["tier_until"], is_admin=bool(profile["is_admin"]),
                    language=profile["language"], stamp=profile["stamp"], created=profile["created"])

    def find(self, email: str) -> User | None:
        row = self.store.credentials.execute("SELECT id FROM credentials WHERE email = ?",
                                             (email.strip().lower(),)).fetchone()
        return self.get(row["id"]) if row else None

    def register(self, email: str, password: str, name: str = "") -> User:
        address = normal_email(email)
        check_new_password(password)
        shown = clean_name(name) or address.split("@")[0]
        salt = new_salt()
        with self.store.writing(self.store.credentials) as db:
            if db.execute("SELECT 1 FROM credentials WHERE email = ?", (address,)).fetchone():
                raise Refused("Пользователь с такой почтой уже зарегистрирован", 409)
            user_id = db.execute("INSERT INTO credentials (email, salt, hash) VALUES (?, ?, ?)",
                                 (address, salt, password_hash(password, salt))).lastrowid
        with self.store.writing(self.store.work) as db:
            db.execute("INSERT INTO profiles (user_id, name, stamp, created) VALUES (?, ?, ?, ?)",
                       (user_id, shown, secrets.token_hex(8), time.time()))
        self.store.audit(user_id, "регистрация", address)
        return self.get(user_id)

    def authenticate(self, email: str, password: str) -> User:
        address = (email or "").strip().lower()
        now = time.time()
        attempt = self.store.work.execute("SELECT * FROM attempts WHERE email = ?", (address,)).fetchone()
        if attempt and attempt["blocked_until"] > now:
            wait = int(attempt["blocked_until"] - now) // 60 + 1
            raise Refused(f"Слишком много неудачных попыток. Повторите через {wait} мин.", 429)
        row = self.store.credentials.execute("SELECT * FROM credentials WHERE email = ?", (address,)).fetchone()
        if row is None or not password_matches(password or "", row["salt"], row["hash"]):
            failures = (attempt["failures"] if attempt else 0) + 1
            blocked = now + PAUSE_SECONDS if failures >= FAILURES_BEFORE_PAUSE else 0
            with self.store.writing(self.store.work) as db:
                db.execute("INSERT INTO attempts (email, failures, blocked_until) VALUES (?, ?, ?) "
                           "ON CONFLICT(email) DO UPDATE SET failures = ?, blocked_until = ?",
                           (address, 0 if blocked else failures, blocked, 0 if blocked else failures, blocked))
            raise Refused("Неверная почта или пароль", 401)
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM attempts WHERE email = ?", (address,))
            db.execute("UPDATE profiles SET last_login = ? WHERE user_id = ?", (now, row["id"]))
        return self.get(row["id"])

    def change_password(self, user: User, current: str, new: str) -> User:
        row = self.store.credentials.execute("SELECT * FROM credentials WHERE id = ?", (user.id,)).fetchone()
        if not password_matches(current or "", row["salt"], row["hash"]):
            raise Refused("Текущий пароль указан неверно", 403)
        check_new_password(new)
        salt = new_salt()
        with self.store.writing(self.store.credentials) as db:
            db.execute("UPDATE credentials SET salt = ?, hash = ? WHERE id = ?",
                       (salt, password_hash(new, salt), user.id))
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE profiles SET stamp = ? WHERE user_id = ?", (secrets.token_hex(8), user.id))
        self.store.audit(user.id, "смена пароля")
        return self.get(user.id)

    def update_profile(self, user: User, name: str | None = None, language: str | None = None) -> User:
        with self.store.writing(self.store.work) as db:
            if name is not None:
                db.execute("UPDATE profiles SET name = ? WHERE user_id = ?", (clean_name(name) or user.name, user.id))
            if language is not None:
                if language not in ("ru", "en", "zh"):
                    raise Refused("Язык интерфейса: ru, en или zh")
                db.execute("UPDATE profiles SET language = ? WHERE user_id = ?", (language, user.id))
        return self.get(user.id)

    def names(self, ids: list[int]) -> dict[int, dict]:
        result = {}
        for user_id in set(ids):
            user = self.get(user_id)
            if user:
                result[user_id] = {"id": user.id, "name": user.name, "email": user.email}
        return result

    def set_tier(self, user_id: int, tier: str, until: float | None) -> User:
        if tier not in ("demo", "pro", "max"):
            raise Refused("Тариф: demo, pro или max")
        with self.store.writing(self.store.work) as db:
            db.execute("UPDATE profiles SET tier = ?, tier_until = ? WHERE user_id = ?",
                       (tier, None if tier == "demo" else until, user_id))
        return self.get(user_id)
