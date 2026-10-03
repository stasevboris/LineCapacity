from __future__ import annotations

from .editor import (
    BRANCH_CONSUMER,
    BRANCH_LINE,
    LINE_TYPE_BY_POINT_KIND,
    OUTGOING,
    SPAN,
    default_type_text,
    known_category,
    slot,
)
from .model import Scheme, Transformer

POINT_KIND_BY_ACTION = {"outgoing": OUTGOING, "span": SPAN, "branch_line": BRANCH_LINE,
                        "branch_consumer": BRANCH_CONSUMER}
LINE_FIELDS = ("type_name", "label", "phase_mode", "length_m", "r_phase_ohm_per_km",
               "r_neutral_ohm_per_km", "r_single_phase_ohm_per_km", "phase_no")
TRANSFORMER_FIELDS = ("type_name", "label", "sn_kva", "px_kw", "pk_kw", "unn_kv", "uvn_kv",
                      "uk_percent", "pbv_steps", "pbv_step", "pbv_percent")
CONSUMER_FIELDS = ("label", "address", "load_type", "p_kw", "cos_phi", "annual_kwh")


def pick(source, names) -> dict:
    data = source.model_dump()
    return {name: data[name] for name in names}


def line_values(scheme: Scheme | None, point_kind: int) -> dict:
    lines = scheme.lines if scheme else []
    if not lines:
        return pick(slot(scheme, "lines"), LINE_FIELDS)
    wanted = LINE_TYPE_BY_POINT_KIND[point_kind]
    for line in reversed(lines):
        if line.line_type == wanted:
            return pick(line, LINE_FIELDS)
    return pick(lines[0], LINE_FIELDS)


def pole_values(scheme: Scheme | None) -> dict:
    poles = scheme.poles if scheme else []
    source = poles[-1] if poles else slot(scheme, "poles")
    return {"label": source.label, "branch_count": min(source.branch_count, 10)}


def consumer_values(scheme: Scheme | None, phase_mode: int) -> dict:
    consumers = scheme.consumers if scheme else []
    source = consumers[-1] if consumers else slot(scheme, "consumers")
    values = pick(source, CONSUMER_FIELDS)
    values["category"] = int(source.category) if known_category(source.category) else None
    values["type_text"] = default_type_text(phase_mode)
    return values


def transformer_values() -> dict:
    return pick(Transformer(), TRANSFORMER_FIELDS)


def blank_line(scheme: Scheme | None) -> dict:
    return pick(slot(scheme, "lines"), LINE_FIELDS)


def type_texts() -> list[str]:
    return [default_type_text(0), default_type_text(1)]


def feeding(scheme: Scheme | None, x: int | None, y: int | None) -> dict:
    for line in scheme.lines if scheme else []:
        if line.end_x == x and line.end_y == y:
            return {"phase_mode": line.phase_mode, "phase_no": line.phase_no}
    return {"phase_mode": 0, "phase_no": 1}


def dialog(scheme: Scheme | None, kind: str, x: int | None = None, y: int | None = None) -> dict:
    if kind == "new":
        return {"transformer": transformer_values(), "line": line_values(None, OUTGOING),
                "pole": pole_values(None), "blank": blank_line(None)}
    if kind in ("outgoing", "span", "branch_line"):
        return {"line": line_values(scheme, POINT_KIND_BY_ACTION[kind]), "pole": pole_values(scheme),
                "blank": blank_line(scheme)}
    if kind == "branch_consumer":
        line = line_values(scheme, BRANCH_CONSUMER)
        return {"line": line, "consumer": consumer_values(scheme, line["phase_mode"]),
                "blank": blank_line(scheme), "type_texts": type_texts()}
    if kind == "pole":
        return {"pole": pole_values(scheme)}
    if kind == "consumer":
        phase = feeding(scheme, x, y)
        return {"consumer": consumer_values(scheme, phase["phase_mode"]), "feeding": phase}
    return {}
