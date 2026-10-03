from __future__ import annotations

import cmath
import math
from dataclasses import replace

import pytest

from linecapacity.constants import (
    ALUMINIUM_TEMP_COEFF,
    HALF_HOURS,
    OIL_RISE_RATED,
    OIL_TIME_CONSTANT_S,
    STEP_S,
    WEAR_REFERENCE_TEMP,
    WIRE_HEATING_ALLOWANCE,
)
from linecapacity.model import ConsumerCategory, InsulationType, Line, LineType, PhaseMode
from linecapacity.settings import CalculationSettings
from linecapacity.solver import calculate
from tests.helpers import SCHEMES
from tests.sequences import TRANSFORMER, build, drop_one, drop_three, house, pole, shop, tap, trunk
from voltplan.calc.bridge import to_model
from voltplan.exchange import cir

SETTINGS = CalculationSettings()
SEASONS = {0: SETTINGS.line_air_summer, 1: SETTINGS.line_air_winter}


def feeder(drop: dict, consumer: dict):
    steps = [
        lambda s: {"kind": "new", "transformer": TRANSFORMER, "line": trunk("Л-1", 40), "pole": pole("1", 1)},
        lambda s: {"kind": "branch_consumer", "point": tap(s, "1", 1), "line": drop, "consumer": consumer},
    ]
    return to_model(build(steps)[-1][1])


def source_emf(model) -> float:
    return SETTINGS.high_voltage_kv * 1e3 / (model.transformer.kt * math.sqrt(3))


def wire(line, season: int, resistance: float) -> float:
    base = 20 if line.insulation() == InsulationType.NONE else 25
    branch = line.line_type in (LineType.BRANCH_TO_LINE, LineType.BRANCH_TO_CONSUMER)
    contact = SETTINGS.contact_resistance_ohm if branch else 0.0
    return resistance * (1 + ALUMINIUM_TEMP_COEFF * (SEASONS[season] + WIRE_HEATING_ALLOWANCE - base)) + contact


def load_impedance(p_kw: float, cos_phi: float, phases: int) -> complex:
    q_kvar = math.sqrt((p_kw / cos_phi) ** 2 - p_kw ** 2)
    scale = phases * SETTINGS.voltage_rated ** 2 / 1e3
    return 1 / complex(p_kw / scale, -q_kvar / scale)


def test_bus_power_counts_as_many_outgoing_lines_as_the_scheme_declares():
    scheme = cir.load_bytes((SCHEMES[0].parents[1] / "tests" / "data" / "calc" / "два-фидера.cir").read_bytes())
    assert scheme.outgoing_count == 2
    quiet = replace(CalculationSettings(), extra_load_enabled=False)
    both = calculate(to_model(scheme), quiet, 1, False)
    both = both.seasons[both.season_order[0]]
    first = calculate(to_model(scheme.model_copy(update={"outgoing_count": 1})), quiet, 1, False)
    first = first.seasons[first.season_order[0]]
    assert [abs(value) for value in first.bus_voltages] == pytest.approx([abs(value) for value in both.bus_voltages])
    assert 0 < first.bus_p < both.bus_p
    assert sum(first.phase_p) == pytest.approx(first.bus_p)


@pytest.mark.parametrize("season", [0, 1])
def test_symmetric_load_matches_series_circuit(season):
    model = feeder(drop_three("Л-2", 20), shop("1", "ул. Одна, 1", 10.0))
    result = calculate(model, SETTINGS, season, False).seasons[season]
    transformer = complex(model.transformer.r_ohm, model.transformer.x_ohm)
    lines = sum(wire(line, season, line.r_phase_ohm) for line in model.lines)
    load = load_impedance(10.0, 0.95, 3)
    current = source_emf(model) / (transformer + lines + load)
    for value in result.phase_voltages[0]:
        assert value == pytest.approx(abs(current * load), rel=1e-9)
    for offset in (0, 4):
        assert [abs(i) for i in result.wire_currents[offset:offset + 3]] == pytest.approx([abs(current)] * 3, rel=1e-9)
        assert abs(result.wire_currents[offset + 3]) < 1e-6


@pytest.mark.parametrize("phase", [1, 2, 3])
def test_single_phase_load_closes_through_neutral(phase):
    model = feeder(drop_one("Л-2", 25, phase), shop("1", "ул. Одна, 1", 3.0))
    result = calculate(model, SETTINGS, 0, False).seasons[0]
    trunk_line, drop = model.lines
    loop = (complex(model.transformer.r_ohm, model.transformer.x_ohm)
            + wire(trunk_line, 0, trunk_line.r_phase_ohm) + wire(trunk_line, 0, trunk_line.r_neutral_ohm)
            + 2 * wire(drop, 0, drop.r_phase_ohm) + load_impedance(3.0, 0.95, 1))
    current = source_emf(model) / loop
    voltage = abs(current * load_impedance(3.0, 0.95, 1))
    assert result.phase_voltages[0][phase - 1] == pytest.approx(voltage, rel=1e-9)
    trunk_currents = [abs(i) for i in result.wire_currents[0:4]]
    assert trunk_currents[phase - 1] == pytest.approx(abs(current), rel=1e-9)
    assert trunk_currents[3] == pytest.approx(abs(current), rel=1e-9)
    assert sum(trunk_currents[:3]) - trunk_currents[phase - 1] < 1e-6
    assert [abs(i) for i in result.wire_currents[4:6]] == pytest.approx([abs(current)] * 2, rel=1e-9)


def test_zero_load_leaves_no_load_voltage():
    model = feeder(drop_three("Л-2", 20), shop("1", "ул. Одна, 1", 0.0))
    result = calculate(model, SETTINGS, 0, False).seasons[0]
    assert list(result.phase_voltages[0]) == pytest.approx([source_emf(model)] * 3, rel=1e-9)
    assert max(abs(i) for i in result.wire_currents) < 1e-9
    assert result.wire_temperatures == pytest.approx([SEASONS[0]] * 2)


def test_idle_transformer_heats_by_exponent_from_cold():
    model = feeder(drop_three("Л-2", 20), shop("1", "ул. Одна, 1", 0.0))
    result = calculate(model, SETTINGS, 0, False).seasons[0]
    ratio = model.transformer.pk_kw / model.transformer.px_kw
    steady = OIL_RISE_RATED * (1 / (1 + ratio)) ** 0.9
    step = math.exp(-STEP_S / OIL_TIME_CONSTANT_S)
    oil = [SETTINGS.transformer_air_summer + steady * (1 - step ** (HALF_HOURS + i + 1)) for i in range(HALF_HOURS)]
    assert max(result.load_factor) < 1e-6
    assert result.oil_temps == pytest.approx(oil, rel=1e-9)
    assert result.winding_temps == pytest.approx(oil, rel=1e-9)
    wear = 24 / HALF_HOURS * sum(2 ** ((value - WEAR_REFERENCE_TEMP) / 6) for value in oil)
    assert result.wear_hours == pytest.approx(wear, rel=1e-9)


@pytest.mark.parametrize("path", SCHEMES[:6], ids=[p.stem for p in SCHEMES[:6]])
def test_bus_power_equals_consumers_plus_line_losses(path):
    model = to_model(cir.load_bytes(path.read_bytes()))
    results = calculate(model, SETTINGS)
    for number in results.season_order:
        season = results.seasons[number]
        losses = 0.0
        position = 0
        for line in model.lines:
            single = line.phase_mode == PhaseMode.SINGLE_PHASE and line.line_type == LineType.BRANCH_TO_CONSUMER
            resistances = [line.r_phase_ohm] * 2 if single else [line.r_phase_ohm] * 3 + [line.r_neutral_ohm]
            for offset, resistance in enumerate(resistances):
                losses += abs(season.wire_currents[position + offset]) ** 2 * wire(line, number, resistance)
            position += len(resistances)
        assert season.bus_p == pytest.approx(sum(season.consumer_p) + losses, rel=1e-6)
        assert season.line_loss_kw == pytest.approx(losses / 1000, rel=1e-6)


def test_minimal_load_raises_voltage_of_symmetric_load():
    model = feeder(drop_three("Л-2", 20), house("1", "ул. Одна, 1", 1293))
    results = calculate(model, SETTINGS)
    minimal = results.min_load_voltages[0]
    for number in (0, 1):
        assert all(high > low for high, low in zip(minimal, results.seasons[number].phase_voltages[0],
                                                   strict=True))


def test_unknown_consumer_type_draws_no_power():
    model = feeder(drop_one("Л-2", 25, 1), house("1", "ул. Одна, 1", 1500))
    model.consumers[0].category = 49.894
    result = calculate(model, SETTINGS, 0, False).seasons[0]
    assert result.consumer_p[0] < 1e-6
    model.consumers[0].category = ConsumerCategory.HOUSEHOLD_NO_CIE
    assert calculate(model, SETTINGS, 0).seasons[0].consumer_p[0] > 1000


@pytest.mark.parametrize("heavy", [True, False])
@pytest.mark.parametrize("annual", [1293, 2586])
def test_household_load_scales_with_annual_consumption(annual, heavy):
    settings = replace(SETTINGS, extra_load_enabled=heavy)
    model = feeder(drop_three("Л-2", 20), house("1", "ул. Одна, 1", annual))
    seasons = calculate(model, settings).seasons
    extra = settings.extra_load_kw if heavy else 0.0
    for number, nominal in ((0, settings.home_summer_kw), (1, settings.home_winter_kw)):
        power = nominal * annual / settings.home_annual_kwh + extra
        expected = 3 * settings.voltage_rated ** 2 / (power * 1e3)
        assert seasons[number].load_impedances[0][0] == pytest.approx(expected, rel=1e-12)
        assert seasons[number].extra_load_w == pytest.approx(extra * 1e3)


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_bridge_keeps_every_field(path):
    scheme = cir.load_bytes(path.read_bytes())
    model = to_model(scheme)
    pairs = [(scheme.transformer, model.transformer)] + list(zip(scheme.lines, model.lines, strict=True))
    pairs += list(zip(scheme.poles, model.poles, strict=True)) + list(zip(scheme.consumers, model.consumers,
                                                                          strict=True))
    pairs += list(zip(scheme.connection_points, model.connection_points, strict=True))
    for source, target in pairs:
        for name, value in source.model_dump().items():
            assert getattr(target, name) == value, name


def test_complex_form_of_voltage_is_consistent():
    model = feeder(drop_three("Л-2", 20), shop("1", "ул. Одна, 1", 10.0))
    result = calculate(model, SETTINGS, 0, False).seasons[0]
    angles = [math.degrees(cmath.phase(u)) for u in result.bus_voltages]
    assert (angles[1] - angles[0]) % 360 == pytest.approx(240, abs=1e-6)
    assert (angles[2] - angles[0]) % 360 == pytest.approx(120, abs=1e-6)


@pytest.mark.parametrize("mark, section, cores", [
    ("А 35", 35.0, 4), ("СИП-4 4х16", 16.0, 4), ("ВВГ 4х2.5", 2.5, 4), ("ВВГ 3х2,5+1х1,5", 2.5, 4),
    ("СИП-2 3х35+1х54,6", 35.0, 4), ("АПвП 2х16", 16.0, 2), ("АС50", 0.0, 4), ("СИП 4х", None, 4),
    ("СИП-2 Аx50", 50.0, 0), ("А", 0.0, 0),
])
def test_mark_is_read_like_linecapacity(mark, section, cores):
    line = Line(type_name=mark)
    assert line.section_mm2() == section
    assert line.cores() == cores
