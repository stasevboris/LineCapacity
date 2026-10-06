from __future__ import annotations

import json
import time
from urllib.parse import unquote

import pytest

from tests.helpers import SCHEMES, point, signed_client
from voltplan.exchange import cir
from voltplan.scheme.model import Line, Scheme


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    return signed_client(tmp_path_factory.mktemp("site"))


@pytest.fixture
def scheme(client):
    return client.post("/api/scheme/apply", json={"action": {"kind": "new"}}).json()["scheme"]


def russian(detail: str) -> bool:
    return "Input should" not in detail and "String should" not in detail and any("а" <= c <= "я" for c in detail)


@pytest.mark.parametrize("label", ["1\r\n2", "Т1\nКТП", "а\tб", "Опора ≤ 5", "中"])
def test_texts_outside_cir_are_rejected(client, scheme, label):
    scheme["poles"][0]["label"] = label
    response = client.post("/api/exchange/export", json={"scheme": scheme, "name": "x"})
    assert response.status_code == 422
    assert russian(response.json()["detail"])


def test_unknown_consumer_category_is_rejected(client, scheme):
    action = {"kind": "branch_consumer", "point": point(163, 70), "consumer": {"category": -7.5}}
    response = client.post("/api/scheme/apply", json={"scheme": scheme, "action": action})
    assert response.status_code == 422
    assert russian(response.json()["detail"])


def test_huge_branch_count_is_rejected_quickly(client, scheme):
    scheme["poles"][0]["branch_count"] = 20_000_000
    started = time.perf_counter()
    action = {"kind": "delete", "target": "pole", "index": 0}
    response = client.post("/api/scheme/apply", json={"scheme": scheme, "action": action})
    assert response.status_code == 422
    assert time.perf_counter() - started < 1


def test_too_many_lines_are_rejected(client, scheme):
    scheme["lines"] = [Line().model_dump()] * 1201
    response = client.post("/api/exchange/export", json={"scheme": scheme, "name": "x"})
    assert response.status_code == 422


def test_import_of_oversized_scheme_is_refused(client):
    base = Scheme()
    oversized = Scheme.model_construct(transformer=base.transformer, lines=[Line()] * 1301, poles=[], consumers=[],
                                       connection_points=[], outgoing_count=0)
    response = client.post("/api/exchange/import", files={"file": ("большая.cir", cir.dump_bytes(oversized))})
    assert response.status_code == 400
    assert "не поддерживается" in response.json()["detail"]


def test_nan_is_rejected(client, scheme):
    scheme["lines"][0]["length_m"] = "NaN"
    body = json.dumps({"scheme": scheme, "name": "x"}).replace('"NaN"', "NaN")
    response = client.post("/api/exchange/export", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_validation_messages_are_russian(client):
    response = client.post("/api/scheme/apply", json={"action": {"kind": "new", "line": {"length_m": "abc"}}})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert russian(detail) and "length_m" not in detail


def test_long_name_is_shortened(client, scheme):
    response = client.post("/api/exchange/export", json={"scheme": scheme, "name": "Я" * 300})
    assert response.status_code == 200
    name = unquote(response.headers["content-disposition"].split("''")[-1])
    assert name == "Я" * 120 + ".cir"


def test_form_gives_linecapacity_defaults(client):
    data = client.post("/api/scheme/form", json={"kind": "new"}).json()
    assert data["title"] == "Новая схема"
    assert data["transformer"]["label"] == "T1 КТП-54"
    assert data["line"]["length_m"] == 30 and data["pole"] == {"label": "1/1", "branch_count": 1}
    assert data["blank"]["r_single_phase_ohm_per_km"] == 1.8


def test_form_for_consumer_follows_feeding_line(client, scheme):
    action = {"kind": "branch_consumer", "point": point(163, 70), "line": {"phase_mode": 1, "phase_no": 3}}
    built = client.post("/api/scheme/apply", json={"scheme": scheme, "action": action}).json()["scheme"]
    built["consumers"] = []
    built["connection_points"] = [dict(p, active=True) if p["point_kind"] == 6 else p
                                  for p in built["connection_points"]]
    end = next(line for line in built["lines"] if line["line_type"] == 3)
    data = client.post("/api/scheme/form", json={"scheme": built, "kind": "consumer",
                                                 "point": point(end["end_x"], end["end_y"])}).json()
    assert data["feeding"] == {"phase_mode": 1, "phase_no": 3}
    assert data["consumer"]["type_text"] == "мощность по ТУ: 3,5 кВт"


def test_titles(client):
    titles = client.get("/api/scheme/titles").json()
    assert titles["new"] == "Новая схема" and titles["span"] == "Пролёт между опорами"


def test_menu_remembers_clicked_branch(client):
    scheme = client.post("/api/scheme/apply", json={"action": {"kind": "new", "pole": {"branch_count": 3}}}).json()
    data = client.post("/api/scheme/menu", json={"scheme": scheme["scheme"], "point": point(193, 70)}).json()
    assert data["scheme"]["poles"][0]["current_branch_no"] == 2


def test_apply_returns_undo_states(client, scheme):
    action = {"kind": "span", "point": point(193, 70)}
    data = client.post("/api/scheme/apply", json={"scheme": scheme, "action": action}).json()
    assert [(len(s["lines"]), len(s["poles"])) for s in data["snapshots"]] == [(2, 1), (2, 2)]


@pytest.mark.parametrize("path", SCHEMES[1:4], ids=[p.stem for p in SCHEMES[1:4]])
def test_label_edit_through_api_changes_one_row(client, path):
    raw = path.read_bytes()
    scheme = client.post("/api/exchange/import", files={"file": (path.name, raw)}).json()["scheme"]
    action = {"kind": "update", "target": "consumer", "index": 0, "fields": {"label": "ПРАВКА"}}
    changed = client.post("/api/scheme/apply", json={"scheme": scheme, "action": action}).json()["scheme"]
    exported = client.post("/api/exchange/export", json={"scheme": changed, "name": "x"}).content
    before, after = raw.decode("cp1251").split("\r\n"), exported.decode("cp1251").split("\r\n")
    differ = [i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b]
    assert len(differ) == 1 and after[differ[0]] == "ПРАВКА"


def test_oversized_upload_is_refused_before_reading(client):
    body = b"0" * (8 * 1024 * 1024 + 100 * 1024)
    response = client.post("/api/exchange/import", files={"file": ("схема.cir", body)})
    assert response.status_code == 413
    assert response.json()["detail"] == "Файл больше 8 МБ"
