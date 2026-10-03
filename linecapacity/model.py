from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

DIGITS = "0123456789"
CROSS = ("x", "х")
SECTION_SIGNS = ("x", "х", " ")
ALUMINIUM_SIGNS = ("А", "A", "СИП")


class LineType(IntEnum):
    OUTGOING = 0
    SPAN = 1
    BRANCH_TO_LINE = 2
    BRANCH_TO_CONSUMER = 3


class PhaseMode(IntEnum):
    THREE_PHASE = 0
    SINGLE_PHASE = 1


class ConsumerLoadType(IntEnum):
    TYPICAL = 0
    INDIVIDUAL = 1


class ConsumerCategory(IntEnum):
    HOUSEHOLD_NO_CIE = 0
    HOUSEHOLD_WITH_CIE = 1
    LIGHTING = 2
    OTHER = 3


class WireMaterial(IntEnum):
    ALUMINUM = 0
    COPPER = 1


class InsulationType(IntEnum):
    NONE = 0
    XLPE = 1
    PVC = 2


@dataclass
class Transformer:
    type_name: str
    label: str
    x: int = 50
    y: int = 40
    h: int = 80
    sn_kva: float = 250.0
    px_kw: float = 0.74
    pk_kw: float = 3.7
    unn_kv: float = 0.4
    uvn_kv: float = 10.0
    uk_percent: float = 4.5
    pbv_step: int = 0
    pbv_steps: int = 5
    pbv_percent: float = 2.5
    r_ohm: float = 0.0
    x_ohm: float = 0.0
    kt: float = 25.0

    def is_dry(self) -> bool:
        return "ТС" in self.type_name


@dataclass
class Line:
    type_name: str = "СИП-4 4х35+1х25"
    label: str = "Л-1"
    x: int = 0
    y: int = 0
    end_x: int = 0
    end_y: int = 0
    vertical: int = 0
    line_type: LineType = LineType.OUTGOING
    phase_mode: PhaseMode = PhaseMode.THREE_PHASE
    length_m: float = 30.0
    canvas_length: int = 40
    r_phase_ohm_per_km: float = 0.87
    r_neutral_ohm_per_km: float = 0.87
    r_single_phase_ohm_per_km: float = 0.87
    phase_no: int = 1
    r_phase_ohm: float = 0.0
    r_neutral_ohm: float = 0.0
    feeder_no: int = 0

    def cores(self) -> int:
        mark = self.type_name
        if len(mark) <= 1:
            return 0
        multipliers = [position for position in range(1, len(mark)) if mark[position] in CROSS]
        if not multipliers:
            return 2 if self.phase_mode == PhaseMode.SINGLE_PHASE else 4
        if any(mark[position - 1] not in DIGITS for position in multipliers):
            return 0
        return sum(int(mark[position - 1]) for position in multipliers)

    def material(self) -> WireMaterial:
        if any(sign in self.type_name for sign in ALUMINIUM_SIGNS):
            return WireMaterial.ALUMINUM
        return WireMaterial.COPPER

    def section_mm2(self) -> float | None:
        mark = self.type_name
        start = next((mark.find(sign) for sign in SECTION_SIGNS if sign in mark), -1)
        if start < 0:
            return 0.0
        text = ""
        for char in mark[start + 1 : start + 5].replace(".", ","):
            if char != "," and char not in DIGITS:
                break
            text += char
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return None

    def insulation(self) -> InsulationType:
        if "В" in self.type_name:
            return InsulationType.PVC
        if "П" in self.type_name:
            return InsulationType.XLPE
        return InsulationType.NONE


@dataclass
class Pole:
    label: str = "1/1"
    x: int = 0
    y: int = 0
    end_x: int = 0
    end_y: int = 0
    canvas_length: int = 30
    branch_count: int = 1
    current_branch_no: int = 0
    feeder_no: int = 0


@dataclass
class Consumer:
    type_text: str = "мощность по ТУ: 3,5 кВт"
    label: str = "1"
    address: str = ""
    x: int = 0
    y: int = 0
    p_kw: float = 0.35
    cos_phi: float = 0.998
    phase_mode: PhaseMode = PhaseMode.THREE_PHASE
    phase_no: int = 1
    load_type: ConsumerLoadType = ConsumerLoadType.TYPICAL
    annual_kwh: float = 1293.0
    category: ConsumerCategory = ConsumerCategory.HOUSEHOLD_NO_CIE
    feeder_no: int = 0


@dataclass
class ConnectionPoint:
    x: int
    y: int
    active: bool = True
    point_kind: int = 0
    object_no: int = 0
    branch_no: int = 0
    feeder_no: int = 0


@dataclass
class CircuitModel:
    transformer: Transformer
    outgoing_count: int = 0
    lines: list[Line] = field(default_factory=list)
    poles: list[Pole] = field(default_factory=list)
    consumers: list[Consumer] = field(default_factory=list)
    connection_points: list[ConnectionPoint] = field(default_factory=list)
