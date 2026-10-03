from __future__ import annotations

import sys

import pytest

from tests.helpers import ROOT, SCHEMES, act
from tests.linecapacity.driver import LineCapacity, find_exe, ink
from tests.sequences import SEQUENCES, build
from voltplan.exchange import cir
from voltplan.scheme.model import Scheme

pytestmark = pytest.mark.linecapacity

EXE = find_exe()
OUT = ROOT / "logs" / "linecapacity"
RESAVED = ("базовая", "сложная")
SAMPLE = ROOT / "schemes" / "Ботвиново ГКТП397.cir"


@pytest.fixture(scope="module", autouse=True)
def windows_only():
    if sys.platform != "win32":
        pytest.skip("LineCapacity работает только в Windows")
    if EXE is None:
        pytest.skip("укажите путь к LineCapacity.exe в переменной LINECAPACITY_EXE")
    pytest.importorskip("pywinauto")
    OUT.mkdir(parents=True, exist_ok=True)


def rows(raw: bytes) -> list[str]:
    return raw.decode("cp1251").split("\r\n")


def explain(ours: list[str], theirs: list[str]) -> str:
    diff = [f"строка {i + 1}: VoltPlan «{a}» — LineCapacity «{b}»"
            for i, (a, b) in enumerate(zip(ours, theirs, strict=False)) if a != b]
    if len(ours) != len(theirs):
        diff.append(f"число строк: VoltPlan {len(ours)}, LineCapacity {len(theirs)}")
    return "\n".join(diff[:25])


def build_in_linecapacity(name: str) -> tuple[bytes, list]:
    history = build(SEQUENCES[name]())
    target = OUT / f"{name}-linecapacity.cir"
    with LineCapacity(EXE) as program:
        previous = None
        for action, scheme in history:
            program.perform(action, previous)
            previous = scheme
        program.screenshot(OUT / f"{name}-linecapacity.png")
        program.save_as(target)
    assert target.exists(), "LineCapacity не сохранила файл"
    return target.read_bytes(), history


def comparable(ours: Scheme, theirs: Scheme) -> bytes:
    ours = ours.model_copy(deep=True)
    ours.transformer.h = theirs.transformer.h
    return cir.dump_bytes(ours)


@pytest.mark.parametrize("name", list(SEQUENCES))
def test_same_actions_give_same_file(name):
    theirs_raw, history = build_in_linecapacity(name)
    ours = history[-1][1]
    ours_raw = comparable(ours, cir.load_bytes(theirs_raw))
    (OUT / f"{name}-voltplan.cir").write_bytes(cir.dump_bytes(ours))
    assert rows(ours_raw) == rows(theirs_raw), explain(rows(ours_raw), rows(theirs_raw))


def test_label_edit_on_sample_matches_linecapacity():
    scheme = cir.load_bytes(SAMPLE.read_bytes())
    line, consumer = scheme.lines[16], scheme.consumers[0]
    target = OUT / "правка-образца-linecapacity.cir"
    with LineCapacity(EXE) as program:
        assert program.open(SAMPLE) == []
        program.update("line", line, {"label": "ВЛ-3а"})
        program.update("consumer", consumer, {"label": "д.22а"})
        program.save_as(target)
    ours = act(scheme, kind="update", target="line", index=16, fields={"label": "ВЛ-3а"})
    ours = act(ours, kind="update", target="consumer", index=0, fields={"label": "д.22а"})
    theirs_raw = target.read_bytes()
    ours_raw = comparable(ours, cir.load_bytes(theirs_raw))
    (OUT / "правка-образца-voltplan.cir").write_bytes(cir.dump_bytes(ours))
    assert rows(ours_raw) == rows(theirs_raw), explain(rows(ours_raw), rows(theirs_raw))
    assert cir.load_bytes(theirs_raw).lines[16].phase_mode == 1


@pytest.mark.parametrize("name", list(SEQUENCES))
def test_linecapacity_file_is_reproduced_by_voltplan(name):
    path = OUT / f"{name}-linecapacity.cir"
    if not path.exists():
        pytest.skip("нет файла, построенного в LineCapacity")
    raw = path.read_bytes()
    assert cir.dump_bytes(cir.load_bytes(raw)) == raw


@pytest.mark.parametrize("name", RESAVED)
def test_voltplan_file_opens_and_resaves_in_linecapacity(name):
    scheme = build(SEQUENCES[name]())[-1][1]
    source = OUT / f"{name}-из-voltplan.cir"
    source.write_bytes(cir.dump_bytes(scheme))
    target = OUT / f"{name}-пересохранено.cir"
    with LineCapacity(EXE) as program:
        problems = program.open(source)
        image = program.screenshot(OUT / f"{name}-из-voltplan.png")
        program.save_as(target)
    assert problems == []
    assert ink(image) > 2000, "LineCapacity не нарисовала схему"
    expected, actual = rows(source.read_bytes()), rows(target.read_bytes())
    assert actual == expected, explain(expected, actual)


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_samples_resave_the_same_in_both_programs(path):
    target = OUT / f"образец-{path.stem}.cir"
    with LineCapacity(EXE) as program:
        problems = program.open(path)
        program.screenshot(OUT / f"образец-{path.stem}.png")
        program.save_as(target)
    assert problems == []
    theirs = target.read_bytes()
    ours = cir.dump_bytes(cir.load_bytes(path.read_bytes()))
    assert rows(theirs) == rows(ours), explain(rows(ours), rows(theirs))
