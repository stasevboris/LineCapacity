from __future__ import annotations

import copy
import math
from dataclasses import dataclass

from .constants import OIL_OVERLOAD, WINDING_OVERLOAD
from .model import CircuitModel, ConsumerLoadType, PhaseMode
from .settings import CalculationSettings
from .solver import CalculationResults, Phases, _consumer_load, _transformer_heating, calculate

STEP_KW = 5.0
REFERENCE_PHASE_V = 220.0
LOAD_GROWTH = 1.05
ABSENT_V = 1000.0
GROWTH_STEPS_LIMIT = 5000


class AllowedPowerError(ValueError):
    pass


@dataclass
class AllowedPower:
    by_voltage_w: float
    by_transformer_w: float
    season: int
    candidates_w: list[float]


def own_phases(model: CircuitModel, voltages: list[Phases], index: int) -> list[float]:
    consumer = model.consumers[index]
    if consumer.phase_mode == PhaseMode.THREE_PHASE:
        return [float(value) for value in voltages[index]]
    phases = [ABSENT_V] * 3
    phases[consumer.phase_no - 1] = float(voltages[index][consumer.phase_no - 1])
    return phases


def weakest_phase(model: CircuitModel, voltages: list[Phases], index: int) -> int:
    consumer = model.consumers[index]
    if consumer.phase_mode != PhaseMode.THREE_PHASE:
        return consumer.phase_no - 1
    lowest, chosen = ABSENT_V, 0
    for phase, value in enumerate(own_phases(model, voltages, index)):
        if value < lowest:
            lowest, chosen = value, phase
    return chosen


def network_lowest(model: CircuitModel, voltages: list[Phases], worst: int) -> float:
    phases = own_phases(model, voltages, worst)
    consumer = model.consumers[worst]
    if consumer.phase_mode == PhaseMode.THREE_PHASE:
        return min(phases)
    return phases[consumer.phase_no - 1]


def weakest_on_feeder(model: CircuitModel, voltages: list[Phases], index: int, phase: int) -> int:
    target = model.consumers[index]
    lowest = own_phases(model, voltages, index)[phase]
    chosen = index
    for other, consumer in enumerate(model.consumers):
        if other == index or consumer.feeder_no != target.feeder_no:
            continue
        value = own_phases(model, voltages, other)[phase]
        same_phase = consumer.phase_mode == PhaseMode.THREE_PHASE or consumer.phase_no == target.phase_no
        if same_phase and value < lowest:
            lowest, chosen = value, other
    return chosen


def extrapolate(first_p: float, second_p: float, first_margin: float, second_margin: float) -> float:
    spread = first_margin - second_margin
    if spread == 0 or not math.isfinite(spread):
        raise AllowedPowerError("Расчёт выполняется некорректно! Проверьте данные по нагрузкам!")
    return first_p + first_margin * (second_p - first_p) / spread


def transformer_reserve(model: CircuitModel, settings: CalculationSettings, base: CalculationResults,
                        season: int) -> float:
    curve = list(base.seasons[season].load_factor)
    start = max(curve)
    air = settings.transformer_air_summer if season == 0 else settings.transformer_air_winter
    for _ in range(GROWTH_STEPS_LIMIT):
        curve = [LOAD_GROWTH * value for value in curve]
        oil, winding, _ = _transformer_heating(model, air, curve)
        if max(oil) >= OIL_OVERLOAD or max(winding) >= WINDING_OVERLOAD:
            break
    else:
        raise AllowedPowerError("Расчёт выполняется некорректно! Проверьте данные по нагрузкам!")
    total_p = base.seasons[season].bus_p
    total_q = base.seasons[1].bus_q
    return (max(curve) - start) * model.transformer.sn_kva * 1000.0 * math.cos(math.atan(total_q / total_p))


def smallest_positive(values: list[float]) -> float:
    found = [value for value in values if 0 < value < 1e9]
    return min(found) if found else 0.0


def allowed_power(model: CircuitModel, settings: CalculationSettings, index: int,
                  base: CalculationResults | None = None) -> AllowedPower:
    if not 0 <= index < len(model.consumers):
        raise AllowedPowerError("Потребитель не найден")
    base = base or calculate(model, settings, 2, False)
    if set(base.seasons) != {0, 1}:
        raise AllowedPowerError("Допустимая мощность считается после расчёта по двум сезонам")
    season = 0 if base.seasons[0].consumer_p[index] > base.seasons[1].consumer_p[index] else 1
    first = base.seasons[season]
    resistance = _consumer_load(model, settings, index, season, True, False, [[], [], []])[0]
    first_p = REFERENCE_PHASE_V ** 2 / resistance
    phase = weakest_phase(model, first.phase_voltages, index)
    feeder_worst = weakest_on_feeder(model, first.phase_voltages, index, phase)
    limit = 1 - settings.voltage_loss_limit / 100.0
    first_floor = abs(complex(first.bus_voltages[phase])) * limit
    first_own = own_phases(model, first.phase_voltages, index)[phase]
    first_network = network_lowest(model, first.phase_voltages, first.lowest_consumer)
    first_feeder = own_phases(model, first.phase_voltages, feeder_worst)[phase]

    loaded = copy.deepcopy(model)
    second_p = first_p + STEP_KW * 1000.0
    loaded.consumers[index].load_type = ConsumerLoadType.INDIVIDUAL
    loaded.consumers[index].p_kw = second_p / 1000.0
    second = calculate(loaded, settings, 2, False).seasons[season]
    second_floor = abs(complex(second.bus_voltages[phase])) * limit
    second_own = own_phases(loaded, second.phase_voltages, index)[phase]
    second_network = network_lowest(loaded, second.phase_voltages, second.lowest_consumer)
    second_feeder = own_phases(loaded, second.phase_voltages, feeder_worst)[phase]

    candidates = [
        extrapolate(first_p, second_p, first_own - first_floor, second_own - second_floor),
        extrapolate(first_p, second_p, first_network - first_floor, second_network - second_floor),
        extrapolate(first_p, second_p, first_feeder - first_floor, second_feeder - second_floor),
        transformer_reserve(model, settings, base, 0),
        transformer_reserve(model, settings, base, 1),
    ]
    by_transformer = smallest_positive(candidates[3:])
    if by_transformer == 0:
        raise AllowedPowerError("Расчёт выполняется некорректно! Проверьте данные по нагрузкам!")
    return AllowedPower(smallest_positive(candidates[:3]), by_transformer, season, candidates)
