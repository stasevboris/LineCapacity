from __future__ import annotations

import json
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError

from linecapacity.solver import calculate

from ..accounts import tiers
from ..calc import settings as calc_settings
from ..calc.bridge import to_model
from ..calc.document import calculation_report
from ..calc.losses import annual_losses
from ..calc.profile import voltage_profile
from ..calc.results import check_scheme, run
from ..calc.scenarios import summary
from ..calc.tools import allowed, assign_load_kind, settings_after_import, settings_after_load_kind, spread
from ..exchange.meters import MAX_BYTES, apply_period, read_table
from ..scheme.editor import EditError
from ..scheme.model import Scheme
from .session import Signed, site

router = APIRouter(prefix="/api", tags=["Расчёт"])
Values = dict[str, float | bool | list[float]]


class CalcRequest(BaseModel):
    scheme: Scheme
    period: Literal[0, 1, 2] = 2
    min_load: bool = True
    settings: Values | None = None


class LoadKind(BaseModel):
    scheme: Scheme
    typical: bool
    settings: Values = Field(default_factory=dict)


class AllowedRequest(BaseModel):
    scheme: Scheme
    index: int = Field(ge=0)
    settings: Values | None = None


class MeterRequest(BaseModel):
    scheme: Scheme
    p_kw: float
    q_kvar: float
    month: int = Field(ge=1, le=12)
    by_annual: bool = True
    settings: Values | None = None


class Scenario(BaseModel):
    name: str = Field(max_length=120)
    settings: Values | None = None
    period: Literal[0, 1, 2] = 2
    min_load: bool = True


class ScenarioRequest(BaseModel):
    scheme: Scheme
    settings: Values | None = None
    scenarios: list[Scenario] = Field(min_length=1, max_length=20)


def sized(user, scheme: Scheme) -> None:
    tiers.check_size(user, len(scheme.poles), len(scheme.consumers))


def effective(request: Request, *layers: Values | None):
    return calc_settings.build(site(request).reference.values(), *layers)


@router.get("/calc/settings")
def settings_form(user: Signed, request: Request) -> dict:
    return {"fields": calc_settings.describe(), "reference": site(request).reference.values(),
            "defaults": calc_settings.defaults(), "energy_price_usd": site(request).options.energy_price()}


@router.post("/calc")
def calc(user: Signed, data: CalcRequest, request: Request) -> dict:
    sized(user, data.scheme)
    return run(data.scheme, data.period, data.min_load, effective(request, data.settings))


@router.post("/calc/load-kind")
def load_kind(user: Signed, data: LoadKind) -> dict:
    sized(user, data.scheme)
    scheme, message = assign_load_kind(data.scheme, data.typical)
    return {"scheme": scheme, "message": message, "settings": settings_after_load_kind(data.settings, data.typical)}


@router.post("/calc/allowed")
def allowed_power(user: Signed, data: AllowedRequest, request: Request) -> dict:
    sized(user, data.scheme)
    return allowed(data.scheme, effective(request, data.settings), data.index)


@router.post("/calc/meter")
def meter(user: Signed, data: MeterRequest, request: Request) -> dict:
    sized(user, data.scheme)
    scheme, season, message = spread(data.scheme, effective(request, data.settings), data.p_kw, data.q_kvar,
                                     data.month, data.by_annual)
    return {"scheme": scheme, "season": season, "message": message}


@router.post("/calc/scenarios")
def scenarios(user: Signed, data: ScenarioRequest, request: Request) -> dict:
    sized(user, data.scheme)
    reference = site(request).reference.values()
    rows = []
    for item in data.scenarios:
        chosen = calc_settings.build(reference, data.settings, item.settings)
        rows.append(summary(data.scheme, item.name, item.period, item.min_load, chosen))
    return {"rows": rows}


async def upload(file: UploadFile) -> bytes:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise EditError("Файл больше 5 МБ")
    return content


@router.post("/calc/excel/periods")
async def excel_periods(user: Signed, file: Annotated[UploadFile, File()]) -> dict:
    table = read_table(await upload(file))
    return {"periods": table.periods, "meters": len(table.addresses)}


@router.post("/calc/excel/apply")
async def excel_apply(user: Signed, file: Annotated[UploadFile, File()], scheme: Annotated[str, Form()],
                      period: Annotated[int, Form()], cos_phi: Annotated[float, Form()],
                      air: Annotated[float | None, Form()] = None, settings: Annotated[str, Form()] = "{}") -> dict:
    try:
        parsed = Scheme.model_validate_json(scheme)
    except ValidationError:
        raise EditError("Схема передана неверно") from None
    sized(user, parsed)
    try:
        layer = json.loads(settings)
    except ValueError:
        raise EditError("Настройки переданы неверно") from None
    if not isinstance(layer, dict):
        raise EditError("Настройки переданы неверно")
    result = apply_period(parsed, read_table(await upload(file)), period, cos_phi)
    return {"scheme": result.scheme, "found": result.found, "season": result.season, "messages": result.messages,
            "settings": settings_after_import(layer, result.season, air)}


class ProfileRequest(BaseModel):
    scheme: Scheme
    consumer: int | None = Field(None, ge=0)
    season: Literal[0, 1] = 1
    settings: Values | None = None


class LossesRequest(BaseModel):
    scheme: Scheme
    settings: Values | None = None


@router.post("/calc/profile")
def profile(user: Signed, data: ProfileRequest, request: Request) -> dict:
    tiers.require(user, "epure")
    sized(user, data.scheme)
    return voltage_profile(data.scheme, effective(request, data.settings), data.consumer, data.season)


@router.post("/calc/losses")
def losses(user: Signed, data: LossesRequest, request: Request) -> dict:
    tiers.require(user, "annual_losses")
    sized(user, data.scheme)
    check_scheme(data.scheme)
    model = to_model(data.scheme)
    results = calculate(model, effective(request, data.settings), 2, False)
    return annual_losses(model, results, site(request).options.energy_price())


class DocumentRequest(BaseModel):
    scheme: Scheme
    name: str = Field("Схема", max_length=120)
    period: Literal[0, 1, 2] = 2
    min_load: bool = True
    settings: Values | None = None


@router.post("/calc/report.docx")
def report_document(user: Signed, data: DocumentRequest, request: Request) -> Response:
    tiers.require(user, "docx")
    sized(user, data.scheme)
    current = site(request)
    changed = calc_settings.changed(data.settings, current.reference.values())
    price = current.options.energy_price() if "annual_losses" in tiers.effective(user).features else None
    content = calculation_report(data.scheme, data.name, user.name or user.email, effective(request, data.settings),
                                 changed, data.period, data.min_load, price)
    filename = quote(f"Отчёт — {data.name}.docx")
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})
