from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers import ROOT, SCHEMES
from voltplan.app import create_app
from voltplan.exchange import cir


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_calc_returns_results(client):
    scheme = cir.load_bytes(SCHEMES[0].read_bytes()).model_dump()
    response = client.post("/api/calc", json={"scheme": scheme, "period": 2, "min_load": True})
    assert response.status_code == 200
    data = response.json()
    assert {"seasons", "labels", "memo", "report", "good", "show_report"} <= set(data)


def test_calc_refusal_is_conflict(client):
    new = client.post("/api/scheme/apply", json={"action": {"kind": "new"}}).json()["scheme"]
    response = client.post("/api/calc", json={"scheme": new})
    assert response.status_code == 409
    assert response.json()["detail"] == "В схеме отсутствуют потребители! Расчёт не запущен!"


def test_calc_rejects_unknown_period(client):
    scheme = cir.load_bytes(SCHEMES[0].read_bytes()).model_dump()
    assert client.post("/api/calc", json={"scheme": scheme, "period": 5}).status_code == 422


def sample_scheme() -> dict:
    return cir.load_bytes(SCHEMES[0].read_bytes()).model_dump()


def test_scheme_without_lines_is_refused(client):
    scheme = sample_scheme()
    scheme["lines"] = []
    response = client.post("/api/calc", json={"scheme": scheme})
    assert response.status_code == 409
    assert response.json()["detail"] == "В схеме отсутствуют ЛЭП! Расчёт не запущен!"


def test_zero_length_line_is_refused(client):
    scheme = sample_scheme()
    scheme["lines"][3]["length_m"] = 0
    response = client.post("/api/calc", json={"scheme": scheme})
    assert response.status_code == 409
    assert response.json()["detail"] == "В схеме имеются ЛЭП нулевой длины! Расчёт не запущен!"


def test_extreme_overload_is_answered_with_numbers(client):
    scheme = cir.load_bytes((ROOT / "tests" / "data" / "calc" / "запредельная.cir").read_bytes()).model_dump()
    response = client.post("/api/calc", json={"scheme": scheme})
    assert response.status_code == 200
    data = response.json()
    assert data["memo"]["lines"][1][5] == "Температура провода: 5,425E10 град. Цельсия"
    assert len(data["charts"]["0"]["load"]) == 48 and data["report_ready"] is True


def test_results_carry_transformer_charts(client):
    response = client.post("/api/calc", json={"scheme": sample_scheme(), "period": 0})
    charts = response.json()["charts"]
    assert set(charts) == {"0"}
    assert {len(values) for values in charts["0"].values() if values} == {48}


@pytest.mark.parametrize("mark, phase, rows", [
    ("А 50", 0, ["Материал провода: алюминий", "Материал изоляции: нет", "Количество жил: 4",
                 "Сечение фазного провода: 50 мм^2"]),
    ("СИП-4 2х16", 1, ["Материал провода: алюминий", "Материал изоляции: сшитый полиэтилен", "Количество жил: 2",
                       "Сечение фазного провода: 16 мм^2"]),
    ("СИП 4х", 0, ["Материал провода: алюминий", "Материал изоляции: сшитый полиэтилен", "Количество жил: 4",
                   "Сечение фазного провода: не определено"]),
])
def test_mark_rows_repeat_linecapacity_line_window(client, mark, phase, rows):
    response = client.get("/api/catalog/mark", params={"type_name": mark, "phase_mode": phase})
    assert response.status_code == 200
    assert response.json()["rows"] == rows
