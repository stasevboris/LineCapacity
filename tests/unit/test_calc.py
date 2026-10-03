from __future__ import annotations

import json
import math
import time
from dataclasses import replace

import numpy as np
import pytest

from linecapacity.model import Line as CoreLine
from linecapacity.settings import CalculationSettings
from linecapacity.solver import calculate
from tests.helpers import ROOT, SCHEMES, act, point
from voltplan.calc.bridge import to_model
from voltplan.calc.results import (
    current_text,
    extra_load_marks,
    outside,
    overheated,
    plain,
    report,
    run,
    transformer_state,
    voltage_text,
)
from voltplan.exchange import cir
from voltplan.scheme.editor import EditError


def sample(stem: str):
    return cir.load_bytes(next(p for p in SCHEMES if p.stem.startswith(stem)).read_bytes())


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_every_sample_is_calculated(path):
    scheme = cir.load_bytes(path.read_bytes())
    result = run(scheme)
    json.dumps(result)
    assert set(result["seasons"]) == {"0", "1"}
    for key in ("0", "1"):
        labels = result["labels"][key]
        assert len(labels["consumers"]) == len(scheme.consumers)
        assert len(labels["lines"]) == len(scheme.lines)
        assert len(labels["bus"]) == 3 and len(labels["sums"]) == 3
    assert len(result["memo"]["lines"]) == len(scheme.lines)
    assert len(result["memo"]["consumers"]) == len(scheme.consumers)
    assert result["report"][-2]["text"] == "Заключение о пропускной способности сети:"
    assert result["show_report"] == (len(scheme.consumers) > 1)


def test_kamenka_report_matches_linecapacity_text():
    rows = [row["text"] for row in run(sample("Каменка"))["report"]]
    assert rows[2] == "Значение минимального напряжения: 210,5 В"
    assert rows[5] == "Потери мощности в ЛЭП: 1,31 кВт (5,32%)"
    assert "Внимание! Недопустимая температура провода!" not in rows[13:24]
    assert rows[24:27] == ["Расчёт в режиме минимальных нагрузок:",
                           "Максимальное напряжение у потребителя с адресом: ул. Полевая, д.7",
                           "Значение максимального напряжения: 230,9 В"]
    assert rows[-1] == "Пропускная способность сети недостаточна!"


def test_equal_values_pick_the_first_object():
    result = run(sample("Болсуны"))
    assert result["min_load_mode"]["max_consumer"] == 7


@pytest.mark.parametrize("period, seasons", [(0, {"0"}), (1, {"1"}), (2, {"0", "1"})])
def test_period_choice(period, seasons):
    result = run(sample("Каменка"), period, False)
    assert set(result["seasons"]) == seasons
    assert result["min_load_mode"] is None and "2" not in result["labels"]


def test_memo_follows_linecapacity_windows():
    result = run(sample("Каменка"))
    assert result["memo"]["transformer"][0] == "Летний период:"
    assert result["memo"]["transformer"][1].startswith("U1= ")
    consumer = result["memo"]["consumers"][0]
    assert consumer[0] == "Летний период:" and "Режим минимальных нагрузок:" in consumer
    line = result["memo"]["lines"][0]
    assert line[1].startswith("Ток в фазном проводе L1: ") and line[1].endswith(" А")


def test_scheme_without_consumers_is_refused(new_scheme):
    with pytest.raises(EditError, match="отсутствуют потребители"):
        run(new_scheme)


def test_scheme_with_free_line_end_is_refused(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70))
    scheme = act(scheme, kind="span", point=point(193, 70))
    scheme = act(scheme, kind="delete", target="pole", index=1)
    with pytest.raises(EditError, match="неприсоединённые ЛЭП"):
        run(scheme)


def raised_voltage():
    return act(sample("Гатское"), kind="update", target="transformer", index=0,
               fields={"pbv_step": -2, "pbv_percent": 5.0})


def test_voltage_warning_does_not_change_conclusion():
    rows = [row["text"] for row in run(raised_voltage())["report"]]
    assert "Внимание! Недопустимо высокое напряжение у потребителя!" in rows
    assert rows[-1] == "Пропускная способность сети достаточна!"


def test_plain_turns_special_numbers_into_null():
    assert plain({"a": [math.inf, np.float64(-math.inf), math.nan, np.float64(1.5)]}) == {"a": [None, None, None, 1.5]}


def test_largest_scheme_is_calculated_quickly():
    scheme = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "крупная-299.cir").read_bytes())
    assert (len(scheme.poles), len(scheme.lines), len(scheme.consumers)) == (299, 897, 598)
    started = time.perf_counter()
    result = run(scheme)
    assert time.perf_counter() - started < 3
    assert len(result["memo"]["lines"]) == 897


def kamenka_results():
    scheme = sample("Каменка")
    model = to_model(scheme)
    return scheme, model, calculate(model, CalculationSettings())


@pytest.mark.parametrize("oil, winding, wear, state", [
    (95.0, 98.0, 0.5, "Трансформатор работает без перегрузки!"),
    (95.1, 60.0, 23.99, "Трансформатор работает с кратковременной (допустимой) перегрузкой!"),
    (60.0, 98.1, 24.0, "Внимание! Трансформатор работает с длительной перегрузкой!"),
    (115.1, 60.0, 0.5, "Внимание! Недопустимая температура трансформатора!"),
    (60.0, 140.1, 0.5, "Внимание! Недопустимая температура трансформатора!"),
])
def test_transformer_state_thresholds(oil, winding, wear, state):
    _, _, results = kamenka_results()
    season = replace(results.seasons[1], oil_peak=oil, winding_peak=winding, wear_hours=wear)
    assert transformer_state(season)[0] == state


@pytest.mark.parametrize("loss, alarm", [(7.99, False), (8.0, True)])
def test_voltage_loss_limit_is_inclusive(loss, alarm):
    scheme, model, results = kamenka_results()
    for number in results.season_order:
        results.seasons[number] = replace(results.seasons[number], voltage_loss_percent=loss,
                                          hottest_temperature=30.0, oil_peak=40.0, winding_peak=40.0)
    rows, good = report(scheme, model, CalculationSettings(), results, False)
    texts = [row["text"] for row in rows]
    assert ("Внимание! Недопустимо высокие потери напряжения!" in texts) is alarm
    assert good is not alarm


def test_short_overload_keeps_capacity_sufficient():
    scheme, model, results = kamenka_results()
    for number in results.season_order:
        results.seasons[number] = replace(results.seasons[number], voltage_loss_percent=1.0,
                                          hottest_temperature=30.0, oil_peak=96.0, winding_peak=60.0,
                                          wear_hours=10.0)
    rows, good = report(scheme, model, CalculationSettings(), results, False)
    assert good and rows[-1]["text"] == "Пропускная способность сети достаточна!"


@pytest.mark.parametrize("current, text", [(0.000999, "0,000"), (0.001, "0,001"), (12.3456, "12,346")])
def test_current_display_threshold(current, text):
    assert current_text(complex(current, 0)) == text


@pytest.mark.parametrize("voltage, text", [(0.0999, "0,0"), (0.1, "0,1"), (230.44, "230,4")])
def test_voltage_display_threshold(voltage, text):
    assert voltage_text(voltage) == text


def refusal(scheme) -> str:
    with pytest.raises(EditError) as refused:
        run(scheme)
    return str(refused.value)


def test_consumer_outside_lines_is_refused():
    scheme = sample("Каменка")
    scheme.consumers[3].x += 1
    assert refusal(scheme) == "В схеме имеются потребители, не присоединённые к ЛЭП! Расчёт не запущен!"


def test_pole_without_feeding_line_is_refused():
    scheme = sample("Каменка")
    scheme.poles[5].x += 1
    assert refusal(scheme) == "В схеме имеются опоры без питающей ЛЭП! Расчёт не запущен!"


def test_line_outside_poles_is_refused():
    scheme = sample("Каменка")
    line = next(line for line in scheme.lines if line.line_type == 1)
    line.x += 1
    assert refusal(scheme) == f"ЛЭП «{line.label}» не начинается на опоре! Расчёт не запущен!"


def test_mark_without_section_is_refused():
    scheme = sample("Каменка")
    scheme.lines[2].type_name = "СИП 4х"
    assert refusal(scheme) == (f"В марке провода «СИП 4х» ЛЭП «{scheme.lines[2].label}» нет сечения жилы! "
                               "Расчёт не запущен!")


def test_individual_load_with_zero_cos_is_refused():
    scheme = sample("Каменка")
    scheme.consumers[0].load_type = 1
    scheme.consumers[0].cos_phi = 0.0
    assert refusal(scheme) == (f"У потребителя «{scheme.consumers[0].label}» с индивидуальной нагрузкой cos φ "
                               "не больше нуля! Расчёт не запущен!")


def test_broken_large_scheme_is_refused_before_calculation():
    scheme = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "крупная-299.cir").read_bytes())
    scheme.consumers[-1].y += 3
    started = time.perf_counter()
    refusal(scheme)
    assert time.perf_counter() - started < 0.5


def test_zero_load_gives_zero_phase_shares():
    scheme = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "нулевая-нагрузка.cir").read_bytes())
    rows = [row["text"] for row in run(scheme)["report"]]
    shares = [row for row in rows if row.startswith("Распределение активной мощности")]
    assert shares and all(row.endswith("L1: 0,0%; L2: 0,0%; L3: 0,0%") for row in shares)


def test_dry_transformer_charts_have_no_oil():
    dry = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "один-однофазный-сухой.cir").read_bytes())
    oil = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "разные-типы.cir").read_bytes())
    assert "ТС" in dry.transformer.type_name and "ТС" not in oil.transformer.type_name
    assert all(chart["oil"] is None for chart in run(dry)["charts"].values())
    assert all(len(chart["oil"]) == 48 for chart in run(oil)["charts"].values())


@pytest.mark.parametrize("mark, below, above", [
    ("А 35", 70.0, 70.01), ("АС 35/6,2", 70.0, 70.01), ("СИП-2 3х35+1х54,6", 90.0, 90.01),
    ("АПвП 2х16", 90.0, 90.01), ("ВВГ 4х2.5", 70.0, 70.01), ("АВВГ 4х16", 70.0, 70.01),
])
def test_wire_temperature_limits_follow_insulation(mark, below, above):
    line = CoreLine(type_name=mark)
    assert not overheated(line, below)
    assert overheated(line, above)


@pytest.mark.parametrize("voltage, red", [(197.99, True), (198.0, False), (242.0, False), (242.01, True)])
def test_voltage_label_turns_red_outside_limits(voltage, red):
    assert outside(voltage, CalculationSettings()) is red


def test_extra_load_note_only_for_single_phase_consumers():
    scheme = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "один-трёхфазный.cir").read_bytes())
    model = to_model(scheme)
    targets = calculate(model, CalculationSettings()).extra_load_targets
    assert targets[0][scheme.consumers[0].feeder_no] == 0
    assert extra_load_marks(model, CalculationSettings(), targets) == [False]
    memo = run(scheme)["memo"]["consumers"][0]
    assert "Потребителю добавлена мощность утяжеления!" not in memo
