from __future__ import annotations

import pytest

from linecapacity.settings import CalculationSettings
from tests import menu_cases as cases
from tests.compare import compare_report, explain
from tests.helpers import ROOT
from voltplan.calc import settings as calc_settings
from voltplan.calc.results import run
from voltplan.calc.tools import allowed, assign_load_kind, spread
from voltplan.exchange import cir
from voltplan.exchange.meters import apply_period, read_table

RECORDED = cases.recorded()


def load(path: str):
    return cir.load_bytes((ROOT / path).read_bytes())


def texts(result: dict) -> list[str]:
    return [row["text"] for row in result["report"]]


@pytest.mark.parametrize("case", RECORDED["load_kind"], ids=[case["name"] for case in RECORDED["load_kind"]])
def test_load_kind_gives_the_file_linecapacity_saved(case):
    scheme, message = assign_load_kind(load(case["scheme"]), case["typical"])
    assert message == case["message"]
    assert cir.dump_bytes(scheme) == (ROOT / case["file"]).read_bytes()


@pytest.mark.parametrize("case", RECORDED["meter"], ids=[case["name"] for case in RECORDED["meter"]])
def test_meter_gives_the_file_and_results_of_linecapacity(case):
    scheme, season, message = spread(load(case["scheme"]), CalculationSettings(), case["p_kw"], case["q_kvar"],
                                     case["month"], case["by_annual"])
    assert message == case["message"] and season == case["period"]
    assert cases.same_file(cir.dump_bytes(scheme), (ROOT / case["file"]).read_bytes()) == []
    problems, used = compare_report(case["report"], texts(run(scheme, case["period"], True)), case["substitutions"])
    assert problems == [] and used == case["substitutions"]


@pytest.mark.parametrize("case", RECORDED["excel"], ids=[case["name"] for case in RECORDED["excel"]])
def test_excel_import_gives_the_file_and_results_of_linecapacity(case):
    assert (ROOT / case["book"]).read_bytes()[:2] == b"PK"
    table = read_table((ROOT / case["book"]).read_bytes())
    result = apply_period(load(case["scheme"]), table, case["period"], case["cos_phi"])
    assert "\n".join(result.messages) == case["message"]
    assert cases.same_file(cir.dump_bytes(result.scheme), (ROOT / case["file"]).read_bytes()) == []
    air = {0: "line_air_summer", 1: "line_air_winter"}[result.season]
    report = texts(run(result.scheme, 2, True, calc_settings.build({air: case["air"]})))
    assert report == case["report"], explain(case["report"], report)


@pytest.mark.parametrize("case", RECORDED["settings"], ids=[case["name"] for case in RECORDED["settings"]])
def test_changed_settings_give_linecapacity_results(case):
    result = run(load(case["scheme"]), case["period"], case["min_load"], calc_settings.build(case["values"]))
    assert texts(result) == case["report"], explain(case["report"], texts(result))
    assert result["memo"]["transformer"] == case["memo"]["transformer"]


@pytest.mark.parametrize("case", RECORDED["allowed"], ids=[case["name"] for case in RECORDED["allowed"]])
def test_allowed_power_matches_linecapacity(case):
    found = allowed(load(case["scheme"]), CalculationSettings(), case["consumer"])
    assert found["report"] == case["report"]
    assert found["memo"] == case["memo"]


def test_recorded_cases_cover_every_menu_function():
    assert all(RECORDED[kind] for kind in cases.KINDS)
    assert {case["typical"] for case in RECORDED["load_kind"]} == {True, False}
    assert {case["by_annual"] for case in RECORDED["meter"]} == {True, False}


def test_substitutions_are_only_for_equal_values():
    listed = [item for case in RECORDED["meter"] for item in case["substitutions"]]
    assert listed and {item["reason"] for item in listed} == {"равные значения"}
