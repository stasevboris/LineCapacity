from __future__ import annotations

import json

from tests.helpers import ROOT

RECORDED = ROOT / "tests" / "data" / "calc" / "linecapacity.json"


def recorded() -> list[dict]:
    return json.loads(RECORDED.read_text(encoding="utf-8"))


def case_named(name: str) -> dict:
    return next(case for case in recorded() if case["name"] == name)


def windows(case: dict) -> list[tuple[str, int | None, list[str]]]:
    memo = case["memo"]
    found = [("transformer", None, memo["transformer"])] if "transformer" in memo else []
    for kind in ("lines", "consumers"):
        found += [(kind, int(index), rows) for index, rows in memo.get(kind, {}).items()]
    return found


def compare_report(expected: list[str], actual: list[str], substitutions: list[dict]
                   ) -> tuple[list[str], list[dict]]:
    allowed = {(item["linecapacity"], item["voltplan"]): item for item in substitutions}
    problems = []
    used: list[dict] = []
    if len(expected) != len(actual):
        problems.append(f"строк: LineCapacity {len(expected)}, VoltPlan {len(actual)}")
    for number, (theirs, ours) in enumerate(zip(expected, actual, strict=False), 1):
        if theirs == ours:
            continue
        if (theirs, ours) in allowed:
            if allowed[(theirs, ours)] not in used:
                used.append(allowed[(theirs, ours)])
            continue
        problems.append(f"строка {number}: LineCapacity «{theirs}» — VoltPlan «{ours}»")
    unused = [item for item in substitutions if item not in used]
    problems += [f"записанная подстановка не понадобилась: «{item['linecapacity']}»" for item in unused]
    return problems, used


def explain(expected: list[str], actual: list[str]) -> str:
    diff = [f"строка {i + 1}: LineCapacity «{a}» — VoltPlan «{b}»"
            for i, (a, b) in enumerate(zip(expected, actual, strict=False)) if a != b]
    if len(expected) != len(actual):
        diff.append(f"строк: LineCapacity {len(expected)}, VoltPlan {len(actual)}")
    return "\n".join(diff[:20])
