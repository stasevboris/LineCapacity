from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

MAX_POLES = 300
MAX_LINES = MAX_POLES * 4
MAX_CONSUMERS = MAX_POLES * 2
MAX_POINTS = MAX_POLES * 8
MAX_OUTGOING = 21
MAX_BRANCHES = 100
MAX_TEXT = 255
COORDINATE = 10_000_000


def plain_text(value: str) -> str:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("текст не должен содержать переводов строки и служебных символов")
    try:
        value.encode("cp1251")
    except UnicodeEncodeError as exc:
        raise ValueError(f"символ «{value[exc.start]}» нельзя сохранить в файл .cir") from exc
    return value


Text = Annotated[str, Field(max_length=MAX_TEXT), AfterValidator(plain_text)]
Coordinate = Annotated[int, Field(ge=-COORDINATE, le=COORDINATE)]
Length = Annotated[int, Field(ge=0, le=COORDINATE)]
Feeder = Annotated[int, Field(ge=0, le=MAX_OUTGOING)]


class Part(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="ignore", allow_inf_nan=False)


class Transformer(Part):
    type_name: Text = "ТМ-250"
    label: Text = "T1 КТП-54"
    x: Coordinate = 50
    y: Coordinate = 40
    h: Length = 5467
    sn_kva: float = 250.0
    px_kw: float = 0.74
    pk_kw: float = 3.7
    unn_kv: float = 0.4
    uvn_kv: float = 10.0
    uk_percent: float = 4.5
    pbv_step: int = Field(0, ge=-10, le=10)
    pbv_steps: int = Field(5, ge=0, le=20)
    pbv_percent: float = 2.5
    r_ohm: float = 1.0
    x_ohm: float = 1.0
    kt: float = 1.0


class Line(Part):
    type_name: Text = "А 16"
    label: Text = "Л-1"
    x: Coordinate = 0
    y: Coordinate = 0
    end_x: Coordinate = 0
    end_y: Coordinate = 0
    vertical: int = Field(0, ge=0, le=1)
    line_type: int = Field(0, ge=0, le=3)
    phase_mode: int = Field(0, ge=0, le=1)
    length_m: float = 30.0
    canvas_length: Length = 40
    r_phase_ohm_per_km: float = 1.8
    r_neutral_ohm_per_km: float = 1.8
    r_single_phase_ohm_per_km: float = 1.8
    phase_no: int = Field(1, ge=0, le=3)
    r_phase_ohm: float = 1.0
    r_neutral_ohm: float = 1.0
    feeder_no: Feeder = 0


class Pole(Part):
    label: Text = "1/1"
    x: Coordinate = 0
    y: Coordinate = 0
    end_x: Coordinate = 0
    end_y: Coordinate = 0
    canvas_length: Length = 30
    branch_count: int = Field(1, ge=0, le=MAX_BRANCHES)
    current_branch_no: int = Field(0, ge=0, le=MAX_BRANCHES)
    feeder_no: Feeder = 0


class Consumer(Part):
    type_text: Text = "мощность по ТУ: 3,5 кВт"
    label: Text = "10"
    address: Text = "п.Стрешин, ул. Юбилейная, д.10"
    x: Coordinate = 0
    y: Coordinate = 0
    p_kw: float = 0.35
    cos_phi: float = 0.998
    phase_mode: int = Field(0, ge=0, le=1)
    phase_no: int = Field(1, ge=0, le=3)
    load_type: int = Field(0, ge=0, le=1)
    annual_kwh: float = 1293.0
    category: float = 0.0
    feeder_no: Feeder = 0


class ConnectionPoint(Part):
    x: Coordinate = 0
    y: Coordinate = 0
    active: bool = False
    point_kind: int = Field(0, ge=0, le=7)
    object_no: int = Field(0, ge=0, le=MAX_POINTS)
    branch_no: int = Field(0, ge=0, le=MAX_BRANCHES)
    feeder_no: Feeder = 0


class Spare(Part):
    lines: list[Line] = Field(default_factory=list, max_length=MAX_LINES)
    poles: list[Pole] = Field(default_factory=list, max_length=MAX_POLES)
    consumers: list[Consumer] = Field(default_factory=list, max_length=MAX_CONSUMERS)


class Scheme(Part):
    transformer: Transformer = Field(default_factory=Transformer)
    lines: list[Line] = Field(default_factory=list, max_length=MAX_LINES)
    poles: list[Pole] = Field(default_factory=list, max_length=MAX_POLES)
    consumers: list[Consumer] = Field(default_factory=list, max_length=MAX_CONSUMERS)
    connection_points: list[ConnectionPoint] = Field(default_factory=list, max_length=MAX_POINTS)
    outgoing_count: int = Field(0, ge=0, le=MAX_OUTGOING)
    spare: Spare = Field(default_factory=Spare)
