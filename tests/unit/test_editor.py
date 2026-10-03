from __future__ import annotations

import pytest

from tests.helpers import SCHEMES, act, point
from voltplan.exchange import cir
from voltplan.scheme.actions import Action
from voltplan.scheme.editor import EditError, Editor
from voltplan.scheme.model import MAX_POLES, Pole


def contacts(scheme):
    return [(p.x, p.y, p.active, p.point_kind, p.branch_no, p.feeder_no) for p in scheme.connection_points]


def three_branch_scheme():
    scheme = act(None, kind="new")
    return act(scheme, kind="span", point=point(193, 70), pole={"label": "2", "branch_count": 3})


def test_new_scheme_geometry(new_scheme):
    t = new_scheme.transformer
    assert (t.x, t.y, t.h) == (50, 40, 5467)
    line = new_scheme.lines[0]
    assert (line.x, line.y, line.end_x, line.end_y) == (53, 70, 133, 70)
    assert (line.vertical, line.line_type, line.canvas_length, line.feeder_no) == (0, 0, 80, 0)
    pole = new_scheme.poles[0]
    assert (pole.x, pole.y, pole.end_x, pole.end_y, pole.canvas_length, pole.branch_count) == (133, 70, 193, 70, 60, 1)
    assert new_scheme.outgoing_count == 1
    assert contacts(new_scheme) == [
        (133, 70, False, 1, 0, 0),
        (163, 70, True, 2, 1, 0),
        (193, 70, True, 2, 0, 0),
    ]


def test_new_scheme_transformer_equivalent(new_scheme):
    t = new_scheme.transformer
    assert t.r_ohm == pytest.approx(0.009472)
    assert t.x_ohm == pytest.approx(0.0271978163829378)
    assert t.kt == pytest.approx(25.0)


def test_transformer_step_changes_ratio():
    scheme = act(None, kind="new", transformer={"pbv_step": 2})
    assert scheme.transformer.kt == pytest.approx(25.0 * 1.05)


def test_line_resistances_from_dialog():
    scheme = act(None, kind="new", line={"length_m": 50, "r_phase_ohm_per_km": 0.641, "r_neutral_ohm_per_km": 0.868})
    line = scheme.lines[0]
    assert line.r_phase_ohm == pytest.approx(0.641 * 50 / 1000)
    assert line.r_neutral_ohm == pytest.approx(0.868 * 50 / 1000)
    assert line.r_single_phase_ohm_per_km == 1.8


def test_span_adds_line_and_pole(new_scheme):
    scheme = act(new_scheme, kind="span", point=point(193, 70), pole={"branch_count": 2})
    line = scheme.lines[-1]
    assert (line.x, line.y, line.end_x, line.end_y, line.line_type, line.canvas_length) == (193, 70, 233, 70, 1, 40)
    pole = scheme.poles[-1]
    assert (pole.x, pole.end_x, pole.canvas_length, pole.branch_count) == (233, 323, 90, 2)
    assert (193, 70, False, 2, 0, 0) in contacts(scheme)
    assert (263, 70, True, 2, 1, 0) in contacts(scheme)
    assert (293, 70, True, 2, 2, 0) in contacts(scheme)
    assert (323, 70, True, 2, 0, 0) in contacts(scheme)


@pytest.mark.parametrize("tap_x, branch, drop", [(263, 1, 100), (293, 2, 70), (323, 3, 40)])
def test_consumer_drop_depends_on_branch(tap_x, branch, drop):
    scheme = act(three_branch_scheme(), kind="branch_consumer", point=point(tap_x, 70))
    line = scheme.lines[-1]
    assert (line.x, line.end_y - line.y, line.vertical, line.line_type, line.canvas_length) == (tap_x, drop, 1, 3, drop)
    consumer = scheme.consumers[-1]
    assert (consumer.x, consumer.y) == (tap_x, 70 + drop)
    assert scheme.poles[1].current_branch_no == branch


def test_consumer_takes_phase_from_line(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70),
                 line={"phase_mode": 1, "phase_no": 3, "r_single_phase_ohm_per_km": 2.0, "length_m": 20})
    line, consumer = scheme.lines[-1], scheme.consumers[-1]
    assert (line.phase_mode, line.phase_no) == (1, 3)
    assert line.r_phase_ohm == line.r_neutral_ohm == pytest.approx(0.04)
    assert (consumer.phase_mode, consumer.phase_no) == (1, 3)
    assert consumer.type_text == "мощность по ТУ: 3,5 кВт"
    assert consumer.category == 0.0


def test_three_phase_consumer_defaults(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70))
    consumer = scheme.consumers[-1]
    assert consumer.phase_mode == 0
    assert consumer.type_text == "мощность по ТУ: 12 кВт"
    assert consumer.category == 1.0


def test_individual_zero_power_is_tiny(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70),
                 consumer={"load_type": 1, "p_kw": 0})
    assert scheme.consumers[-1].p_kw == 1e-15


@pytest.mark.parametrize("tap_x, length", [(263, 128), (293, 98), (323, 68)])
def test_branch_line_minimal_length(tap_x, length):
    scheme = act(three_branch_scheme(), kind="branch_line", point=point(tap_x, 70))
    line = scheme.lines[-1]
    assert (line.line_type, line.canvas_length, line.end_y) == (2, length, 70 + length)
    pole = scheme.poles[-1]
    assert (pole.x, pole.y) == (tap_x, 70 + length)
    assert (tap_x, 70 + length, False, 4, 0, 0) in contacts(scheme)


def test_branch_line_goes_below_elements_on_the_right():
    scheme = act(three_branch_scheme(), kind="branch_consumer", point=point(323, 70))
    scheme = act(scheme, kind="branch_line", point=point(293, 70))
    assert scheme.lines[-1].canvas_length == 40 + 80


def test_single_pole_branch_ignores_other_poles():
    scheme = act(None, kind="new")
    scheme = act(scheme, kind="span", point=point(193, 70), pole={"branch_count": 3})
    scheme = act(scheme, kind="branch_consumer", point=point(263, 70))
    common = act(scheme, kind="branch_line", point=point(163, 70))
    single = act(scheme, kind="branch_line", point=point(163, 70), to_single=True)
    assert common.lines[-1].canvas_length == 100 + 80
    assert single.lines[-1].canvas_length == 80


def test_second_outgoing_goes_below_first(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70))
    scheme = act(scheme, kind="outgoing")
    line = scheme.lines[-1]
    assert (line.x, line.y, line.end_x, line.feeder_no, line.line_type) == (53, 110 + 60, 133, 1, 0)
    assert scheme.outgoing_count == 2
    assert scheme.poles[-1].feeder_no == 1


def test_branch_reaching_next_feeder_shifts_it_down(new_scheme):
    scheme = act(new_scheme, kind="outgoing")
    assert scheme.lines[-1].y == 130
    scheme = act(scheme, kind="branch_consumer", point=point(163, 70))
    feeder_two = [line for line in scheme.lines if line.feeder_no == 1]
    assert feeder_two[0].y == 130 + (110 + 24 - 130) + 24
    assert all(p.y == feeder_two[0].y for p in scheme.poles if p.feeder_no == 1)


def test_add_branch_shifts_right_and_renumbers(new_scheme):
    scheme = act(new_scheme, kind="span", point=point(193, 70))
    scheme = act(scheme, kind="add_branch", index=0)
    first = scheme.poles[0]
    assert (first.branch_count, first.canvas_length, first.end_x, first.current_branch_no) == (2, 90, 223, 1)
    assert (scheme.poles[1].x, scheme.poles[1].end_x) == (263, 323)
    assert (scheme.lines[1].x, scheme.lines[1].end_x) == (223, 263)
    taps = sorted((p.x, p.branch_no, p.active) for p in scheme.connection_points if p.y == 70 and p.x <= 223)
    assert taps == [(133, 0, False), (163, 1, True), (193, 2, True), (223, 0, False)]


def test_menu_for_each_point(new_scheme):
    editor = Editor(new_scheme)
    assert editor.menu(163, 70) == ["outgoing", "branch_line", "branch_consumer"]
    assert editor.menu(193, 70) == ["outgoing", "span"]
    assert editor.menu(133, 70) == ["outgoing"]
    assert editor.menu(1, 1) == ["outgoing"]


def test_menu_for_free_line_ends():
    scheme = act(None, kind="new")
    editor = Editor(scheme)
    editor.s.poles.clear()
    editor.s.connection_points[0].active = True
    assert editor.menu(133, 70) == ["outgoing", "pole"]
    scheme = act(None, kind="new")
    scheme = act(scheme, kind="branch_consumer", point=point(163, 70))
    scheme = act(scheme, kind="delete", target="consumer", index=0)
    assert Editor(scheme).menu(163, 110) == ["outgoing", "consumer"]


def test_wrong_action_for_point_is_refused(new_scheme):
    with pytest.raises(EditError, match="недоступно"):
        act(new_scheme, kind="span", point=point(163, 70))
    with pytest.raises(EditError):
        act(new_scheme, kind="branch_consumer", point=point(193, 70))
    with pytest.raises(EditError, match="точка"):
        act(new_scheme, kind="span")


def test_delete_consumer_reactivates_point(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70))
    scheme = act(scheme, kind="delete", target="consumer", index=0)
    assert scheme.consumers == []
    assert (163, 110, True, 6, 0, 0) in contacts(scheme)
    scheme = act(scheme, kind="consumer", point=point(163, 110), consumer={"label": "новый"})
    assert scheme.consumers[0].label == "новый"


def test_delete_line_rules(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70))
    with pytest.raises(EditError, match="потребитель"):
        act(scheme, kind="delete", target="line", index=1)
    with pytest.raises(EditError, match="опора"):
        act(scheme, kind="delete", target="line", index=0)
    scheme = act(scheme, kind="delete", target="consumer", index=0)
    scheme = act(scheme, kind="delete", target="line", index=1)
    assert len(scheme.lines) == 1
    assert (163, 70, True, 2, 1, 0) in contacts(scheme)
    assert all((p.x, p.y) != (163, 110) for p in scheme.connection_points)


def test_delete_pole_rules(new_scheme):
    scheme = act(new_scheme, kind="span", point=point(193, 70), pole={"branch_count": 2})
    with pytest.raises(EditError, match="присоединена ЛЭП"):
        act(scheme, kind="delete", target="pole", index=0)
    scheme = act(scheme, kind="delete", target="pole", index=1)
    assert len(scheme.poles) == 1
    assert (233, 70, True, 3, 0, 0) in contacts(scheme)
    assert not any(p.x in (263, 293, 323) for p in scheme.connection_points)
    assert Editor(scheme).menu(233, 70) == ["outgoing", "pole"]
    scheme = act(scheme, kind="pole", point=point(233, 70), pole={"label": "5", "branch_count": 0})
    assert scheme.poles[-1].label == "5"


def test_delete_outgoing_line_decrements_counter():
    scheme = act(None, kind="new")
    scheme = act(scheme, kind="outgoing")
    scheme = act(scheme, kind="delete", target="pole", index=1)
    scheme = act(scheme, kind="delete", target="line", index=1)
    assert scheme.outgoing_count == 1
    assert len(scheme.lines) == 1


def test_transformer_cannot_be_deleted(new_scheme):
    with pytest.raises(EditError, match="Трансформатор"):
        act(new_scheme, kind="delete", target="transformer", index=0)


def test_update_line_phase_updates_consumer(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70),
                 line={"phase_mode": 1, "phase_no": 2})
    scheme = act(scheme, kind="update", target="line", index=1, fields={"phase_mode": 0, "length_m": 44})
    line, consumer = scheme.lines[1], scheme.consumers[0]
    assert (line.phase_mode, line.length_m) == (0, 44)
    assert line.r_phase_ohm == pytest.approx(1.8 * 44 / 1000)
    assert consumer.phase_mode == 0
    assert consumer.type_text == "мощность по ТУ: 12 кВт"


def test_update_keeps_single_phase_span(new_scheme):
    scheme = act(new_scheme, kind="span", point=point(193, 70),
                 line={"phase_mode": 1, "phase_no": 2, "r_single_phase_ohm_per_km": 0.84, "length_m": 38})
    scheme = act(scheme, kind="update", target="line", index=1, fields={"label": "Л-9"})
    line = scheme.lines[1]
    assert (line.label, line.phase_mode, line.phase_no, line.r_single_phase_ohm_per_km) == ("Л-9", 1, 2, 0.84)
    assert line.r_phase_ohm == line.r_neutral_ohm == pytest.approx(0.84 * 38 / 1000)


def test_outgoing_line_may_be_single_phase():
    scheme = act(None, kind="new", line={"phase_mode": 1, "phase_no": 3, "r_single_phase_ohm_per_km": 1.2})
    assert (scheme.lines[0].phase_mode, scheme.lines[0].phase_no) == (1, 3)


def test_update_pole_label_only(new_scheme):
    scheme = act(new_scheme, kind="update", target="pole", index=0, fields={"label": "7/1", "branch_count": 5})
    assert (scheme.poles[0].label, scheme.poles[0].branch_count) == ("7/1", 1)


def test_update_transformer_recomputes(new_scheme):
    scheme = act(new_scheme, kind="update", target="transformer",
                 fields={"type_name": "ТМ-160", "sn_kva": 160, "pk_kw": 2.65, "uk_percent": 4.5})
    t = scheme.transformer
    assert t.type_name == "ТМ-160"
    assert t.r_ohm == pytest.approx(2.65e3 * 0.4e3 ** 2 / 160e3 ** 2)


def test_update_consumer_fields(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70))
    scheme = act(scheme, kind="update", target="consumer", index=0,
                 fields={"label": "12", "address": "ул. Мира, 12", "load_type": 1, "p_kw": 4.5, "cos_phi": 0.95})
    consumer = scheme.consumers[0]
    values = (consumer.label, consumer.address, consumer.load_type, consumer.p_kw, consumer.cos_phi)
    assert values == ("12", "ул. Мира, 12", 1, 4.5, 0.95)
    assert consumer.phase_mode == 0


@pytest.mark.parametrize("fields", [{"length_m": 0}, {"length_m": -5}, {"r_phase_ohm_per_km": 0}])
def test_update_line_validation(new_scheme, fields):
    with pytest.raises(EditError, match="должн"):
        act(new_scheme, kind="update", target="line", index=0, fields=fields)


def test_update_consumer_validation(new_scheme):
    scheme = act(new_scheme, kind="branch_consumer", point=point(163, 70))
    with pytest.raises(EditError):
        act(scheme, kind="update", target="consumer", index=0, fields={"cos_phi": 1.5})


def test_invalid_index(new_scheme):
    with pytest.raises(EditError, match="Не найден"):
        act(new_scheme, kind="delete", target="pole", index=9)
    with pytest.raises(EditError, match="Не найден"):
        act(new_scheme, kind="add_branch", index=-1)


def test_pole_limit(new_scheme):
    editor = Editor(new_scheme)
    editor.s.poles.extend(Pole(x=10000 + i, y=5000) for i in range(MAX_POLES - 1))
    with pytest.raises(EditError, match="опор"):
        editor.apply(Action(kind="span", point=point(193, 70)))


def test_editor_does_not_mutate_input(new_scheme):
    before = new_scheme.model_dump()
    act(new_scheme, kind="span", point=point(193, 70))
    assert new_scheme.model_dump() == before


@pytest.mark.parametrize("path", SCHEMES[:6], ids=[p.stem for p in SCHEMES[:6]])
def test_real_scheme_can_be_extended(path):
    scheme = cir.load_bytes(path.read_bytes())
    editor = Editor(scheme)
    free = [p for p in scheme.connection_points if p.active and p.point_kind == 2]
    assert free, "в образце нет свободных точек опор"
    target = free[0]
    kinds = editor.menu(target.x, target.y)
    kind = "span" if "span" in kinds else "branch_consumer"
    changed = act(scheme, kind=kind, point=point(target.x, target.y))

    def total(s):
        return len(s.lines) + len(s.poles) + len(s.consumers)

    assert total(changed) == total(scheme) + 2
    text = cir.dumps(changed)
    assert cir.dumps(cir.loads(text)) == text
    assert text.split(chr(13) + chr(10))[:2] == [str(len(changed.lines)), str(len(changed.poles))]
