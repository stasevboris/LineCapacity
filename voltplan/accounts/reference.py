from __future__ import annotations

import json
import time

from ..calc import settings as calc_settings
from ..scheme.editor import EditError
from .security import Refused
from .storage import Store
from .users import User


class Reference:
    def __init__(self, store: Store) -> None:
        self.store = store

    def stored(self) -> dict:
        rows = self.store.work.execute("SELECT key, value FROM reference_settings").fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    def values(self) -> dict:
        merged = calc_settings.defaults()
        merged.update(self.stored())
        return merged

    def update(self, user: User, values: dict) -> dict:
        if not user.is_admin:
            raise Refused("Раздел доступен только администратору", 403)
        try:
            cleaned = calc_settings.clean(values)
            calc_settings.build(self.stored(), cleaned)
        except EditError as error:
            raise Refused(str(error)) from None
        defaults = calc_settings.defaults()
        now = time.time()
        with self.store.writing(self.store.work) as db:
            for key, value in cleaned.items():
                if value == defaults[key]:
                    db.execute("DELETE FROM reference_settings WHERE key = ?", (key,))
                else:
                    db.execute("INSERT OR REPLACE INTO reference_settings (key, value, updated) VALUES (?, ?, ?)",
                               (key, json.dumps(value), now))
        self.store.audit(user.id, "справочник типовых нагрузок изменён", ", ".join(sorted(cleaned)))
        return self.values()

    def reset(self, user: User) -> dict:
        if not user.is_admin:
            raise Refused("Раздел доступен только администратору", 403)
        with self.store.writing(self.store.work) as db:
            db.execute("DELETE FROM reference_settings")
        self.store.audit(user.id, "справочник типовых нагрузок сброшен")
        return self.values()
