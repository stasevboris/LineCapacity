from __future__ import annotations

import json
import math
import time

from ..calc.losses import DEFAULT_PRICE_USD
from .security import Refused
from .storage import Store
from .users import User


class Options:
    def __init__(self, store: Store) -> None:
        self.store = store

    def energy_price(self) -> float:
        row = self.store.work.execute("SELECT value FROM site_options WHERE key = 'energy_price_usd'").fetchone()
        return json.loads(row["value"]) if row else DEFAULT_PRICE_USD

    def set_energy_price(self, user: User, value: float) -> float:
        if not user.is_admin:
            raise Refused("Раздел доступен только администратору", 403)
        if not math.isfinite(value) or value <= 0 or value > 10:
            raise Refused("Стоимость электроэнергии — от 0 до 10 долларов за кВт·ч")
        with self.store.writing(self.store.work) as db:
            db.execute("INSERT OR REPLACE INTO site_options (key, value, updated) VALUES ('energy_price_usd', ?, ?)",
                       (json.dumps(value), time.time()))
        self.store.audit(user.id, "стоимость электроэнергии изменена", f"{value} USD/кВт·ч")
        return value
