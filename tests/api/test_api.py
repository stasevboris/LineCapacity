from __future__ import annotations

from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from tests.helpers import SCHEMES, point
from voltplan.app import create_app
from voltplan.exchange import cir
from voltplan.scheme.model import Scheme


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def new_scheme(client):
    response = client.post("/api/scheme/apply", json={"action": {"kind": "new"}})
    assert response.status_code == 200
    return response.json()


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "VoltPlan" in response.text
    assert client.get("/js/main.js").status_code == 200
    assert client.get("/css/app.css").status_code == 200


def test_catalog(client):
    data = client.get("/api/catalog").json()
    assert len(data["transformers"]) == 75
    assert len(data["lines"]) > 4000
    tm = next(m for m in data["transformers"] if m["type_name"] == "ТМ-250")
    assert tm["sn_kva"] == 250 and tm["pbv_steps"] == 5
    line = data["lines"][0]
    assert set(line) == {"type_name", "r_phase_ohm_per_km", "r_neutral_ohm_per_km", "phase_mode"}


def test_new_scheme_returns_current_point(client):
    data = new_scheme(client)
    assert data["current"] == point(193, 70)
    assert data["scheme"]["outgoing_count"] == 1


def test_menu(client):
    scheme = new_scheme(client)["scheme"]
    data = client.post("/api/scheme/menu", json={"scheme": scheme, "point": point(163, 70)}).json()
    assert [a["kind"] for a in data["actions"]] == ["outgoing", "branch_line", "branch_consumer"]
    assert data["point_kind"] == 2
    assert data["actions"][2]["title"] == "Ответвление к потребителю"


def test_apply_sequence(client):
    scheme = new_scheme(client)["scheme"]
    response = client.post("/api/scheme/apply", json={"scheme": scheme, "action": {
        "kind": "branch_consumer", "point": point(163, 70),
        "line": {"type_name": "СИП-4 2х16", "phase_mode": 1, "phase_no": 2, "length_m": 25,
                 "r_single_phase_ohm_per_km": 1.91},
        "consumer": {"label": "1", "address": "ул. Садовая, 1"}}})
    assert response.status_code == 200
    data = response.json()
    assert data["current"] == point(163, 110)
    assert data["scheme"]["consumers"][0]["phase_no"] == 2


def test_refusal_is_conflict(client):
    scheme = new_scheme(client)["scheme"]
    span = {"kind": "span", "point": point(193, 70)}
    scheme = client.post("/api/scheme/apply", json={"scheme": scheme, "action": span}).json()["scheme"]
    delete = {"kind": "delete", "target": "pole", "index": 0}
    response = client.post("/api/scheme/apply", json={"scheme": scheme, "action": delete})
    assert response.status_code == 409
    assert "Опора не удалена" in response.json()["detail"]


def test_wrong_point_is_conflict(client):
    scheme = new_scheme(client)["scheme"]
    action = {"kind": "span", "point": point(163, 70)}
    response = client.post("/api/scheme/apply", json={"scheme": scheme, "action": action})
    assert response.status_code == 409


@pytest.mark.parametrize("action", [
    {"kind": "unknown"},
    {"kind": "span", "point": {"x": "a", "y": 1}},
    {"kind": "new", "line": {"length_m": -1}},
    {"kind": "new", "pole": {"branch_count": 11}},
    {"kind": "new", "transformer": {"pbv_steps": 3, "pbv_step": 2}},
])
def test_invalid_input_is_rejected(client, action):
    response = client.post("/api/scheme/apply", json={"action": action})
    assert response.status_code == 422


def test_scheme_required(client):
    response = client.post("/api/scheme/apply", json={"action": {"kind": "outgoing"}})
    assert response.status_code == 409


def test_export_and_import(client):
    scheme = new_scheme(client)["scheme"]
    response = client.post("/api/exchange/export", json={"scheme": scheme, "name": "Тестовая схема"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "Тестовая схема.cir" in unquote(response.headers["content-disposition"])
    back = client.post("/api/exchange/import", files={"file": ("Тестовая схема.cir", response.content)})
    assert back.status_code == 200
    assert back.json()["name"] == "Тестовая схема"
    assert cir.dump_bytes(Scheme(**back.json()["scheme"])) == response.content


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_import_export_samples_byte_exact(client, path):
    raw = path.read_bytes()
    imported = client.post("/api/exchange/import", files={"file": (path.name, raw)})
    assert imported.status_code == 200
    exported = client.post("/api/exchange/export", json={"scheme": imported.json()["scheme"], "name": path.stem})
    assert exported.content == raw


def test_import_rejects_other_extension(client):
    response = client.post("/api/exchange/import", files={"file": ("схема.txt", b"1")})
    assert response.status_code == 400


def test_import_rejects_broken_file(client):
    response = client.post("/api/exchange/import", files={"file": ("схема.cir", b"1\r\n2\r\n")})
    assert response.status_code == 400
    assert "повреждён" in response.json()["detail"]


def test_import_rejects_large_file(client):
    response = client.post("/api/exchange/import", files={"file": ("схема.cir", b"0" * (8 * 1024 * 1024 + 10))})
    assert response.status_code == 413


def test_export_sanitizes_name(client):
    scheme = new_scheme(client)["scheme"]
    response = client.post("/api/exchange/export", json={"scheme": scheme, "name": 'a/b:c*?"'})
    assert "abc.cir" in unquote(response.headers["content-disposition"])


def test_openapi_is_available(client):
    assert client.get("/api/openapi.json").status_code == 200
