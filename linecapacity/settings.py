from __future__ import annotations

from dataclasses import dataclass

from .charts import ELECTRIC_HOME_SUMMER_CURVE, ELECTRIC_HOME_WINTER_CURVE, HOME_SUMMER_CURVE, HOME_WINTER_CURVE
from .constants import (
    CONTACT_RESISTANCE_OHM,
    ELECTRIC_HOME_ANNUAL_KWH,
    ELECTRIC_HOME_MINIMAL_KW,
    ELECTRIC_HOME_SUMMER_KW,
    ELECTRIC_HOME_WINTER_KW,
    EXTRA_LOAD_KW,
    HIGH_VOLTAGE_KV,
    HOME_ANNUAL_KWH,
    HOME_MINIMAL_KW,
    HOME_SUMMER_KW,
    HOME_WINTER_KW,
    LINE_AIR_SUMMER,
    LINE_AIR_WINTER,
    STREET_LIGHT_ANNUAL_KWH,
    STREET_LIGHT_SUMMER_KW,
    STREET_LIGHT_WINTER_KW,
    TRANSFORMER_AIR_SUMMER,
    TRANSFORMER_AIR_WINTER,
    TYPICAL_COS,
    VOLTAGE_LOSS_LIMIT,
    VOLTAGE_MAX,
    VOLTAGE_MIN,
    VOLTAGE_RATED,
)


@dataclass
class CalculationSettings:
    line_air_summer: float = LINE_AIR_SUMMER
    line_air_winter: float = LINE_AIR_WINTER
    transformer_air_summer: float = TRANSFORMER_AIR_SUMMER
    transformer_air_winter: float = TRANSFORMER_AIR_WINTER

    voltage_min: float = VOLTAGE_MIN
    voltage_max: float = VOLTAGE_MAX
    voltage_rated: float = VOLTAGE_RATED
    high_voltage_kv: float = HIGH_VOLTAGE_KV
    voltage_loss_limit: float = VOLTAGE_LOSS_LIMIT
    contact_resistance_ohm: float = CONTACT_RESISTANCE_OHM

    home_summer_kw: float = HOME_SUMMER_KW
    home_winter_kw: float = HOME_WINTER_KW
    home_minimal_kw: float = HOME_MINIMAL_KW
    home_summer_cos: float = TYPICAL_COS
    home_winter_cos: float = TYPICAL_COS
    electric_home_summer_kw: float = ELECTRIC_HOME_SUMMER_KW
    electric_home_winter_kw: float = ELECTRIC_HOME_WINTER_KW
    electric_home_minimal_kw: float = ELECTRIC_HOME_MINIMAL_KW
    electric_home_summer_cos: float = TYPICAL_COS
    electric_home_winter_cos: float = TYPICAL_COS
    street_light_summer_kw: float = STREET_LIGHT_SUMMER_KW
    street_light_winter_kw: float = STREET_LIGHT_WINTER_KW
    street_light_summer_cos: float = TYPICAL_COS
    street_light_winter_cos: float = TYPICAL_COS
    extra_load_kw: float = EXTRA_LOAD_KW
    extra_load_enabled: bool = True

    home_annual_kwh: float = HOME_ANNUAL_KWH
    electric_home_annual_kwh: float = ELECTRIC_HOME_ANNUAL_KWH
    street_light_annual_kwh: float = STREET_LIGHT_ANNUAL_KWH
    scale_by_annual: bool = True

    home_summer_curve: tuple[float, ...] = HOME_SUMMER_CURVE
    home_winter_curve: tuple[float, ...] = HOME_WINTER_CURVE
    electric_home_summer_curve: tuple[float, ...] = ELECTRIC_HOME_SUMMER_CURVE
    electric_home_winter_curve: tuple[float, ...] = ELECTRIC_HOME_WINTER_CURVE
