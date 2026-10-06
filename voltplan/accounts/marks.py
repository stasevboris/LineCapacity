from __future__ import annotations

import json
import math
import time

from ..catalog import phase_hint
from ..scheme.model import MAX_TEXT
from . import tiers
from .security import Refused
from .storage import Store
from .users import User

LIMIT = 200
LINE_FIELDS = {"r_phase_ohm_per_km": "Rф", "r_neutral_ohm_per_km": "R0"}
TRANSFORMER_FIELDS = {"sn_kva": "Sн", "px_kw": "Pхх", "pk_kw": "Pкз", "uvn_kv": "Uвн", "unn_kv": "Uнн",
                      "uk_percent": "Uк", "pbv_percent": "шаг ступени ПБВ"}


def positive(data: dict, key: str, caption: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value <= 0:
        raise Refused(f"{caption}: нужно число больше нуля")
    return float(value)


def clean_mark(kind: str, data: dict) -> dict:
    name = " ".join(str(data.get("type_name", "")).split())
    if not name:
        raise Refused("Марка не может быть пустой")
    if len(name) > MAX_TEXT or " " in name and kind == "transformer":
        raise Refused("Марка трансформатора пишется без пробелов и не длиннее 255 знаков")
    if kind == "line":
        return {"type_name": name, **{key: positive(data, key, caption) for key, caption in LINE_FIELDS.items()}}
    if kind == "transformer":
        values = {key: positive(data, key, caption) for key, caption in TRANSFORMER_FIELDS.items()}
        steps = data.get("pbv_steps")
        if isinstance(steps, bool) or not isinstance(steps, int) or not 0 <= steps <= 9:
            raise Refused("Число ступеней ПБВ: целое от 0 до 9")
        return {"type_name": name, **values, "pbv_steps": steps}
    raise Refused("Вид марки: line (ЛЭП) или transformer (трансформатор)")


class OwnMarks:
    def __init__(self, store: Store) -> None:
        self.store = store

    def listing(self, user: User) -> dict:
        rows = self.store.work.execute("SELECT * FROM own_marks WHERE user_id = ? ORDER BY id", (user.id,)).fetchall()
        found = {"lines": [], "transformers": []}
        for row in rows:
            mark = {"id": row["id"], **json.loads(row["data"]), "own": True}
            if row["kind"] == "line":
                found["lines"].append({**mark, "phase_mode": phase_hint(mark["type_name"])})
            else:
                found["transformers"].append(mark)
        return found

    def add(self, user: User, kind: str, data: dict) -> dict:
        tiers.require(user, "own_marks")
        mark = clean_mark(kind, data)
        count = self.store.work.execute("SELECT COUNT(*) FROM own_marks WHERE user_id = ?", (user.id,)).fetchone()[0]
        if count >= LIMIT:
            raise Refused(f"Своих марок может быть не больше {LIMIT}", 409)
        existing = self.listing(user)["lines" if kind == "line" else "transformers"]
        if any(item["type_name"] == mark["type_name"] for item in existing):
            raise Refused("Такая марка уже есть среди ваших", 409)
        with self.store.writing(self.store.work) as db:
            db.execute("INSERT INTO own_marks (user_id, kind, data, created) VALUES (?, ?, ?, ?)",
                       (user.id, kind, json.dumps(mark, ensure_ascii=False), time.time()))
        return self.listing(user)

    def delete(self, user: User, mark_id: int) -> dict:
        with self.store.writing(self.store.work) as db:
            removed = db.execute("DELETE FROM own_marks WHERE id = ? AND user_id = ?", (mark_id, user.id)).rowcount
        if not removed:
            raise Refused("Марка не найдена", 404)
        return self.listing(user)
