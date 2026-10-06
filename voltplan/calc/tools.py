from __future__ import annotations

import math

from linecapacity.allowed import AllowedPowerError, allowed_power
from linecapacity.meter import MeterError, spread_by_meter
from linecapacity.settings import CalculationSettings
from linecapacity.solver import calculate

from ..scheme.editor import EditError
from ..scheme.model import Scheme
from . import settings as calc_settings
from .bridge import to_model
from .results import check_scheme, report
from .text import fixed

TYPICAL_DONE = "Типовые значения нагрузки присвоены!"
INDIVIDUAL_DONE = "Индивидуальные значения нагрузки присвоены!"
SPREAD_DONE = "Нагрузки присвоены!"
NOT_FOUND = "не определяется!"


def assign_load_kind(scheme: Scheme, typical: bool) -> tuple[Scheme, str]:
    if not scheme.consumers:
        raise EditError("В схеме отсутствуют потребители!")
    changed = scheme.model_copy(deep=True)
    for consumer in changed.consumers:
        consumer.load_type = 0 if typical else 1
    return changed, TYPICAL_DONE if typical else INDIVIDUAL_DONE


LINE_AIR = {0: "line_air_summer", 1: "line_air_winter"}


def settings_after_load_kind(layer: dict | None, typical: bool) -> dict:
    kept = calc_settings.clean(layer)
    if typical:
        for key in LINE_AIR.values():
            kept.pop(key, None)
    return kept


def settings_after_import(layer: dict | None, season: int | None, air: float | None) -> dict:
    kept = calc_settings.clean(layer)
    if season in LINE_AIR and air is not None:
        kept[LINE_AIR[season]] = calc_settings.number(air)
    return kept


def spread(scheme: Scheme, settings: CalculationSettings, p_kw: float, q_kvar: float, month: int,
           by_annual: bool) -> tuple[Scheme, int, str]:
    if not scheme.consumers:
        raise EditError("В схеме отсутствуют потребители!")
    if not (math.isfinite(p_kw) and math.isfinite(q_kvar)):
        raise EditError("Некорректные данные! Повторите ввод!")
    try:
        season, loads = spread_by_meter(to_model(scheme), settings, p_kw, q_kvar, month, by_annual)
    except MeterError as error:
        raise EditError(str(error)) from None
    changed = scheme.model_copy(deep=True)
    for consumer, load in zip(changed.consumers, loads, strict=True):
        consumer.load_type = 1
        consumer.p_kw = load.p_kw
        consumer.cos_phi = load.cos_phi
    return changed, season, SPREAD_DONE


def kw(value: float) -> str:
    return f"{fixed(value / 1000.0, 5, 2)} кВт" if value > 0 else NOT_FOUND


def allowed(scheme: Scheme, settings: CalculationSettings, index: int) -> dict:
    check_scheme(scheme)
    if not 0 <= index < len(scheme.consumers):
        raise EditError("Потребитель не найден")
    model = to_model(scheme)
    base = calculate(model, settings, 2, False)
    _, good = report(scheme, model, settings, base, False)
    if not good:
        raise EditError("Допустимая мощность определяется, только если пропускная способность сети достаточна")
    try:
        found = allowed_power(model, settings, index, base)
    except AllowedPowerError as error:
        raise EditError(str(error)) from None
    address = scheme.consumers[index].address
    return {
        "season": found.season,
        "by_voltage_kw": found.by_voltage_w / 1000.0,
        "by_transformer_kw": found.by_transformer_w / 1000.0,
        "report": [
            "Допустимая мощность потребителя по адресу",
            f"{address}:",
            f" по критерию допустимых потерь напряжения: {kw(found.by_voltage_w)}",
            f" по критерию перегрузки силового трансформатора: {kw(found.by_transformer_w)}",
        ],
        "memo": [
            "",
            "Допустимая активная мощность потребителя: ",
            f" по критерию допустимых потерь напряжения: {fixed(found.by_voltage_w / 1000.0, 5, 2)} кВт",
            f" по критерию перегрузки силового трансформатора: {fixed(found.by_transformer_w / 1000.0, 5, 2)} кВт",
        ],
    }
