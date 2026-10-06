from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path

ROUNDS = 200_000
SALT_BYTES = 16
PASSWORD_MIN = 8
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


class Refused(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def normal_email(email: str) -> str:
    value = (email or "").strip().lower()
    if len(value) > 254 or not EMAIL.match(value):
        raise Refused("Укажите адрес электронной почты, например name@example.by")
    return value


def check_new_password(password: str) -> None:
    if len(password or "") < PASSWORD_MIN:
        raise Refused(f"Пароль должен быть не короче {PASSWORD_MIN} знаков")
    if len(password) > 128:
        raise Refused("Пароль должен быть не длиннее 128 знаков")
    if not (any(ch.isalpha() for ch in password) and any(ch.isdigit() for ch in password)):
        raise Refused("Пароль должен содержать буквы и цифры")


def new_salt() -> str:
    return os.urandom(SALT_BYTES).hex()


def password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ROUNDS).hex()


def password_matches(password: str, salt: str, expected: str) -> bool:
    return hmac.compare_digest(password_hash(password, salt), expected)


def load_secret(data_dir: Path) -> bytes:
    configured = os.environ.get("VOLTPLAN_SECRET", "")
    if configured:
        return configured.encode("utf-8")
    path = data_dir / "secret.key"
    if not path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32), encoding="ascii")
    return path.read_text(encoding="ascii").strip().encode("ascii")


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class Tokens:
    def __init__(self, secret: bytes, lifetime: int) -> None:
        self.secret = secret
        self.lifetime = lifetime

    def _sign(self, body: str) -> str:
        return hmac.new(self.secret, body.encode("utf-8", "replace"), hashlib.sha256).hexdigest()

    def issue(self, user_id: int, stamp: str) -> str:
        payload = {"user": user_id, "stamp": stamp, "until": int(time.time()) + self.lifetime,
                   "nonce": secrets.token_hex(8)}
        body = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        return f"{body}.{self._sign(body)}"

    def read(self, token: str | None) -> tuple[int, str] | None:
        if not token or token.count(".") != 1:
            return None
        body, signature = token.split(".")
        if not hmac.compare_digest(signature.encode("utf-8"), self._sign(body).encode("ascii")):
            return None
        try:
            payload = json.loads(_decode(body))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict) or payload.get("until", 0) < time.time():
            return None
        user = payload.get("user")
        stamp = payload.get("stamp")
        if not isinstance(user, int) or not isinstance(stamp, str):
            return None
        return user, stamp
