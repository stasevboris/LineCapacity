from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .model import COORDINATE, Text


class Input(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)


class Point(Input):
    x: int = Field(ge=-COORDINATE, le=COORDINATE)
    y: int = Field(ge=-COORDINATE, le=COORDINATE)


class TransformerInput(Input):
    type_name: Text = Field("ТМ-250", min_length=1)
    label: Text = "T1 КТП-54"
    sn_kva: float = Field(250.0, gt=0)
    px_kw: float = Field(0.74, gt=0)
    pk_kw: float = Field(3.7, gt=0)
    unn_kv: float = Field(0.4, gt=0)
    uvn_kv: float = Field(10.0, gt=0)
    uk_percent: float = Field(4.5, gt=0)
    pbv_steps: Literal[3, 5] = 5
    pbv_step: int = 0
    pbv_percent: Literal[2.5, 5.0] = 2.5

    @model_validator(mode="after")
    def step_in_range(self) -> TransformerInput:
        limit = 1 if self.pbv_steps == 3 else 2
        if not -limit <= self.pbv_step <= limit:
            raise ValueError(f"ступень ПБВ должна быть от −{limit} до +{limit}")
        return self


class LineInput(Input):
    type_name: Text = Field("А 16", min_length=1)
    label: Text = "Л-1"
    phase_mode: Literal[0, 1] = 0
    length_m: float = Field(30.0, gt=0)
    r_phase_ohm_per_km: float = 1.8
    r_neutral_ohm_per_km: float = 1.8
    r_single_phase_ohm_per_km: float = 1.8
    phase_no: int = 1

    @model_validator(mode="after")
    def phase_values(self) -> LineInput:
        if self.phase_mode == 0:
            if self.r_phase_ohm_per_km <= 0 or self.r_neutral_ohm_per_km <= 0:
                raise ValueError("сопротивления фазного и нулевого провода должны быть больше нуля")
        else:
            if self.r_single_phase_ohm_per_km <= 0:
                raise ValueError("сопротивление проводов однофазной ЛЭП должно быть больше нуля")
            if self.phase_no not in (1, 2, 3):
                raise ValueError("номер фазы однофазной ЛЭП должен быть 1, 2 или 3")
        return self


class PoleInput(Input):
    label: Text = "1/1"
    branch_count: int = Field(1, ge=0, le=10)


class ConsumerInput(Input):
    type_text: Text | None = None
    label: Text = "10"
    address: Text = "п.Стрешин, ул. Юбилейная, д.10"
    load_type: Literal[0, 1] = 0
    p_kw: float = Field(0.35, ge=0)
    cos_phi: float = Field(0.998, ge=0, le=1)
    annual_kwh: float = Field(1293.0, ge=0)
    category: Literal[0, 1, 2, 3] | None = None

    @model_validator(mode="after")
    def individual_cos(self) -> ConsumerInput:
        if self.load_type == 1 and self.cos_phi <= 0:
            raise ValueError("cos φ индивидуальной нагрузки должен быть больше нуля")
        return self


ActionKind = Literal[
    "new", "outgoing", "span", "branch_line", "branch_consumer",
    "pole", "consumer", "add_branch", "update", "delete",
]
Target = Literal["transformer", "line", "pole", "consumer"]


class Action(Input):
    kind: ActionKind
    point: Point | None = None
    transformer: TransformerInput | None = None
    line: LineInput | None = None
    pole: PoleInput | None = None
    consumer: ConsumerInput | None = None
    to_single: bool = False
    target: Target | None = None
    index: int | None = None
    fields: dict | None = None
