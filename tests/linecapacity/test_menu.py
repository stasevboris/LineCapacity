from __future__ import annotations

import subprocess
import sys

import pytest

from linecapacity.settings import CalculationSettings
from tests import menu_cases as cases
from tests.compare import compare_report, explain
from tests.helpers import ROOT
from tests.linecapacity import calc_menu
from tests.linecapacity.driver import LineCapacity, find_exe
from voltplan.calc import settings as calc_settings
from voltplan.calc.results import run
from voltplan.calc.tools import allowed, assign_load_kind, spread
from voltplan.exchange import cir
from voltplan.exchange.meters import apply_period, read_table

pytestmark = pytest.mark.linecapacity

EXE = find_exe()
OUT = ROOT / "logs" / "linecapacity" / "меню"
RECORDED = cases.recorded()


@pytest.fixture(scope="module", autouse=True)
def windows_only():
    if sys.platform != "win32":
        pytest.skip("LineCapacity работает только в Windows")
    if EXE is None:
        pytest.skip("укажите путь к LineCapacity.exe в переменной LINECAPACITY_EXE")
    pytest.importorskip("pywinauto")
    OUT.mkdir(parents=True, exist_ok=True)


def load(path: str):
    return cir.load_bytes((ROOT / path).read_bytes())


def texts(result: dict) -> list[str]:
    return [row["text"] for row in result["report"]]


def saved(program, name: str) -> bytes:
    path = OUT / f"{name}-linecapacity.cir"
    program.save_as(path)
    return path.read_bytes()


def excel_processes() -> set[int]:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq EXCEL.EXE", "/FO", "CSV", "/NH"], capture_output=True,
                         text=True, encoding="cp866").stdout
    return {int(line.split('","')[1]) for line in out.splitlines() if line.startswith('"EXCEL')}


@pytest.mark.parametrize("case", RECORDED["load_kind"], ids=[case["name"] for case in RECORDED["load_kind"]])
def test_load_kind_matches_linecapacity(case):
    with LineCapacity(EXE) as program:
        assert program.open(ROOT / case["scheme"]) == []
        message = calc_menu.load_kind(program, case["typical"])
        theirs = saved(program, case["name"])
    assert message == case["message"] and theirs == (ROOT / case["file"]).read_bytes(), "запись устарела"
    ours, text = assign_load_kind(load(case["scheme"]), case["typical"])
    assert text == message and cir.dump_bytes(ours) == theirs


@pytest.mark.parametrize("case", RECORDED["meter"], ids=[case["name"] for case in RECORDED["meter"]])
def test_meter_matches_linecapacity(case):
    with LineCapacity(EXE) as program:
        assert program.open(ROOT / case["scheme"]) == []
        message = calc_menu.meter(program, case["p_kw"], case["q_kvar"], case["month"], case["by_annual"])
        theirs = saved(program, case["name"])
        report = program.calculate(case["period"], True)
        program.screenshot(OUT / f"{case['name']}.png")
    assert (message, theirs, report) == (case["message"], (ROOT / case["file"]).read_bytes(), case["report"]), \
        "запись устарела"
    ours, _, text = spread(load(case["scheme"]), CalculationSettings(), case["p_kw"], case["q_kvar"], case["month"],
                           case["by_annual"])
    assert text == message and cases.same_file(cir.dump_bytes(ours), theirs) == []
    problems, _ = compare_report(report, texts(run(ours, case["period"], True)), case["substitutions"])
    assert problems == []


@pytest.mark.parametrize("case", RECORDED["excel"], ids=[case["name"] for case in RECORDED["excel"]])
def test_excel_import_matches_linecapacity(case):
    before = excel_processes()
    try:
        with LineCapacity(EXE) as program:
            assert program.open(ROOT / case["scheme"]) == []
            message = calc_menu.excel(program, ROOT / case["book"], case["cos_phi"], case["air"])
            theirs = saved(program, case["name"])
            report = program.calculate(2, True)
    finally:
        for pid in excel_processes() - before:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    assert (message, theirs, report) == (case["message"], (ROOT / case["file"]).read_bytes(), case["report"]), \
        "запись устарела"
    result = apply_period(load(case["scheme"]), read_table((ROOT / case["book"]).read_bytes()), case["period"],
                          case["cos_phi"])
    assert "\n".join(result.messages) == message and cases.same_file(cir.dump_bytes(result.scheme), theirs) == []
    air = {0: "line_air_summer", 1: "line_air_winter"}[result.season]
    assert texts(run(result.scheme, 2, True, calc_settings.build({air: case["air"]}))) == report


@pytest.mark.parametrize("case", RECORDED["settings"], ids=[case["name"] for case in RECORDED["settings"]])
def test_changed_settings_match_linecapacity(case):
    scheme = load(case["scheme"])
    with LineCapacity(EXE) as program:
        assert program.open(ROOT / case["scheme"]) == []
        calc_menu.settings(program, case["values"])
        report = program.calculate(case["period"], case["min_load"])
        program.close_report()
        transformer = program.memo("transformer", scheme.transformer)
    assert (report, transformer) == (case["report"], case["memo"]["transformer"]), "запись устарела"
    ours = run(scheme, case["period"], case["min_load"], calc_settings.build(case["values"]))
    assert texts(ours) == report, explain(report, texts(ours))
    assert ours["memo"]["transformer"] == transformer


@pytest.mark.parametrize("case", RECORDED["allowed"], ids=[case["name"] for case in RECORDED["allowed"]])
def test_allowed_power_matches_linecapacity(case):
    scheme = load(case["scheme"])
    with LineCapacity(EXE) as program:
        assert program.open(ROOT / case["scheme"]) == []
        program.calculate(2, True)
        program.close_report()
        rows, memo = calc_menu.allowed(program, scheme.consumers[case["consumer"]])
    assert (rows, memo[-4:]) == (case["report"], case["memo"]), "запись устарела"
    found = allowed(scheme, CalculationSettings(), case["consumer"])
    assert found["report"] == rows and found["memo"] == memo[-4:]
