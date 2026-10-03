from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.helpers import SCHEMES, act, point
from voltplan.exchange import cir
from voltplan.scheme import forms
from voltplan.scheme.actions import Action, ConsumerInput
from voltplan.scheme.editor import EditError, Editor
from voltplan.scheme.model import MAX_BRANCHES, ConnectionPoint, Consumer, Line, Pole, Scheme


def lone_pole_scheme(**extra) -> Scheme:
    pole = Pole(label="П", x=100, y=100, end_x=160, end_y=100, canvas_length=60, branch_count=1)
    points = [ConnectionPoint(x=130, y=100, active=True, point_kind=2, branch_no=1),
              ConnectionPoint(x=160, y=100, active=True, point_kind=2)]
    return Scheme(poles=[pole], connection_points=points, **extra)


def test_add_branch_stops_at_horizontal_line_below():
    scheme = lone_pole_scheme(
        lines=[Line(x=50, y=200, end_x=300, end_y=200, vertical=0, canvas_length=250)],
        consumers=[Consumer(x=150, y=150), Consumer(x=150, y=250)],
    )
    changed = act(scheme, kind="add_branch", index=0)
    assert [(c.x, c.y) for c in changed.consumers] == [(180, 150), (150, 250)]


def test_add_branch_stops_at_pole_below():
    scheme = lone_pole_scheme(consumers=[Consumer(x=150, y=170), Consumer(x=150, y=190)])
    scheme.poles.append(Pole(x=60, y=180, end_x=150, end_y=180, canvas_length=90, branch_count=2))
    changed = act(scheme, kind="add_branch", index=0)
    assert [(c.x, c.y) for c in changed.consumers] == [(180, 170), (150, 190)]


def test_add_branch_stops_at_vertical_line_on_the_right():
    scheme = lone_pole_scheme(
        lines=[Line(x=400, y=50, end_x=400, end_y=95, vertical=1, canvas_length=45)],
        consumers=[Consumer(x=350, y=120), Consumer(x=450, y=120)],
    )
    changed = act(scheme, kind="add_branch", index=0)
    assert [(c.x, c.y) for c in changed.consumers] == [(380, 120), (450, 120)]


def test_add_branch_has_limit():
    scheme = lone_pole_scheme()
    scheme.poles[0].branch_count = MAX_BRANCHES
    with pytest.raises(EditError, match="больше"):
        act(scheme, kind="add_branch", index=0)


def test_pole_with_many_branches_can_be_renamed():
    scheme = lone_pole_scheme()
    scheme.poles[0].branch_count = 12
    changed = act(scheme, kind="update", target="pole", index=0, fields={"label": "Новая"})
    assert (changed.poles[0].label, changed.poles[0].branch_count) == ("Новая", 12)


@pytest.mark.parametrize("order, expected", [("chain-first", 260), ("tap-first", 200)])
def test_search_below_single_pole_follows_linecapacity_order(order, expected):
    tap = Line(x=130, y=100, end_x=130, end_y=160, vertical=1)
    first = Line(x=500, y=160, end_x=500, end_y=200, vertical=1)
    second = Line(x=520, y=200, end_x=520, end_y=260, vertical=1)
    lines = [first, second, tap] if order == "chain-first" else [tap, first, second]
    editor = Editor(lone_pole_scheme(lines=lines))
    assert editor.lowest_end_under_pole(0) == expected


def test_shift_down_moves_consumers_of_lower_feeders(new_scheme):
    scheme = act(new_scheme, kind="outgoing")
    lower_pole = next(p for p in scheme.poles if p.feeder_no == 1)
    scheme = act(scheme, kind="branch_consumer", point=point(lower_pole.x + 30, lower_pole.y))
    before = next(c for c in scheme.consumers if c.feeder_no == 1).y
    scheme = act(scheme, kind="branch_consumer", point=point(163, 70))
    after = next(c for c in scheme.consumers if c.feeder_no == 1).y
    assert after - before == (110 + 24 - 130) + 24


def test_click_on_branch_point_records_branch_number():
    scheme = act(None, kind="new", pole={"branch_count": 3})
    editor = Editor(scheme)
    editor.click_point(193, 70)
    assert editor.s.poles[0].current_branch_no == 2
    editor.click_point(253, 70)
    assert editor.s.poles[0].current_branch_no == 0


def test_undo_snapshots_follow_linecapacity():
    editor = Editor(Scheme())
    editor.apply(Action(kind="new"))
    assert [len(s.lines) + len(s.poles) for s in editor.snapshots] == [1, 2]
    assert [s.outgoing_count for s in editor.snapshots] == [1, 1]
    outgoing = Editor(editor.s)
    outgoing.apply(Action(kind="outgoing"))
    assert [(len(s.lines), len(s.poles), s.outgoing_count) for s in outgoing.snapshots] == [(2, 1, 2), (2, 2, 2)]
    scheme = editor.s
    editor = Editor(scheme)
    editor.apply(Action(kind="branch_consumer", point=point(163, 70)))
    assert [(len(s.lines), len(s.consumers)) for s in editor.snapshots] == [(2, 0), (2, 1)]
    unrecorded = (
        ("add_branch", {"index": 0}),
        ("update", {"target": "pole", "index": 0, "fields": {"label": "x"}}),
        ("delete", {"target": "consumer", "index": 0}),
    )
    for kind, extra in unrecorded:
        editor = Editor(editor.s)
        editor.apply(Action(kind=kind, **extra))
        assert editor.snapshots == []


def test_dialog_defaults_match_linecapacity():
    values = forms.dialog(None, "new")
    assert values["transformer"]["label"] == "T1 КТП-54"
    assert values["transformer"]["type_name"] == "ТМ-250"
    assert (values["line"]["type_name"], values["line"]["label"], values["line"]["length_m"]) == ("А 16", "Л-1", 30.0)
    assert values["pole"] == {"label": "1/1", "branch_count": 1}
    scheme = act(None, kind="new")
    consumer = forms.dialog(scheme, "branch_consumer")["consumer"]
    assert (consumer["label"], consumer["address"], consumer["p_kw"], consumer["annual_kwh"]) == (
        "10", "п.Стрешин, ул. Юбилейная, д.10", 0.35, 1293.0)
    assert consumer["type_text"] == "мощность по ТУ: 12 кВт"


def test_line_prefill_uses_first_line_when_type_is_new():
    scheme = act(None, kind="new", line={"type_name": "А 35", "length_m": 40, "r_phase_ohm_per_km": 0.868,
                                         "r_neutral_ohm_per_km": 0.868})
    values = forms.dialog(scheme, "span")["line"]
    assert (values["type_name"], values["length_m"], values["r_phase_ohm_per_km"]) == ("А 35", 40.0, 0.868)


def test_consumer_prefill_repeats_previous_consumer():
    scheme = act(None, kind="new", pole={"branch_count": 2})
    scheme = act(scheme, kind="branch_consumer", point=point(163, 70),
                 consumer={"label": "7", "address": "ул. Мира, 7", "p_kw": 0.180853658536585, "annual_kwh": 1500})
    values = forms.dialog(scheme, "branch_consumer")["consumer"]
    assert (values["label"], values["address"], values["p_kw"], values["annual_kwh"]) == (
        "7", "ул. Мира, 7", 0.180853658536585, 1500.0)


@pytest.mark.parametrize("label", ["1\r\n2", "а\tб", "Опора ≤ 5", "中"])
def test_texts_must_fit_cir(label):
    with pytest.raises(ValidationError):
        Pole(label=label)
    with pytest.raises(ValidationError):
        ConsumerInput(label=label)


def test_scheme_limits():
    with pytest.raises(ValidationError):
        Scheme(lines=[Line()] * 1201)
    with pytest.raises(ValidationError):
        Pole(branch_count=MAX_BRANCHES + 1)
    with pytest.raises(ValidationError):
        Line(length_m=float("nan"))


def test_input_category_must_be_known():
    with pytest.raises(ValidationError):
        ConsumerInput(category=-7.5)


def test_unknown_category_is_normalized_on_edit(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70), line={"phase_mode": 1})
    scheme.consumers[0].category = 49.8942550184878
    changed = act(scheme, kind="update", target="consumer", index=0, fields={"label": "2"})
    assert changed.consumers[0].category == 0.0


def rows(scheme):
    return cir.dumps(scheme).split("\r\n")


def allowed_rows(scheme, kind, index):
    header = 5
    transformer = header
    lines_start = transformer + 17
    poles_start = lines_start + 18 * len(scheme.lines)
    consumers_start = poles_start + 9 * len(scheme.poles)
    if kind == "transformer":
        return {transformer + 1, transformer + 14, transformer + 15, transformer + 16}
    if kind == "line":
        base = lines_start + 18 * index
        return {base + 1, base + 15, base + 16}
    if kind == "pole":
        return {poles_start + 9 * index}
    base = consumers_start + 13 * index
    return {base + 1, base + 5, base + 11}


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_label_edit_changes_only_its_row(path):
    scheme = cir.load_bytes(path.read_bytes())
    original = rows(scheme)
    targets = [("transformer", 0), ("pole", 0), ("consumer", 0)]
    types = [line.line_type for line in scheme.lines]
    targets += [("line", types.index(kind)) for kind in range(4) if kind in types]
    targets += [("line", i) for i, line in enumerate(scheme.lines) if line.phase_mode == 1][:3]
    for kind, index in targets:
        changed = act(scheme, kind="update", target=kind, index=index, fields={"label": "ПРАВКА"})
        new = rows(changed)
        differ = {i for i, (a, b) in enumerate(zip(original, new, strict=True)) if a != b}
        allowed = allowed_rows(scheme, kind, index)
        assert differ <= allowed, (kind, index, sorted(differ - allowed))
        label_row = min(allowed)
        assert new[label_row] == "ПРАВКА"
        if kind == "line":
            assert changed.lines[index].phase_mode == scheme.lines[index].phase_mode
