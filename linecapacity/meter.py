from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import HOURS_PER_YEAR
from .model import CircuitModel, ConsumerCategory
from .settings import CalculationSettings

SUMMER_MONTHS = range(5, 10)


class MeterError(ValueError):
    pass


@dataclass
class SpreadLoad:
    p_kw: float
    cos_phi: float


def season_of_month(month: int) -> int:
    if not 1 <= month <= 12:
        raise MeterError("Некорректные данные! Повторите ввод!")
    return 0 if month in SUMMER_MONTHS else 1


def typical_peaks(settings: CalculationSettings, season: int) -> dict[ConsumerCategory, float]:
    if season == 0:
        return {ConsumerCategory.HOUSEHOLD_NO_CIE: settings.home_summer_kw,
                ConsumerCategory.HOUSEHOLD_WITH_CIE: settings.electric_home_summer_kw,
                ConsumerCategory.LIGHTING: settings.street_light_summer_kw}
    return {ConsumerCategory.HOUSEHOLD_NO_CIE: settings.home_winter_kw,
            ConsumerCategory.HOUSEHOLD_WITH_CIE: settings.electric_home_winter_kw,
            ConsumerCategory.LIGHTING: settings.street_light_winter_kw}


def annual_norms(settings: CalculationSettings) -> dict[ConsumerCategory, float]:
    return {ConsumerCategory.HOUSEHOLD_NO_CIE: settings.home_annual_kwh,
            ConsumerCategory.HOUSEHOLD_WITH_CIE: settings.electric_home_annual_kwh,
            ConsumerCategory.LIGHTING: settings.street_light_annual_kwh}


def spread_by_meter(model: CircuitModel, settings: CalculationSettings, p_kw: float, q_kvar: float, month: int,
                    by_annual: bool = True) -> tuple[int, list[SpreadLoad]]:
    season = season_of_month(month)
    peaks = typical_peaks(settings, season)
    norms = annual_norms(settings)
    weights = dict.fromkeys(peaks, 0.0)
    other_count = 0
    other_kwh = 0.0
    for consumer in model.consumers:
        if consumer.category == ConsumerCategory.OTHER:
            other_count += 1
            other_kwh += consumer.annual_kwh
        elif consumer.category in weights:
            weights[consumer.category] += consumer.annual_kwh / norms[consumer.category] if by_annual else 1.0
    expected = sum(peaks[kind] * weights[kind] for kind in peaks) + other_kwh / HOURS_PER_YEAR
    if expected == 0 or p_kw == 0 or not math.isfinite(expected):
        raise MeterError("Некорректные данные! Повторите ввод!")
    factor = p_kw / expected
    cos_phi = math.cos(math.atan(q_kvar / p_kw))
    loads = []
    for consumer in model.consumers:
        share = consumer.p_kw
        if consumer.category == ConsumerCategory.OTHER:
            share = other_kwh / (HOURS_PER_YEAR * other_count) * factor
        elif consumer.category in peaks:
            scale = consumer.annual_kwh / norms[consumer.category] if by_annual else 1.0
            share = peaks[consumer.category] * factor * scale
        loads.append(SpreadLoad(share, cos_phi))
    return season, loads
