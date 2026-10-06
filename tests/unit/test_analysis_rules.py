from __future__ import annotations

from types import SimpleNamespace

import pytest

from linecapacity.allowed import weakest_on_feeder
from linecapacity.model import ConsumerCategory, PhaseMode
from linecapacity.settings import CalculationSettings
from linecapacity.solver import MINIMAL_SEASON, NEGLIGIBLE_KW, _standard_load
from tests.helpers import ROOT
from voltplan.calc import compare as compare_module
from voltplan.calc.compare import compare, gost_quality, variant_row
from voltplan.calc.losses import annual_losses, loss_hours
from voltplan.exchange import cir
from voltplan.scheme.editor import EditError


def consumer(phase_mode=PhaseMode.THREE_PHASE, phase_no=1, feeder_no=0, address="д.1"):
    return SimpleNamespace(phase_mode=phase_mode, phase_no=phase_no, feeder_no=feeder_no, address=address, label="",
                           annual_kwh=0.0)


def quality(voltages: list[tuple[float, float, float]], consumers=None) -> dict:
    model = SimpleNamespace(consumers=consumers or [consumer() for _ in voltages])
    results = SimpleNamespace(season_order=[0], seasons={0: SimpleNamespace(phase_voltages=voltages)},
                              min_load_voltages=None)
    return gost_quality(model, results, CalculationSettings())


def test_gost_limit_is_ten_percent_of_220_volts_on_both_sides():
    assert CalculationSettings().voltage_rated == 220
    assert quality([(198.0, 220.0, 242.0)])["ok"] is True
    assert quality([(197.97, 220.0, 220.0)])["ok"] is False
    assert quality([(220.0, 242.03, 220.0)])["ok"] is False
    edge = quality([(198.0, 230.0, 220.0)])["consumers"][0]
    assert edge["low_percent"] == pytest.approx(-10.0) and edge["high_percent"] == pytest.approx(100 / 22)


def test_single_phase_consumer_is_judged_by_its_own_phase():
    single = consumer(PhaseMode.SINGLE_PHASE, phase_no=2)
    assert quality([(150.0, 221.0, 150.0)], [single])["ok"] is True
    assert quality([(221.0, 150.0, 221.0)], [single])["ok"] is False


def row(name, good=True, ok=True, voltage=210.0, loss=1.0, **rest):
    return {"name": name, "error": None, "good": good, "quality": {"ok": ok}, "min_voltage": voltage,
            "loss_kw": loss, **rest}


@pytest.mark.parametrize("rows, best", [
    ([row("А", good=False, voltage=230.0, loss=0.1), row("Б", voltage=200.0, loss=3.0)], 1),
    ([row("А", ok=False, voltage=230.0, loss=0.1), row("Б", voltage=200.0, loss=3.0)], 1),
    ([row("А", voltage=205.0, loss=0.1), row("Б", voltage=206.0, loss=3.0)], 1),
    ([row("А", voltage=206.0, loss=0.9), row("Б", voltage=206.0, loss=0.8)], 1),
    ([row("А", voltage=206.0, loss=0.8), row("Б", voltage=206.0, loss=0.8)], 0),
])
def test_best_variant_follows_the_four_rules_in_order(rows, best):
    assert compare(rows)["best"] == best


def test_best_values_mark_highest_voltage_and_lowest_losses():
    rows = [row("А", voltage=205.0, loss=0.5, annual_kwh=900.0), row("Б", voltage=207.0, loss=0.7, annual_kwh=800.0),
            {"name": "В", "error": "схема пуста"}]
    marks = compare(rows)["best_values"]
    assert marks["min_voltage"] == 207.0 and marks["loss_kw"] == 0.5 and marks["annual_kwh"] == 800.0


def test_loss_hours_formula():
    assert loss_hours(3000.0) == pytest.approx((0.124 + 0.3) ** 2 * 8760.0)
    assert loss_hours(5000.0) == pytest.approx(0.624 ** 2 * 8760.0)


def test_annual_losses_on_known_numbers():
    model = SimpleNamespace(consumers=[SimpleNamespace(annual_kwh=30000.0), SimpleNamespace(annual_kwh=10000.0)],
                            transformer=SimpleNamespace(px_kw=0.5, pk_kw=2.0))
    season = SimpleNamespace(bus_p=10000.0, extra_load_w=0.0, line_loss_kw=0.4, load_factor=[0.5, 0.4, 0.3])
    results = SimpleNamespace(season_order=[0], seasons={0: season})
    data = annual_losses(model, results, 0.1)
    hours = (0.124 + 4000.0 / 1e4) ** 2 * 8760.0
    assert data["use_hours"] == pytest.approx(4000.0) and data["loss_hours"] == pytest.approx(hours)
    assert data["lines_kwh"] == pytest.approx(0.4 * hours)
    assert data["transformer_idle_kwh"] == pytest.approx(0.5 * 8760.0)
    assert data["transformer_load_kwh"] == pytest.approx(2.0 * 0.25 * hours)
    assert data["cost_usd"] == pytest.approx(data["total_kwh"] * 0.1)


def test_annual_peak_does_not_count_the_weighting_load():
    model = SimpleNamespace(consumers=[SimpleNamespace(annual_kwh=24000.0)],
                            transformer=SimpleNamespace(px_kw=0.0, pk_kw=0.0))
    season = SimpleNamespace(bus_p=13000.0, extra_load_w=5000.0, line_loss_kw=0.1, load_factor=[0.3])
    data = annual_losses(model, SimpleNamespace(season_order=[0], seasons={0: season}), 0.1)
    assert data["peak_kw"] == pytest.approx(8.0) and data["use_hours"] == pytest.approx(3000.0)


@pytest.mark.parametrize("bus_p, extra", [(-10350.0, 0.0), (5000.0, 5000.0)])
def test_annual_losses_refuse_a_network_without_positive_peak(bus_p, extra):
    model = SimpleNamespace(consumers=[], transformer=SimpleNamespace(px_kw=0.5, pk_kw=2.0))
    season = SimpleNamespace(bus_p=bus_p, extra_load_w=extra, line_loss_kw=0.1, load_factor=[0.3])
    with pytest.raises(EditError, match="наибольшая нагрузка сети"):
        annual_losses(model, SimpleNamespace(season_order=[0], seasons={0: season}), 0.1)


def test_comparison_shows_no_annual_losses_when_they_are_refused(monkeypatch):
    scheme = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "разные-типы.cir").read_bytes())
    normal = variant_row("А", scheme, CalculationSettings(), 2, False, 0.1)
    assert normal["annual_kwh"] > 0

    def refuse(*_):
        raise EditError("наибольшая нагрузка сети получилась не больше нуля")

    monkeypatch.setattr(compare_module, "annual_losses", refuse)
    refused = variant_row("Б", scheme, CalculationSettings(), 2, False, 0.1)
    assert refused["error"] is None and refused["annual"] is None
    assert refused["annual_kwh"] is None and refused["annual_cost_usd"] is None
    marks = compare([normal, refused])["best_values"]
    assert marks["annual_kwh"] == normal["annual_kwh"]


def test_allowed_power_looks_only_at_same_phase_consumers_of_the_feeder():
    target = consumer(PhaseMode.THREE_PHASE, phase_no=1)
    other_phase = consumer(PhaseMode.SINGLE_PHASE, phase_no=3)
    same_phase = consumer(PhaseMode.SINGLE_PHASE, phase_no=1)
    foreign = consumer(feeder_no=1)
    model = SimpleNamespace(consumers=[target, other_phase, same_phase, foreign])
    voltages = [(215.0, 214.0, 205.0), (0.0, 0.0, 190.0), (200.0, 0.0, 0.0), (150.0, 150.0, 150.0)]
    assert weakest_on_feeder(model, voltages, 0, 2) == 0
    assert weakest_on_feeder(model, voltages, 0, 0) == 2


def test_typical_loads_take_their_own_settings():
    settings = CalculationSettings(home_summer_kw=1.1, home_winter_kw=1.3, home_minimal_kw=0.7,
                                   electric_home_summer_kw=2.1, electric_home_winter_kw=2.3,
                                   electric_home_minimal_kw=0.9, street_light_summer_kw=0.11,
                                   street_light_winter_kw=0.13, home_summer_cos=0.91, home_winter_cos=0.81,
                                   electric_home_summer_cos=0.92, electric_home_winter_cos=0.82,
                                   street_light_summer_cos=0.93, street_light_winter_cos=0.83)
    loads = {season: {category: _standard_load(settings, category, season, 2.0, 8760.0, 0.5)
                      for category in ConsumerCategory} for season in (0, 1, MINIMAL_SEASON)}
    home, electric, light, other = ConsumerCategory
    assert loads[0] == {home: (2.7, 0.91), electric: (4.2, 0.92), light: (0.22, 0.93), other: (1.0, 0.81)}
    assert loads[1] == {home: (3.1, 0.81), electric: (4.6, 0.82), light: (0.26, 0.83), other: (1.0, 0.81)}
    assert loads[MINIMAL_SEASON] == {home: (1.4, 0.81), electric: (1.8, 0.82), light: (NEGLIGIBLE_KW, 0.83),
                                     other: (NEGLIGIBLE_KW, 0.81)}
