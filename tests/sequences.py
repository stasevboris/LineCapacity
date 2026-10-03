from __future__ import annotations

from voltplan.scheme import forms
from voltplan.scheme.actions import Action
from voltplan.scheme.editor import BRANCH_STEP, Editor, default_type_text, restore
from voltplan.scheme.model import Scheme

DIALOG_KINDS = {"new", "outgoing", "span", "branch_line", "branch_consumer", "pole", "consumer"}
LINE_COMMON = ("type_name", "label", "phase_mode", "length_m")
LINE_PHASE = {0: ("r_phase_ohm_per_km", "r_neutral_ohm_per_km"), 1: ("r_single_phase_ohm_per_km", "phase_no")}

TRANSFORMER = {
    "type_name": "ТМ-160", "label": "Т1 КТП-17", "sn_kva": 160, "px_kw": 0.51, "pk_kw": 2.65,
    "unn_kv": 0.4, "uvn_kv": 10, "uk_percent": 4.5, "pbv_steps": 5, "pbv_step": 0, "pbv_percent": 2.5,
}


def trunk(label: str, length: float) -> dict:
    return {"type_name": "А 35", "label": label, "phase_mode": 0, "length_m": length,
            "r_phase_ohm_per_km": 0.868, "r_neutral_ohm_per_km": 0.868}


def drop_one(label: str, length: float, phase: int) -> dict:
    return {"type_name": "СИП-4 2х16", "label": label, "phase_mode": 1, "length_m": length,
            "r_single_phase_ohm_per_km": 1.91, "phase_no": phase}


def drop_three(label: str, length: float) -> dict:
    return {"type_name": "СИП-4 4х16", "label": label, "phase_mode": 0, "length_m": length,
            "r_phase_ohm_per_km": 1.91, "r_neutral_ohm_per_km": 1.91}


def house(label: str, address: str, annual: float, category: int = 0) -> dict:
    return {"type_text": "мощность по ТУ: 3,5 кВт", "label": label, "address": address,
            "load_type": 0, "annual_kwh": annual, "category": category}


def shop(label: str, address: str, power: float) -> dict:
    return {"type_text": "мощность по ТУ: 12 кВт", "label": label, "address": address,
            "load_type": 1, "p_kw": power, "cos_phi": 0.95}


def pole(label: str, branches: int) -> dict:
    return {"label": label, "branch_count": branches}


def tap(scheme: Scheme, label: str, branch: int) -> dict:
    found = next(p for p in scheme.poles if p.label == label)
    return {"x": found.x + branch * BRANCH_STEP, "y": found.y}


def end(scheme: Scheme, label: str) -> dict:
    found = next(p for p in scheme.poles if p.label == label)
    return {"x": found.x + found.canvas_length, "y": found.y}


def pole_index(scheme: Scheme, label: str) -> int:
    return next(i for i, p in enumerate(scheme.poles) if p.label == label)


def consumer_index(scheme: Scheme, label: str) -> int:
    return next(i for i, c in enumerate(scheme.consumers) if c.label == label)


def line_index(scheme: Scheme, label: str) -> int:
    return next(i for i, line in enumerate(scheme.lines) if line.label == label)


def line_end(scheme: Scheme, label: str) -> dict:
    found = scheme.lines[line_index(scheme, label)]
    return {"x": found.end_x, "y": found.end_y}


def basic_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1), "line": drop_one("Л-2", 25, 2),
                   "consumer": house("1", "ул. Лесная, 1", 1500)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 2), "line": drop_three("Л-3", 20),
                   "consumer": shop("2", "ул. Лесная, 2", 5.5)},
        lambda s: {"kind": "span", "point": end(s, "1"), "line": trunk("Л-4", 45), "pole": pole("2", 3)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "2", 3), "line": drop_one("Л-5", 18, 1),
                   "consumer": house("3", "ул. Лесная, 3", 1293)},
        lambda s: {"kind": "branch_line", "point": tap(s, "2", 2), "line": trunk("Л-6", 30),
                   "pole": pole("2/1", 1), "to_single": False},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "2/1", 1), "line": drop_one("Л-7", 22, 3),
                   "consumer": house("4", "пер. Тихий, 4", 9000, 1)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "2", 1), "line": drop_one("Л-8", 15, 1),
                   "consumer": house("5", "ул. Лесная, 5", 800)},
    ]


def complex_steps():
    return basic_steps() + [
        lambda s: {"kind": "outgoing", "line": trunk("Л-9", 35), "pole": pole("3", 2)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "3", 1), "line": drop_one("Л-10", 20, 2),
                   "consumer": house("6", "ул. Полевая, 6", 1100)},
        lambda s: {"kind": "span", "point": end(s, "3"), "line": trunk("Л-11", 40), "pole": pole("4", 1)},
        lambda s: {"kind": "branch_line", "point": tap(s, "3", 2), "line": trunk("Л-12", 28),
                   "pole": pole("3/1", 1), "to_single": True},
        lambda s: {"kind": "span", "point": end(s, "2/1"), "line": trunk("Л-13", 32), "pole": pole("2/2", 1)},
        lambda s: {"kind": "add_branch", "index": pole_index(s, "1")},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1), "line": drop_one("Л-14", 16, 3),
                   "consumer": house("8", "ул. Лесная, 8", 1400)},
        lambda s: {"kind": "delete", "target": "consumer", "index": consumer_index(s, "6")},
    ]


def complete_line(prefill: dict, blank: dict, typed: dict) -> dict:
    phase = typed.get("phase_mode", prefill["phase_mode"])
    shown = dict(prefill)
    if phase != prefill["phase_mode"]:
        shown.update({name: blank[name] for name in LINE_PHASE[phase]})
    shown.update(typed)
    shown["phase_mode"] = phase
    return {name: shown[name] for name in LINE_COMMON + LINE_PHASE[phase]}


def complete_consumer(prefill: dict, typed: dict, phase: int | None) -> dict:
    shown = dict(prefill)
    if phase is not None:
        shown["type_text"] = default_type_text(phase)
    shown.update(typed)
    return shown


def complete(scheme: Scheme, action: dict) -> dict:
    kind = action["kind"]
    if kind not in DIALOG_KINDS:
        return action
    place = action.get("point") or {}
    form = forms.dialog(None if kind == "new" else scheme, kind, place.get("x"), place.get("y"))
    full = dict(action)
    if "transformer" in form:
        full["transformer"] = {**form["transformer"], **action.get("transformer", {})}
    if "line" in form:
        full["line"] = complete_line(form["line"], form["blank"], action.get("line", {}))
    if "pole" in form:
        full["pole"] = {**form["pole"], **action.get("pole", {})}
    if "consumer" in form:
        phase = full["line"]["phase_mode"] if kind == "branch_consumer" else None
        full["consumer"] = complete_consumer(form["consumer"], action.get("consumer", {}), phase)
    if kind == "branch_line":
        full.setdefault("to_single", False)
    return full


def build(steps) -> list[tuple[dict, Scheme]]:
    scheme = Scheme()
    blocks: list[Scheme] = []
    history = []
    for step in steps:
        action = step(scheme)
        kind = action["kind"]
        if kind == "undo":
            if len(blocks) > 1:
                blocks.pop()
            if blocks:
                scheme = restore(scheme, blocks[-1])
        elif kind == "click":
            editor = Editor(scheme)
            editor.click_point(action["point"]["x"], action["point"]["y"])
            scheme = editor.s
        else:
            editor = Editor(scheme)
            scheme = editor.apply(Action(**complete(scheme, action)))
            blocks = list(editor.snapshots) if kind == "new" else blocks + editor.snapshots
        history.append((action, scheme))
    return history


def edit_steps():
    return basic_steps() + [
        lambda s: {"kind": "update", "target": "transformer", "index": 0,
                   "fields": {"label": "Т1 КТП-17а", "pbv_step": 1}},
        lambda s: {"kind": "update", "target": "line", "index": line_index(s, "Л-4"),
                   "fields": {"label": "Л-4а", "phase_mode": 1, "r_single_phase_ohm_per_km": 0.84, "phase_no": 2}},
        lambda s: {"kind": "update", "target": "line", "index": line_index(s, "Л-2"), "fields": {"phase_mode": 0}},
        lambda s: {"kind": "update", "target": "line", "index": line_index(s, "Л-6"), "fields": {"length_m": 31.5}},
        lambda s: {"kind": "update", "target": "pole", "index": pole_index(s, "2"), "fields": {"label": "2а"}},
        lambda s: {"kind": "update", "target": "consumer", "index": consumer_index(s, "2"),
                   "fields": {"load_type": 0, "category": 2, "annual_kwh": 2400}},
        lambda s: {"kind": "update", "target": "consumer", "index": consumer_index(s, "1"), "fields": {"label": "1а"}},
        lambda s: {"kind": "span", "point": end(s, "2а")},
        lambda s: {"kind": "branch_consumer", "point": {"x": s.poles[-1].x + BRANCH_STEP, "y": s.poles[-1].y}},
    ]


def default_steps():
    return [
        lambda s: {"kind": "new"},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1/1", 1)},
        lambda s: {"kind": "span", "point": end(s, "1/1")},
        lambda s: {"kind": "outgoing"},
        lambda s: {"kind": "branch_line", "point": {"x": s.poles[1].x + BRANCH_STEP, "y": s.poles[1].y}},
    ]


def first_line_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "span", "point": end(s, "1")},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1),
                   "line": {"phase_mode": 1, "r_single_phase_ohm_per_km": 1.91, "phase_no": 3}},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 2)},
    ]


def undo_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "span", "point": end(s, "1"), "line": trunk("Л-2", 45), "pole": pole("2", 1)},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "pole", "point": line_end(s, "Л-2"), "pole": pole("2а", 2)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1), "line": drop_one("Л-3", 25, 2),
                   "consumer": house("1", "ул. Лесная, 1", 1500)},
        lambda s: {"kind": "delete", "target": "consumer", "index": 0},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "add_branch", "index": pole_index(s, "1")},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 3), "line": drop_three("Л-4", 20),
                   "consumer": shop("2", "ул. Лесная, 2", 5.5)},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "undo"},
    ]


def delete_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 3)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-2", 35), "pole": pole("2", 1)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1), "line": drop_one("Л-3", 25, 2),
                   "consumer": house("1", "ул. 1", 1500)},
        lambda s: {"kind": "delete", "target": "consumer", "index": 0},
        lambda s: {"kind": "delete", "target": "line", "index": line_index(s, "Л-3")},
        lambda s: {"kind": "branch_line", "point": tap(s, "1", 1), "line": trunk("Л-5", 30),
                   "pole": pole("1/1", 1), "to_single": False},
        lambda s: {"kind": "span", "point": end(s, "2"), "line": trunk("Л-6", 30), "pole": pole("3", 1)},
        lambda s: {"kind": "delete", "target": "pole", "index": pole_index(s, "3")},
        lambda s: {"kind": "delete", "target": "line", "index": line_index(s, "Л-6")},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 3), "line": drop_three("Л-7", 20),
                   "consumer": shop("2", "ул. 2", 5)},
        lambda s: {"kind": "click", "point": tap(s, "1", 2)},
        lambda s: {"kind": "span", "point": end(s, "2"), "line": trunk("Л-8", 30), "pole": pole("4", 1)},
    ]


def free_end_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "span", "point": end(s, "1"), "line": trunk("Л-2", 40), "pole": pole("2", 1)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1), "line": drop_one("Л-3", 20, 3),
                   "consumer": house("1", "а", 1000)},
        lambda s: {"kind": "delete", "target": "pole", "index": pole_index(s, "2")},
        lambda s: {"kind": "delete", "target": "consumer", "index": 0},
        lambda s: {"kind": "pole", "point": line_end(s, "Л-2"), "pole": pole("2а", 2)},
        lambda s: {"kind": "consumer", "point": line_end(s, "Л-3"), "consumer": house("1а", "б", 2000)},
        lambda s: {"kind": "click", "point": tap(s, "2а", 2)},
    ]


def undo_outgoing_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-2", 35), "pole": pole("2", 1)},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "pole", "point": line_end(s, "Л-2"), "pole": pole("2а", 1)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-3", 30), "pole": pole("3", 1)},
    ]


def undo_new_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "pole", "point": line_end(s, "Л-1"), "pole": pole("1а", 1)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-2", 30), "pole": pole("2", 1)},
        lambda s: {"kind": "span", "point": end(s, "2"), "line": trunk("Л-3", 30), "pole": pole("3", 1)},
    ]


def double_undo_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-2", 35), "pole": pole("2", 1)},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "outgoing", "line": trunk("Л-3", 30), "pole": pole("3", 2)},
        lambda s: {"kind": "span", "point": end(s, "3"), "line": trunk("Л-4", 30), "pole": pole("4", 1)},
    ]


def undo_after_delete_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 2)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-2", 35), "pole": pole("2", 1)},
        lambda s: {"kind": "delete", "target": "pole", "index": 1},
        lambda s: {"kind": "delete", "target": "line", "index": 1},
        lambda s: {"kind": "undo"},
        lambda s: {"kind": "pole", "point": line_end(s, "Л-2"), "pole": pole("2а", 1)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-3", 30), "pole": pole("3", 1)},
    ]


def first_outgoing_removed_steps():
    return [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 1)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1), "line": drop_one("Л-2", 25, 2),
                   "consumer": house("1", "ул. Первая, 1", 1500)},
        lambda s: {"kind": "outgoing", "line": trunk("Л-3", 35), "pole": pole("2", 2)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "2", 1), "line": drop_one("Л-4", 20, 1),
                   "consumer": house("2", "ул. Вторая, 2", 1200)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "2", 2), "line": drop_one("Л-5", 22, 2),
                   "consumer": house("3", "ул. Вторая, 3", 1800)},
        lambda s: {"kind": "span", "point": end(s, "2"), "line": trunk("Л-6", 40), "pole": pole("3", 2)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "3", 1), "line": drop_one("Л-7", 18, 1),
                   "consumer": house("4", "ул. Вторая, 4", 2000)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "3", 2), "line": drop_three("Л-8", 20),
                   "consumer": shop("5", "ул. Вторая, 5", 4)},
        lambda s: {"kind": "delete", "target": "consumer", "index": consumer_index(s, "1")},
        lambda s: {"kind": "delete", "target": "line", "index": line_index(s, "Л-2")},
        lambda s: {"kind": "delete", "target": "pole", "index": pole_index(s, "1")},
        lambda s: {"kind": "delete", "target": "line", "index": line_index(s, "Л-1")},
    ]


SEQUENCES = {
    "базовая": basic_steps,
    "сложная": complex_steps,
    "правка": edit_steps,
    "умолчания": default_steps,
    "первая-лэп": first_line_steps,
    "отмена": undo_steps,
    "отмена-отходящей": undo_outgoing_steps,
    "отмена-новой": undo_new_steps,
    "двойная-отмена": double_undo_steps,
    "отмена-после-удаления": undo_after_delete_steps,
    "удаление": delete_steps,
    "свободные-концы": free_end_steps,
    "удаление-первой-отходящей": first_outgoing_removed_steps,
}
