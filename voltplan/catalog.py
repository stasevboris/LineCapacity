from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from linecapacity.model import InsulationType, Line, PhaseMode, WireMaterial

from .calc.text import general
from .config import DATABASE
from .exchange.cir import decode, parse_number


@dataclass(frozen=True)
class TransformerMark:
    type_name: str
    sn_kva: float
    px_kw: float
    pk_kw: float
    uvn_kv: float
    unn_kv: float
    uk_percent: float
    pbv_steps: int
    pbv_percent: float


@dataclass(frozen=True)
class LineMark:
    type_name: str
    r_phase_ohm_per_km: float
    r_neutral_ohm_per_km: float


INSULATION_NAMES = {
    InsulationType.NONE: "нет",
    InsulationType.XLPE: "сшитый полиэтилен",
    InsulationType.PVC: "поливинилхлорид",
}
MATERIAL_NAMES = {WireMaterial.ALUMINUM: "алюминий", WireMaterial.COPPER: "медь"}


def mark_rows(type_name: str, phase_mode: int) -> list[str]:
    line = Line(type_name=type_name, phase_mode=PhaseMode(phase_mode))
    section = line.section_mm2()
    shown = f"{general(section, 15)} мм^2" if section is not None else "не определено"
    return [
        f"Материал провода: {MATERIAL_NAMES[line.material()]}",
        f"Материал изоляции: {INSULATION_NAMES[line.insulation()]}",
        f"Количество жил: {line.cores()}",
        f"Сечение фазного провода: {shown}",
    ]


def phase_hint(type_name: str) -> int:
    line = Line(type_name=type_name)
    if line.cores() > 2 or line.insulation() == InsulationType.NONE:
        return 0
    return 1


def read_transformers(path: Path) -> list[TransformerMark]:
    marks = []
    for row in decode(path.read_bytes()).splitlines():
        parts = row.split()
        if len(parts) != 9:
            continue
        name, rated, idle, short, high, low, impedance, steps, percent = parts
        marks.append(TransformerMark(
            type_name=name, sn_kva=parse_number(rated), px_kw=parse_number(idle),
            pk_kw=parse_number(short), uvn_kv=parse_number(high),
            unn_kv=parse_number(low), uk_percent=parse_number(impedance),
            pbv_steps=int(parse_number(steps)), pbv_percent=parse_number(percent),
        ))
    return marks


def read_lines(path: Path) -> list[LineMark]:
    marks = []
    for row in decode(path.read_bytes()).splitlines():
        parts = row.split()
        if len(parts) < 3:
            continue
        marks.append(LineMark(
            type_name=" ".join(parts[:-2]),
            r_phase_ohm_per_km=parse_number(parts[-2]),
            r_neutral_ohm_per_km=parse_number(parts[-1]),
        ))
    return marks


def describe_line(mark: LineMark) -> dict:
    return {**asdict(mark), "phase_mode": phase_hint(mark.type_name)}


@lru_cache(maxsize=4)
def load(directory: str = str(DATABASE)) -> dict:
    root = Path(directory)
    return {
        "transformers": [asdict(m) for m in read_transformers(root / "Transformers.trf")],
        "lines": [describe_line(m) for m in read_lines(root / "Lines.lns")],
    }
