from __future__ import annotations

import io
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from tests.helpers import ROOT, sign_up, upgrade
from voltplan.app import create_app
from voltplan.exchange import cir


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    return create_app(tmp_path_factory.mktemp("site"))


def person(app, tier: str = "demo", admin: bool = False) -> tuple[TestClient, dict]:
    client = TestClient(app)
    card = sign_up(client, name="Проверяющий")
    if tier != "demo":
        upgrade(app, card["id"], tier)
    if admin:
        with app.state.site.store.writing(app.state.site.store.work) as db:
            db.execute("UPDATE profiles SET is_admin = 1 WHERE user_id = ?", (card["id"],))
    return client, card


def test_admin_routes_refuse_ordinary_users(app):
    client, _ = person(app)
    for method, path in (("GET", "/api/admin/users"), ("GET", "/api/admin/journal"), ("GET", "/api/admin/payments"),
                         ("POST", "/api/admin/broadcast"), ("PUT", "/api/admin/options")):
        response = client.request(method, path, json={"text": "x", "energy_price_usd": 1})
        assert response.status_code == 403
        assert response.json() == {"detail": "Раздел доступен только администратору"}


def test_administrator_manages_tiers_rights_and_notifications(app):
    admin, admin_card = person(app, admin=True)
    other, other_card = person(app)
    listed = admin.get("/api/admin/users", params={"query": other_card["email"]}).json()
    assert [row["id"] for row in listed] == [other_card["id"]]
    until = time.time() + 10 * 86400
    changed = admin.put(f"/api/admin/users/{other_card['id']}/tier", json={"tier": "max", "until": until})
    assert changed.json()["tier"] == "max"
    assert other.get("/api/account/tier").json()["tier"]["code"] == "max"
    past = admin.put(f"/api/admin/users/{other_card['id']}/tier", json={"tier": "pro", "until": time.time() - 5})
    assert past.status_code == 400
    self_drop = admin.put(f"/api/admin/users/{admin_card['id']}/admin", json={"is_admin": False})
    assert self_drop.status_code == 409
    assert admin.put(f"/api/admin/users/{other_card['id']}/admin", json={"is_admin": True}).json()["is_admin"]
    sent = admin.post("/api/admin/broadcast", json={"text": "Плановые работы в 22:00"}).json()
    assert sent["sent"] >= 2
    texts = [item["text"] for item in other.get("/api/notifications").json()["items"]]
    assert "Плановые работы в 22:00" in texts
    journal = admin.get("/api/admin/journal", params={"query": "уведомление"}).json()
    assert journal and journal[0]["action"] == "уведомление разослано"


def test_energy_price_is_checked_and_used(app):
    admin, _ = person(app, "max", admin=True)
    assert admin.put("/api/admin/options", json={"energy_price_usd": -1}).status_code == 400
    assert admin.put("/api/admin/options", json={"energy_price_usd": 0.2}).json() == {"energy_price_usd": 0.2}
    scheme = cir.load_bytes((ROOT / "schemes" / "Каменка КТП158.cir").read_bytes()).model_dump(mode="json")
    losses = admin.post("/api/calc/losses", json={"scheme": scheme}).json()
    assert losses["price_usd"] == 0.2
    assert losses["cost_usd"] == pytest.approx(losses["total_kwh"] * 0.2)


def test_docx_report_is_a_word_document(app):
    demo, _ = person(app)
    pro, _ = person(app, "pro")
    scheme = cir.load_bytes((ROOT / "schemes" / "Каменка КТП158.cir").read_bytes()).model_dump(mode="json")
    assert demo.post("/api/calc/report.docx", json={"scheme": scheme}).status_code == 403
    response = pro.post("/api/calc/report.docx", json={"scheme": scheme, "name": "Каменка",
                                                       "settings": {"line_air_winter": -12}})
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    text = archive.read("word/document.xml").decode("utf-8")
    assert "Отчёт о расчёте режима сети 0,4 кВ" in text and "Каменка" in text
    assert "Температура воздуха для проводов, зима" in text
    assert "Годовые потери" not in text


def test_make_admin_from_command_line(tmp_path, monkeypatch):
    from voltplan import __main__ as entry
    monkeypatch.setattr(entry, "DATA_DIR", tmp_path)
    assert "не найден" in entry.make_admin("nobody@b.by")
    local = create_app(tmp_path)
    client = TestClient(local)
    card = sign_up(client)
    local.state.site.close()
    assert entry.make_admin(card["email"]).endswith("теперь администратор")
