from __future__ import annotations

import time
from pathlib import Path

from ..config import SESSION_SECONDS
from .billing import Billing
from .collab import Collab
from .desk import Desk
from .marks import OwnMarks
from .options import Options
from .projects import Projects
from .reference import Reference
from .security import Tokens, load_secret
from .storage import Store
from .users import User, Users


class Site:
    def __init__(self, data_dir: Path) -> None:
        self.store = Store(data_dir)
        self.users = Users(self.store)
        self.projects = Projects(self.store, self.users)
        self.reference = Reference(self.store)
        self.marks = OwnMarks(self.store)
        self.options = Options(self.store)
        self.collab = Collab(self.store, self.users, self.projects)
        self.desk = Desk(self.store, self.users, self.collab.notify)
        self.billing = Billing(self.store, self.users, self.collab.notify)
        self.tokens = Tokens(load_secret(self.store.data_dir), SESSION_SECONDS)

    def session_user(self, token: str | None) -> User | None:
        read = self.tokens.read(token)
        if read is None:
            return None
        signature = token.split(".")[1]
        if self.store.work.execute("SELECT 1 FROM revoked_sessions WHERE signature = ?", (signature,)).fetchone():
            return None
        user = self.users.get(read[0])
        if user is None or user.stamp != read[1]:
            return None
        return user

    def revoke(self, token: str | None) -> None:
        if self.tokens.read(token) is None:
            return
        now = time.time()
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM revoked_sessions WHERE until < ?", (now,))
            db.execute("INSERT OR IGNORE INTO revoked_sessions (signature, until) VALUES (?, ?)",
                       (token.split(".")[1], now + self.tokens.lifetime))

    def token_for(self, user: User) -> str:
        return self.tokens.issue(user.id, user.stamp)

    def close(self) -> None:
        self.store.close()
