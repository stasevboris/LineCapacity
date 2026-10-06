from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields

from linecapacity.settings import CalculationSettings

from ..scheme.editor import EditError

WRONG = "Неверные данные! Повторите ввод!"
CURVES = ("home_summer_curve", "home_winter_curve", "electric_home_summer_curve", "electric_home_winter_curve")
HALF_HOURS = 48


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    unit: str
    group: str
    kind: str = "number"


FIELDS = (
    Field("line_air_summer", "Температура воздуха для проводов, лето", "°C", "Температура воздуха"),
    Field("line_air_winter", "Температура воздуха для проводов, зима", "°C", "Температура воздуха"),
    Field("transformer_air_summer", "Температура воздуха для трансформатора, лето", "°C", "Температура воздуха"),
    Field("transformer_air_winter", "Температура воздуха для трансформатора, зима", "°C", "Температура воздуха"),
    Field("voltage_rated", "Номинальное напряжение у потребителя", "В", "Напряжение"),
    Field("voltage_max", "Наибольшее допустимое напряжение у потребителя", "В", "Напряжение"),
    Field("voltage_min", "Наименьшее допустимое напряжение у потребителя", "В", "Напряжение"),
    Field("high_voltage_kv", "Линейное напряжение на стороне ВН", "кВ", "Напряжение"),
    Field("voltage_loss_limit", "Допустимые потери напряжения", "%", "Напряжение"),
    Field("contact_resistance_ohm", "Сопротивление контактов проводов", "Ом", "Напряжение"),
    Field("home_summer_kw", "Бытовой без КИЭ, лето", "кВт", "Типовые нагрузки"),
    Field("home_summer_cos", "Бытовой без КИЭ, лето, cos φ", "", "Типовые нагрузки"),
    Field("home_winter_kw", "Бытовой без КИЭ, зима", "кВт", "Типовые нагрузки"),
    Field("home_winter_cos", "Бытовой без КИЭ, зима, cos φ", "", "Типовые нагрузки"),
    Field("home_minimal_kw", "Бытовой без КИЭ, минимальная нагрузка", "кВт", "Типовые нагрузки"),
    Field("electric_home_summer_kw", "Бытовой с КИЭ, лето", "кВт", "Типовые нагрузки"),
    Field("electric_home_summer_cos", "Бытовой с КИЭ, лето, cos φ", "", "Типовые нагрузки"),
    Field("electric_home_winter_kw", "Бытовой с КИЭ, зима", "кВт", "Типовые нагрузки"),
    Field("electric_home_winter_cos", "Бытовой с КИЭ, зима, cos φ", "", "Типовые нагрузки"),
    Field("electric_home_minimal_kw", "Бытовой с КИЭ, минимальная нагрузка", "кВт", "Типовые нагрузки"),
    Field("street_light_summer_kw", "Уличное освещение, лето", "кВт", "Типовые нагрузки"),
    Field("street_light_summer_cos", "Уличное освещение, лето, cos φ", "", "Типовые нагрузки"),
    Field("street_light_winter_kw", "Уличное освещение, зима", "кВт", "Типовые нагрузки"),
    Field("street_light_winter_cos", "Уличное освещение, зима, cos φ", "", "Типовые нагрузки"),
    Field("extra_load_kw", "Мощность утяжеления нагрузки", "кВт", "Утяжеление"),
    Field("extra_load_enabled", "Утяжелять нагрузку дальних потребителей", "", "Утяжеление", "flag"),
    Field("home_annual_kwh", "Бытовой без КИЭ", "кВт·ч", "Типовое годовое потребление"),
    Field("electric_home_annual_kwh", "Бытовой с КИЭ", "кВт·ч", "Типовое годовое потребление"),
    Field("street_light_annual_kwh", "Уличное освещение", "кВт·ч", "Типовое годовое потребление"),
    Field("scale_by_annual", "Учитывать годовое потребление потребителя", "", "Типовое годовое потребление",
          "flag"),
)
KEYS = {item.key for item in FIELDS} | set(CURVES)
POSITIVE = ("voltage_rated", "voltage_max", "voltage_min", "high_voltage_kv", "home_summer_kw", "home_winter_kw",
            "electric_home_summer_kw", "electric_home_winter_kw", "street_light_summer_kw",
            "street_light_winter_kw", "home_annual_kwh", "electric_home_annual_kwh", "street_light_annual_kwh")
LABELS = {item.key: item.label for item in FIELDS}
LARGEST = 1e6
NOT_NEGATIVE = ("extra_load_kw", "home_minimal_kw", "electric_home_minimal_kw")
COSINES = ("home_summer_cos", "home_winter_cos", "electric_home_summer_cos", "electric_home_winter_cos",
           "street_light_summer_cos", "street_light_winter_cos")


def defaults() -> dict:
    data = asdict(CalculationSettings())
    return {key: list(value) if key in CURVES else value for key, value in data.items()}


def describe() -> list[dict]:
    return [{"key": item.key, "label": item.label, "unit": item.unit, "group": item.group, "kind": item.kind}
            for item in FIELDS]


def number(value) -> float:
    if isinstance(value, bool):
        raise EditError(WRONG)
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise EditError(WRONG) from None
    if not math.isfinite(result):
        raise EditError(WRONG)
    return result


def clean(values: dict | None) -> dict:
    result = {}
    for key, value in (values or {}).items():
        if key not in KEYS:
            raise EditError(f"Неизвестная настройка расчёта: {key}")
        if key in CURVES:
            if not isinstance(value, list | tuple) or len(value) != HALF_HOURS:
                raise EditError("Суточный график должен содержать 48 получасовых значений")
            points = [number(point) for point in value]
            if any(point < 0 for point in points) or max(points) <= 0:
                raise EditError("Значения суточного графика не могут быть отрицательными")
            result[key] = points
        elif key in ("extra_load_enabled", "scale_by_annual"):
            if not isinstance(value, bool):
                raise EditError(WRONG)
            result[key] = value
        else:
            result[key] = number(value)
    return result


def build(*layers: dict | None) -> CalculationSettings:
    merged = defaults()
    for layer in layers:
        merged.update(clean(layer))
    if any(abs(merged[key]) > 1 for key in COSINES):
        raise EditError(WRONG)
    if any(merged[key] <= 0 for key in POSITIVE) or merged["contact_resistance_ohm"] < 0:
        raise EditError(WRONG)
    if any(merged[key] == 0 for key in COSINES):
        raise EditError("cos φ типовой нагрузки не может быть равен нулю")
    for key, value in merged.items():
        if key in LABELS and not isinstance(value, bool) and abs(value) > LARGEST:
            raise EditError(f"«{LABELS[key]}»: значение по модулю не может быть больше 1 000 000")
    if any(merged[key] < 0 for key in NOT_NEGATIVE):
        raise EditError("Утяжеление и минимальные нагрузки не могут быть отрицательными")
    if not merged["voltage_min"] < merged["voltage_rated"] < merged["voltage_max"]:
        raise EditError("Номинальное напряжение должно быть больше наименьшего допустимого и меньше наибольшего")
    if not 0 < merged["voltage_loss_limit"] < 100:
        raise EditError("Допустимые потери напряжения задаются в процентах: больше 0 и меньше 100")
    names = {item.name for item in fields(CalculationSettings)}
    return CalculationSettings(**{key: tuple(value) if key in CURVES else value
                                  for key, value in merged.items() if key in names})


def changed(values: dict | None, base: dict | None = None) -> dict:
    reference = defaults()
    reference.update(clean(base))
    return {key: value for key, value in clean(values).items() if reference.get(key) != value}
