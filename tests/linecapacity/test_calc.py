from __future__ import annotations

import json
import sys

import pytest

from tests.compare import compare_report, explain, recorded, windows
from tests.helpers import ROOT, SCHEMES, act
from tests.linecapacity.driver import CalcRefused, LineCapacity, find_exe
from tests.sequences import SEQUENCES, build
from voltplan.calc.results import check_scheme, run
from voltplan.catalog import mark_rows
from voltplan.exchange import cir
from voltplan.scheme.editor import EditError

pytestmark = pytest.mark.linecapacity

EXE = find_exe()
OUT = ROOT / "logs" / "linecapacity" / "расчёт"
OBJECT_SAMPLES = ("Каменка", "Ботвиново", "Октябрь")
OBJECTS_PER_KIND = 3
CASES = recorded()
SAMPLE_CASES = {case["name"]: case for case in CASES if case["scheme"].startswith("schemes/")
                and case["period"] == 2 and case["min_load"]}
DERIVED = ("построено-", "повышенное-напряжение")
OWN_CASES = [case for case in CASES if case["scheme"].startswith("tests/") and not case["name"].startswith(DERIVED)]
KINDS = {"transformer": "transformer", "lines": "line", "consumers": "consumer"}


def refusal(name: str) -> str:
    try:
        check_scheme(build(SEQUENCES[name]())[-1][1])
    except EditError as error:
        return str(error)
    return ""


def consumers(name: str) -> int:
    return len(build(SEQUENCES[name]())[-1][1].consumers)


BUILT = [name for name in SEQUENCES if not refusal(name) and consumers(name) > 1]
SINGLE = [name for name in SEQUENCES if not refusal(name) and consumers(name) == 1]
REFUSED = [name for name in SEQUENCES if refusal(name)]


@pytest.fixture(scope="module", autouse=True)
def windows_only():
    if sys.platform != "win32":
        pytest.skip("LineCapacity работает только в Windows")
    if EXE is None:
        pytest.skip("укажите путь к LineCapacity.exe в переменной LINECAPACITY_EXE")
    pytest.importorskip("pywinauto")
    OUT.mkdir(parents=True, exist_ok=True)


def ours(scheme, period: int = 2, min_load: bool = True) -> list[str]:
    return [row["text"] for row in run(scheme, period, min_load)["report"]]


def case_for(name: str, period: int = 2, min_load: bool = True) -> dict:
    return next(case for case in CASES if case["name"] == name and (case["period"], case["min_load"]) ==
                (period, min_load))


def verify(case: dict, expected: list[str], actual: list[str], name: str) -> None:
    assert expected == case["report"], "записанный отчёт устарел"
    problems, used = compare_report(expected, actual, case["substitutions"])
    if used:
        (OUT / f"{name}-подстановки.txt").write_text(
            "\n".join(f"{item['reason']}: LineCapacity «{item['linecapacity']}» — VoltPlan «{item['voltplan']}»"
                      for item in used), encoding="utf-8")
    assert problems == [], "\n".join(problems)


def theirs(path, name: str, period: int = 2, min_load: bool = True) -> list[str]:
    with LineCapacity(EXE) as program:
        assert program.open(path) == []
        rows = program.calculate(period, min_load)
        program.screenshot(OUT / f"{name}.png")
    (OUT / f"{name}-linecapacity.txt").write_text("\n".join(rows), encoding="utf-8", newline="\n")
    return rows


def memo_of(program, scheme, kind: str, index: int | None) -> list[str]:
    obj = scheme.transformer if index is None else getattr(scheme, kind)[index]
    return program.memo(KINDS[kind], obj)


def ours_memo(result: dict, kind: str, index: int | None) -> list[str]:
    return result["memo"][kind] if index is None else result["memo"][kind][index]


def save_windows(name: str, checked: list[tuple[str, list[str]]]) -> None:
    (OUT / f"объекты-{name}.txt").write_text(
        "\n\n".join(f"{title}\n" + "\n".join(rows) for title, rows in checked), encoding="utf-8")


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_sample_report_matches_linecapacity(path):
    expected = theirs(path, f"образец-{path.stem}")
    actual = ours(cir.load_bytes(path.read_bytes()))
    verify(SAMPLE_CASES[path.stem], expected, actual, f"образец-{path.stem}")


@pytest.mark.parametrize("period, min_load", [(0, False), (1, False), (2, False), (0, True), (1, True)])
def test_period_and_min_load_choice(period, min_load):
    path = next(p for p in SCHEMES if p.stem.startswith("Каменка"))
    expected = theirs(path, f"вид-{period}-{int(min_load)}", period, min_load)
    actual = ours(cir.load_bytes(path.read_bytes()), period, min_load)
    case = next(case for case in CASES if case["scheme"].endswith("Каменка КТП158.cir")
                and (case["period"], case["min_load"]) == (period, min_load))
    verify(case, expected, actual, f"вид-{period}-{int(min_load)}")


@pytest.mark.parametrize("name", BUILT)
def test_scheme_built_in_voltplan_is_calculated_the_same(name):
    scheme = build(SEQUENCES[name]())[-1][1]
    case = case_for(f"построено-{name}")
    assert cir.dump_bytes(scheme) == (ROOT / case["scheme"]).read_bytes(), "записанная схема устарела"
    source = OUT / f"{name}-из-voltplan.cir"
    source.write_bytes(cir.dump_bytes(scheme))
    result = run(scheme)
    with LineCapacity(EXE) as program:
        assert program.open(source) == []
        rows = program.calculate()
        program.screenshot(OUT / f"построено-{name}.png")
        program.close_report()
        found = [(kind, index, memo_of(program, scheme, kind, index)) for kind, index, _ in windows(case)]
    (OUT / f"построено-{name}-linecapacity.txt").write_text("\n".join(rows), encoding="utf-8", newline="\n")
    save_windows(f"построено-{name}", [(f"{kind} {index}", rows) for kind, index, rows in found])
    verify(case, rows, [row["text"] for row in result["report"]], f"построено-{name}")
    stale = [f"{kind} {index}" for (kind, index, rows), (_, _, stored) in zip(found, windows(case), strict=True)
             if rows != stored]
    assert stale == [], "записанные окна устарели: " + ", ".join(stale)
    differ = [f"{kind} {index}: {explain(rows, ours_memo(result, kind, index))}"
              for kind, index, rows in found if rows != ours_memo(result, kind, index)]
    assert differ == [], "\n".join(differ)


def test_mark_rows_match_linecapacity_line_window():
    stored = json.loads((ROOT / "tests" / "data" / "calc" / "марки-linecapacity.json").read_text(encoding="utf-8"))
    scheme = cir.load_bytes((ROOT / stored["scheme"]).read_bytes())
    with LineCapacity(EXE) as program:
        assert program.open(ROOT / stored["scheme"]) == []
        found = {str(index): program.mark_rows(line) for index, line in enumerate(scheme.lines)}
    (OUT / "марки-linecapacity.txt").write_text(
        "\n\n".join(f"{scheme.lines[int(i)].type_name}\n" + "\n".join(rows) for i, rows in found.items()),
        encoding="utf-8")
    assert found == {index: item["rows"] for index, item in stored["lines"].items()}, "записанные строки устарели"
    differ = [f"{line.type_name}: {explain(found[str(i)], mark_rows(line.type_name, line.phase_mode))}"
              for i, line in enumerate(scheme.lines) if found[str(i)] != mark_rows(line.type_name, line.phase_mode)]
    assert differ == [], "\n".join(differ)


@pytest.mark.parametrize("name", SINGLE)
def test_single_consumer_scheme_matches_linecapacity_windows(name):
    scheme = build(SEQUENCES[name]())[-1][1]
    source = OUT / f"{name}-из-voltplan.cir"
    source.write_bytes(cir.dump_bytes(scheme))
    result = run(scheme)
    targets = [("transformer", None)] + [("lines", i) for i in range(len(scheme.lines))] + [("consumers", 0)]
    checked = []
    with LineCapacity(EXE) as program:
        assert program.open(source) == []
        assert program.calculate(report=False) == []
        for kind, index in targets:
            checked.append((f"{kind} {index}", memo_of(program, scheme, kind, index), ours_memo(result, kind, index)))
        assert program.show_report() == ("недоступно", None)
    save_windows(name, [(title, rows) for title, rows, _ in checked])
    assert not result["show_report"]
    differ = [f"{title}: {explain(a, b)}" for title, a, b in checked if a != b]
    assert differ == [], "\n".join(differ)


@pytest.mark.parametrize("case", OWN_CASES, ids=[case["name"] for case in OWN_CASES])
def test_recorded_scheme_matches_linecapacity(case):
    path = ROOT / case["scheme"]
    scheme = cir.load_bytes(path.read_bytes())
    result = run(scheme, case["period"], case["min_load"])
    with LineCapacity(EXE) as program:
        assert program.open(path) == []
        rows = program.calculate(case["period"], case["min_load"], report=case["report"] is not None)
        program.close_report()
        found = [(kind, index, memo_of(program, scheme, kind, index)) for kind, index, _ in windows(case)]
        program.screenshot(OUT / f"данные-{case['name']}.png")
    if case["report"] is not None:
        verify(case, rows, [row["text"] for row in result["report"]], f"данные-{case['name']}")
    stale = [f"{kind} {index}" for (kind, index, rows), (_, _, stored) in zip(found, windows(case), strict=True)
             if rows != stored]
    assert stale == [], "записанные окна устарели: " + ", ".join(stale)
    differ = [f"{kind} {index}" for kind, index, rows in found if rows != ours_memo(result, kind, index)]
    assert differ == [], ", ".join(differ)


def test_report_menu_follows_linecapacity_in_one_session():
    data = ROOT / "tests" / "data" / "calc"
    steps = [("один-однофазный-сухой", False), ("разные-типы", True), ("один-однофазный-сухой", False),
             ("один-трёхфазный", False)]
    seen = []
    with LineCapacity(EXE) as program:
        for name, automatic in steps:
            assert program.open(data / f"{name}.cir") == []
            program.calculate(report=automatic)
            program.close_report()
            seen.append((name, *program.show_report()))
    expected_menu = []
    enabled = False
    for name, automatic in steps:
        result = run(cir.load_bytes((data / f"{name}.cir").read_bytes()))
        assert result["show_report"] is automatic
        enabled = enabled or result["show_report"]
        if not enabled:
            expected_menu.append((name, "недоступно", None))
        elif result["report_ready"]:
            expected_menu.append((name, "итоги", [row["text"] for row in result["report"]]))
        else:
            expected_menu.append((name, "сообщение", "Недостаточно потребителей в схеме!"))
    assert seen == expected_menu


@pytest.mark.parametrize("name", REFUSED)
def test_refusal_message_matches_linecapacity(name):
    source = OUT / f"{name}-из-voltplan.cir"
    source.write_bytes(cir.dump_bytes(build(SEQUENCES[name]())[-1][1]))
    with LineCapacity(EXE) as program:
        assert program.open(source) == []
        with pytest.raises(CalcRefused) as refused:
            program.calculate()
    refused.value.image.save(OUT / f"отказ-{name}.png")
    assert refused.value.text == refusal(name)


def visible(program, points) -> bool:
    rect = program.main.client_area_rect()
    width, height = rect.right - rect.left, rect.bottom - rect.top
    return all(40 < x < width - 60 and 40 < y < height - 80 for x, y in points)


def carries_current(rows: list[str]) -> bool:
    return any(row.startswith("Ток") and not row.endswith(" 0,000 А") for row in rows)


def pick(indexes: list[int], wanted, count: int) -> list[int]:
    first = [i for i in indexes if wanted(i)][:1]
    return first + [i for i in indexes if i not in first][:count - len(first)]


@pytest.mark.parametrize("stem", OBJECT_SAMPLES)
def test_object_results_match_linecapacity(stem):
    path = next(p for p in SCHEMES if p.stem.startswith(stem))
    scheme = cir.load_bytes(path.read_bytes())
    memo = run(scheme)["memo"]
    stored = next(case for case in CASES if case["name"] == path.stem)["memo"]
    checked = []
    with LineCapacity(EXE) as program:
        assert program.open(path) == []
        program.calculate()
        program.close_report()
        checked.append(("ТП", "transformer", None, program.memo("transformer", scheme.transformer)))
        lines = [i for i, line in enumerate(scheme.lines)
                 if visible(program, [(line.x, line.y), (line.end_x, line.end_y)])
                 and carries_current(memo["lines"][i])]
        lines = pick(lines, lambda i: scheme.lines[i].phase_mode == 1, OBJECTS_PER_KIND)
        for index in lines:
            checked.append((f"ЛЭП {index}", "lines", index, program.memo("line", scheme.lines[index])))
        shown = [i for i, c in enumerate(scheme.consumers) if visible(program, [(c.x, c.y + 10)])]
        shown = pick(shown, lambda i: scheme.consumers[i].phase_mode == 0, OBJECTS_PER_KIND)
        for index in shown:
            checked.append((f"потребитель {index}", "consumers", index, program.memo("consumer",
                                                                                      scheme.consumers[index])))
    save_windows(stem, [(title, rows) for title, _, _, rows in checked])
    assert len(lines) == OBJECTS_PER_KIND and len(shown) == OBJECTS_PER_KIND
    stale = [title for title, kind, index, rows in checked
             if (stored.get(kind) if index is None else stored.get(kind, {}).get(str(index)))
             not in (None, rows)]
    assert stale == [], "записанные окна устарели: " + ", ".join(stale)
    differ = [f"{title}: {explain(rows, ours_memo({'memo': memo}, kind, index))}"
              for title, kind, index, rows in checked if rows != ours_memo({"memo": memo}, kind, index)]
    assert differ == [], "\n".join(differ)


def test_voltage_warning_matches_linecapacity():
    path = next(p for p in SCHEMES if p.stem.startswith("Гатское"))
    scheme = act(cir.load_bytes(path.read_bytes()), kind="update", target="transformer", index=0,
                 fields={"pbv_step": -2, "pbv_percent": 5.0})
    case = case_for("повышенное-напряжение")
    assert cir.dump_bytes(scheme) == (ROOT / case["scheme"]).read_bytes(), "записанная схема устарела"
    source = OUT / "повышенное-напряжение-из-voltplan.cir"
    source.write_bytes(cir.dump_bytes(scheme))
    expected = theirs(source, "повышенное-напряжение")
    assert "Внимание! Недопустимо высокое напряжение у потребителя!" in expected
    verify(case, expected, ours(scheme), "повышенное-напряжение")
