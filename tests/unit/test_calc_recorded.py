from __future__ import annotations

import json
import re

import pytest

from tests.compare import compare_report, explain, recorded, windows
from tests.helpers import ROOT
from voltplan.calc.results import hottest_line_text, run
from voltplan.calc.text import general
from voltplan.catalog import mark_rows
from voltplan.exchange import cir

CASES = recorded()
REASONS = {"равные значения", "нулевая нагрузка"}
SAMPLES_WITH_OTHER_NAMES = {
    "Гатское КТП179", "Ковалёв Рог МТП №66 ВЛ 156", "Новозахарполье КТП404", "Р.Бартоломеевская КТП №282 ВЛ 162",
    "Р.Нисимковичская КТП178", "Сидоровичи МТП374",
}
WITH_TRANSFORMER = [case for case in CASES if "transformer" in case["memo"]]
MARKS = json.loads((ROOT / "tests" / "data" / "calc" / "марки-linecapacity.json").read_text(encoding="utf-8"))
LOWEST_VOLTAGE = 198.0
HIGHEST_VOLTAGE = 242.0
WIRE_LIMITS = {"поливинилхлорид": 70.0, "сшитый полиэтилен": 90.0, "нет": 70.0}


def red_voltage(text: str) -> bool:
    number = value(text)
    return number < LOWEST_VOLTAGE or number > HIGHEST_VOLTAGE


def wire_limit(mark: str, phase_mode: int) -> float:
    insulation = mark_rows(mark, phase_mode)[1].split(": ")[1]
    return WIRE_LIMITS[insulation]


def load(case: dict):
    return cir.load_bytes((ROOT / case["scheme"]).read_bytes())


def test_recorded_data_covers_every_sample_and_window_kind():
    names = {case["name"] for case in CASES}
    assert all(path.stem in names for path in sorted((ROOT / "schemes").glob("*.cir")))
    kinds = {kind for case in CASES for kind, _, _ in windows(case)}
    assert kinds == {"transformer", "lines", "consumers"}
    assert {(case["period"], case["min_load"]) for case in CASES} >= {(0, False), (1, False), (2, False),
                                                                        (0, True), (1, True), (2, True)}
    states = {row for case in CASES for row in case["report"] or [] if row.startswith("Трансформатор работает")
              or row.startswith("Внимание! Трансформатор")}
    assert states >= {"Трансформатор работает без перегрузки!",
                      "Трансформатор работает с кратковременной (допустимой) перегрузкой!",
                      "Внимание! Трансформатор работает с длительной перегрузкой!"}


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_results_match_recorded_linecapacity_output(case):
    scheme = load(case)
    result = run(scheme, case["period"], case["min_load"])
    if case["report"] is not None:
        actual = [row["text"] for row in result["report"]]
        problems, used = compare_report(case["report"], actual, case["substitutions"])
        assert problems == [], "\n".join(problems)
        assert used == case["substitutions"]
    else:
        assert len(scheme.consumers) == 1 and not result["show_report"]
    for kind, index, rows in windows(case):
        ours = result["memo"][kind] if index is None else result["memo"][kind][index]
        assert ours == rows, f"{kind} {index}: {explain(rows, ours)}"


def test_other_names_appear_only_for_equal_values():
    listed = [(case["name"], item) for case in CASES for item in case["substitutions"]]
    assert {item["reason"] for _, item in listed} <= REASONS
    samples = {name for name, item in listed if name in SAMPLES_WITH_OTHER_NAMES}
    assert samples == SAMPLES_WITH_OTHER_NAMES
    for _, item in listed:
        head = item["linecapacity"].split(":")[0].split("между")[0]
        assert item["voltplan"].startswith(head)


def numbers(rows: list[str]) -> list[dict]:
    seasons = []
    for row in rows:
        if row.endswith("период:"):
            seasons.append({})
            continue
        match = re.match(r"\s*(U\d|P\d|Q\d)= (\S+)", row) or re.match(
            r"\s*(Мощность утяжеления нагрузки|макс\. температура масла|макс\. температура обмоток): (\S+)", row)
        if match and seasons:
            seasons[-1][match.group(1)] = match.group(2)
    return seasons


def value(text: str) -> float:
    return float(text.replace(",", "."))


@pytest.mark.parametrize("case", WITH_TRANSFORMER, ids=[case["name"] for case in WITH_TRANSFORMER])
def test_scheme_labels_agree_with_linecapacity_transformer_window(case):
    result = run(load(case), case["period"], case["min_load"])
    for number, window in zip(sorted(result["labels"]), numbers(case["memo"]["transformer"]), strict=False):
        labels = result["labels"][number]
        assert [item["text"] for item in labels["bus"]] == [f"{key}={window[key]} В" for key in ("U1", "U2", "U3")]
        assert [item["bad"] for item in labels["bus"]] == [red_voltage(window[key]) for key in ("U1", "U2", "U3")]
        extra = window["Мощность утяжеления нагрузки"]
        p_total, q_total, extra_label = labels["sums"]
        assert extra_label == f"Pут={extra} кВт"
        phases_p = sum(value(window[key]) for key in ("P1", "P2", "P3"))
        phases_q = sum(value(window[key]) for key in ("Q1", "Q2", "Q3"))
        assert value(p_total[2:-4]) == pytest.approx(phases_p - value(extra), abs=0.016)
        assert value(q_total[2:-5]) == pytest.approx(phases_q, abs=0.016)
        winding = window["макс. температура обмоток"]
        oil = window.get("макс. температура масла")
        head = f"Масло: {oil} град.  " if oil else ""
        assert labels["transformer"] == f"{head}Обмотки: {winding} град."


@pytest.mark.parametrize("name, shown, ready", [
    ("разные-типы", True, True),
    ("один-трёхфазный", False, True),
    ("один-однофазный-сухой", False, False),
])
def test_report_rule_follows_linecapacity(name, shown, ready):
    case = next(case for case in CASES if case["name"] == name)
    result = run(load(case))
    assert result["show_report"] is shown
    assert result["report_ready"] is ready


WITH_REPORT = [case for case in CASES if case["report"] is not None]
WITH_WINDOWS = [case for case in CASES if case["memo"].get("lines") or case["memo"].get("consumers")]


def season_blocks(rows: list[str]) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    current = None
    for row in rows:
        if row == "Расчёт для летнего периода:":
            current = "0"
        elif row == "Расчёт для зимнего периода:":
            current = "1"
        elif row.startswith("Расчёт в режиме"):
            current = None
        if current:
            blocks.setdefault(current, []).append(row)
    return blocks


@pytest.mark.parametrize("case", WITH_REPORT, ids=[case["name"] for case in WITH_REPORT])
def test_scheme_marks_point_at_objects_named_in_report(case):
    scheme = load(case)
    result = run(scheme, case["period"], case["min_load"])
    blocks = season_blocks([row["text"] for row in result["report"]])
    for number, rows in blocks.items():
        labels = result["labels"][number]
        worst = scheme.consumers[labels["min_consumer"]]
        assert f"Минимальное напряжение у потребителя с адресом: {worst.address}" in rows
        assert hottest_line_text(scheme, labels["max_line"]) in rows


def memo_values(rows: list[str], prefix: str) -> list[list[str]]:
    seasons: list[list[str]] = []
    for row in rows:
        if row.endswith("период:"):
            seasons.append([])
        elif row.startswith("Режим минимальных"):
            seasons.append([])
        elif row.startswith(prefix) and seasons:
            seasons[-1].append(re.search(r": (\S+)", row).group(1))
    return seasons


@pytest.mark.parametrize("case", WITH_WINDOWS, ids=[case["name"] for case in WITH_WINDOWS])
def test_scheme_labels_agree_with_linecapacity_object_windows(case):
    result = run(load(case), case["period"], case["min_load"])
    numbers = [n for n in ("0", "1") if n in result["labels"]]
    scheme = load(case)
    for index, rows in case["memo"].get("lines", {}).items():
        temperatures = [values[0] for values in memo_values(rows, "Температура провода")]
        assert [result["labels"][n]["lines"][int(index)]["text"] for n in numbers] == temperatures
        line = scheme.lines[int(index)]
        limit = wire_limit(line.type_name, line.phase_mode)
        assert [result["labels"][n]["lines"][int(index)]["bad"] for n in numbers] == \
            [value(t) > limit for t in temperatures]
    for index, rows in case["memo"].get("consumers", {}).items():
        seasons = memo_values(rows, "Напряжение")
        order = numbers + (["2"] if "2" in result["labels"] else [])
        for number, values in zip(order, seasons, strict=True):
            texts = [item["text"] for item in result["labels"][number]["consumers"][int(index)]]
            numbers_row = result["seasons"][number]["consumer_voltages"][int(index)] if number != "2" else \
                result["min_load_mode"]["consumer_voltages"][int(index)]
            assert texts == [general(v, 4) for v in numbers_row]
            assert [value(text) for text in texts] == pytest.approx([value(v) for v in values], abs=0.051)
            flags = [item["bad"] for item in result["labels"][number]["consumers"][int(index)]]
            assert flags == [red_voltage(v) for v in values]


def red_flags(kind: str) -> set[bool]:
    found = set()
    for case in CASES:
        labels = run(load(case), case["period"], case["min_load"])["labels"]
        for season in labels.values():
            items = season.get(kind, [])
            for item in items:
                for label in item if isinstance(item, list) else [item]:
                    found.add(label["bad"])
    return found


@pytest.mark.parametrize("kind", ["bus", "lines", "consumers"])
def test_recorded_cases_show_both_red_and_normal_labels(kind):
    assert red_flags(kind) == {True, False}


@pytest.mark.parametrize("index", sorted(MARKS["lines"], key=int))
def test_mark_rows_match_linecapacity_line_window(index):
    item = MARKS["lines"][index]
    scheme = cir.load_bytes((ROOT / MARKS["scheme"]).read_bytes())
    line = scheme.lines[int(index)]
    assert (line.type_name, line.phase_mode) == (item["type_name"], item["phase_mode"])
    assert mark_rows(item["type_name"], item["phase_mode"]) == item["rows"]


def test_recorded_marks_cover_every_way_of_reading_a_mark():
    rows = [item["rows"] for item in MARKS["lines"].values()]
    shown = {row for group in rows for row in group}
    assert {"Материал провода: медь", "Материал провода: алюминий"} <= shown
    assert {"Материал изоляции: поливинилхлорид", "Материал изоляции: сшитый полиэтилен",
            "Материал изоляции: нет"} <= shown
    assert "Сечение фазного провода: 2,5 мм^2" in shown
    single_without_cross = [item for item in MARKS["lines"].values()
                            if item["phase_mode"] == 1 and "х" not in item["type_name"]]
    assert single_without_cross and all("Количество жил: 2" in item["rows"] for item in single_without_cross)
