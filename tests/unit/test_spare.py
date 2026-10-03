from __future__ import annotations

from tests.helpers import act, point
from tests.sequences import TRANSFORMER, drop_one, house, pole, tap, trunk
from voltplan.exchange import cir
from voltplan.scheme import forms
from voltplan.scheme.editor import restore
from voltplan.scheme.model import Scheme


def with_single_phase_drop() -> Scheme:
    scheme = act(None, kind="new", transformer=TRANSFORMER, line=trunk("Л-1", 40), pole=pole("1", 2))
    return act(scheme, kind="branch_consumer", point=tap(scheme, "1", 1), line=drop_one("Л-2", 25, 2),
               consumer=house("1", "ул. 1", 1500))


def test_deleted_last_element_stays_in_freed_cell():
    scheme = act(with_single_phase_drop(), kind="delete", target="consumer", index=0)
    assert [c.label for c in scheme.spare.consumers] == ["1"]
    scheme = act(scheme, kind="delete", target="line", index=1)
    assert [line.label for line in scheme.spare.lines] == ["Л-2"]


def test_new_three_phase_line_keeps_unused_fields_of_freed_cell():
    scheme = act(with_single_phase_drop(), kind="delete", target="consumer", index=0)
    scheme = act(scheme, kind="delete", target="line", index=1)
    scheme = act(scheme, kind="branch_line", point=tap(scheme, "1", 1), line=trunk("Л-3", 30), pole=pole("1/1", 1))
    line = scheme.lines[1]
    assert (line.phase_mode, line.r_single_phase_ohm_per_km, line.phase_no) == (0, 1.91, 2)
    assert scheme.spare.lines == []


def test_consumer_window_uses_first_cell_when_list_is_empty():
    scheme = act(with_single_phase_drop(), kind="delete", target="consumer", index=0)
    values = forms.dialog(scheme, "branch_consumer")["consumer"]
    assert (values["label"], values["annual_kwh"]) == ("1", 1500.0)


def test_blank_line_is_the_freed_cell():
    scheme = act(with_single_phase_drop(), kind="delete", target="consumer", index=0)
    scheme = act(scheme, kind="delete", target="line", index=1)
    assert forms.dialog(scheme, "span")["blank"]["r_single_phase_ohm_per_km"] == 1.91


def test_new_pole_keeps_current_branch_of_freed_cell():
    scheme = act(None, kind="new", pole={"branch_count": 3})
    scheme = act(scheme, kind="span", point=point(253, 70), pole={"branch_count": 2})
    scheme.poles[1].current_branch_no = 2
    scheme = act(scheme, kind="delete", target="pole", index=1)
    scheme = act(scheme, kind="pole", point=point(scheme.lines[1].end_x, scheme.lines[1].end_y))
    assert scheme.poles[1].current_branch_no == 2


def test_undo_keeps_cells_behind_restored_lists():
    base = act(None, kind="new")
    grown = act(base, kind="span", point=point(193, 70), line={"label": "Л-9"})
    restored = restore(grown, base)
    assert len(restored.lines) == 1
    assert [line.label for line in restored.spare.lines] == ["Л-9"]
    assert [p.label for p in restored.spare.poles] == ["1/1"]


def test_new_scheme_and_file_start_with_fresh_cells():
    scheme = act(with_single_phase_drop(), kind="delete", target="consumer", index=0)
    assert act(scheme, kind="new").spare.consumers == []
    raw = cir.dump_bytes(scheme)
    assert cir.load_bytes(raw).spare.consumers == []
    scheme.spare.consumers = []
    assert cir.dump_bytes(scheme) == raw
