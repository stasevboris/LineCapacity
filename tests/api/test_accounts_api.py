from __future__ import annotations

import re
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from tests.helpers import PASSWORD, fresh_email, sign_up, upgrade
from voltplan.app import create_app
from voltplan.config import SESSION_COOKIE, SESSION_SECONDS

PUBLIC = {"/api/auth/register", "/api/auth/login", "/api/auth/logout", "/api/auth/state", "/api/openapi.json",
          "/api/docs", "/api/docs/oauth2-redirect", "/api/tiers", "/api/health"}


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    return create_app(tmp_path_factory.mktemp("site"))


@pytest.fixture
def anonymous(app):
    return TestClient(app)


def member(app, name: str = "") -> tuple[TestClient, dict]:
    client = TestClient(app)
    return client, sign_up(client, name=name)


def closed_routes(app) -> list[tuple[str, str]]:
    found = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/") or path in PUBLIC:
            continue
        for method in sorted(getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}):
            found.append((method, re.sub(r"\{[^}]+\}", "1", path)))
    return found


def test_every_closed_route_asks_to_sign_in(app, anonymous):
    routes = closed_routes(app)
    assert len(routes) > 30
    for method, path in routes:
        response = anonymous.request(method, path, json={})
        assert response.status_code == 401, (method, path, response.status_code)
        assert response.json() == {"detail": "Войдите в систему"}


def test_session_cookie_is_http_only_and_lasts_a_week(app):
    client = TestClient(app)
    response = client.post("/api/auth/register", json={"email": fresh_email(), "password": PASSWORD})
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and f"Max-Age={SESSION_SECONDS}" in cookie
    assert "Path=/" in cookie
    assert client.get("/api/auth/state").json()["user"]["email"] == response.json()["email"]


def test_forged_cookie_is_ignored(app):
    client, _ = member(app)
    token = client.cookies.get(SESSION_COOKIE)
    client.cookies.set(SESSION_COOKIE, token[:-1] + ("0" if token[-1] != "0" else "1"))
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/state").json() == {"user": None}


def test_login_logout_and_wrong_password(app):
    email = fresh_email()
    TestClient(app).post("/api/auth/register", json={"email": email, "password": PASSWORD})
    client = TestClient(app)
    wrong = client.post("/api/auth/login", json={"email": email, "password": "неверный1"})
    assert wrong.status_code == 401 and wrong.json() == {"detail": "Неверная почта или пароль"}
    assert client.post("/api/auth/login", json={"email": email.upper(), "password": PASSWORD}).status_code == 200
    assert client.get("/api/auth/me").json()["email"] == email
    copied = client.cookies.get(SESSION_COOKIE)
    other = TestClient(app)
    assert other.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    stolen = TestClient(app)
    stolen.cookies.set(SESSION_COOKIE, copied)
    assert stolen.get("/api/auth/me").status_code == 401
    assert other.get("/api/auth/me").json()["email"] == email


def test_pages_ask_to_sign_in_and_keep_the_target(app, anonymous):
    for path in ("/app", "/account", "/collab", "/pay", "/admin", "/app?project=5"):
        response = anonymous.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert unquote(response.headers["location"]) == f"/login?next={path}"
    for name in ("app", "account", "collab", "pay", "admin"):
        response = anonymous.get(f"/{name}.html?project=3", follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == f"/{name}?project=3"
        assert anonymous.get(f"/{name}.html", follow_redirects=True).url.path == "/login"
        for odd in (f"/{name.upper()}.HTML", f"/{name}.html/", f"/{name.title()}.Html/", f"/{name}.html.",
                    f"/{name}.html%20", f"/{name}.html::$DATA", f"/{name}.HTML.%20/"):
            assert anonymous.get(odd, follow_redirects=True).url.path == "/login", odd
    for odd in ("/a:b", "/http://example.com/app", "/con:x.html"):
        assert anonymous.get(odd).status_code == 404, odd
    for path in ("/", "/login", "/register", "/tariffs", "/features", "/about", "/faq", "/status"):
        page = anonymous.get(path)
        assert page.status_code == 200 and 'class="nav"' in page.text and "/css/site.css" in page.text
    client, _ = member(app)
    assert "scheme-name" in client.get("/app").text
    assert "projects-list" in client.get("/account").text
    assert "chat-feed" in client.get("/collab").text


def test_health_reports_the_service_without_signing_in(anonymous):
    data = anonymous.get("/api/health").json()
    assert data["status"] == "ok" and data["storage"] is True
    assert data["marks"] > 50
    assert data["consultant"] is False
    assert set(data) == {"status", "storage", "marks", "consultant"}


def test_projects_are_private_and_roles_are_enforced(app):
    owner, owner_card = member(app, "Владелец")
    upgrade(app, owner_card["id"])
    reader, reader_card = member(app, "Читатель")
    stranger, _ = member(app, "Чужой")
    scheme = owner.post("/api/scheme/apply", json={"action": {"kind": "new"}}).json()["scheme"]
    project = owner.post("/api/projects", json={"name": "Садовая", "scheme": scheme}).json()
    number = project["id"]
    assert stranger.get(f"/api/projects/{number}").status_code == 404
    assert stranger.put(f"/api/projects/{number}/scheme", json={"scheme": scheme}).status_code == 404
    team = owner.post("/api/teams", json={"name": "Бригада"}).json()
    invitation = owner.post("/api/invitations", json={"email": reader_card["email"], "team": team["id"],
                                                      "role": "reader"}).json()
    assert reader.post(f"/api/invitations/{invitation['id']}", json={"accept": True}).status_code == 200
    assert owner.post(f"/api/projects/{number}/shares", json={"team": team["id"]}).status_code == 200
    assert reader.get(f"/api/projects/{number}/scheme").json()["scheme"] == scheme
    refused = reader.put(f"/api/projects/{number}/scheme", json={"scheme": scheme})
    assert refused.status_code == 403
    assert refused.json() == {"detail": "Сохранять изменения может только владелец или редактор"}
    assert reader.delete(f"/api/projects/{number}").status_code == 403
    assert reader.post("/api/calc", json={"scheme": scheme}).status_code in (200, 409)
    assert owner.delete(f"/api/projects/{number}").json() == {"ok": True}
    assert owner.get(f"/api/projects/{number}").status_code == 404


def test_saved_scheme_comes_back_unchanged(app):
    client, _ = member(app)
    scheme = client.post("/api/scheme/apply", json={"action": {"kind": "new"}}).json()["scheme"]
    project = client.post("/api/projects", json={"name": "Проверка"}).json()
    assert client.get(f"/api/projects/{project['id']}/scheme").json()["scheme"] is None
    client.put(f"/api/projects/{project['id']}/scheme", json={"scheme": scheme})
    assert client.get(f"/api/projects/{project['id']}/scheme").json()["scheme"] == scheme
    variant = client.post(f"/api/projects/{project['id']}/variants", json={"name": "Б"}).json()
    assert variant["scheme"] == scheme and variant["name"] == "Б"
    assert len(client.get(f"/api/projects/{project['id']}").json()["variants"]) == 2


def test_message_with_file_reaches_only_the_friend(app):
    anna, _ = member(app, "Анна")
    boris, boris_card = member(app, "Борис")
    stranger, _ = member(app)
    invitation = anna.post("/api/invitations", json={"email": boris_card["email"]}).json()
    boris.post(f"/api/invitations/{invitation['id']}", json={"accept": True})
    sent = anna.post("/api/messages", data={"body": "Схема во вложении", "to_user": str(boris_card["id"])},
                     files={"file": ("улица.cir", b"cir-data", "application/octet-stream")})
    assert sent.status_code == 200
    message = sent.json()
    download = boris.get(f"/api/messages/{message['id']}/file")
    assert download.content == b"cir-data"
    assert "filename*=UTF-8''" in download.headers["content-disposition"]
    assert stranger.get(f"/api/messages/{message['id']}/file").status_code == 404
    blocked = anna.post("/api/messages", data={"to_user": str(boris_card["id"])},
                        files={"file": ("setup.exe", b"MZ", "application/octet-stream")})
    assert blocked.status_code == 400 and blocked.json() == {"detail": "Исполняемые файлы передавать нельзя"}
    for name, content in [("virus.exe.", b"data"), ("run.exe . ", b"data"), ("page.hta", b"data"),
                          ("link.lnk", b"data"), ("panel.cpl", b"data"), ("job.wsf", b"data"), ("macro.vbe", b"data"),
                          ("app.msix", b"data"), ("схема.cir", b"MZ\x90\x00"), ("readme.txt", b"#!/bin/sh")]:
        refused = anna.post("/api/messages", data={"to_user": str(boris_card["id"])},
                            files={"file": (name, content, "application/octet-stream")})
        assert refused.status_code == 400, name
    notes = boris.get("/api/notifications").json()
    assert notes["unseen"] == 2
    assert [item["text"] for item in notes["items"]] == ["Анна пишет вам", "Анна приглашает вас в друзья"]


@pytest.mark.parametrize("body, message", [
    ({"email": "a@b.by", "password": "x" * 129}, "Пароль: слишком длинное значение (не более 128 символов)"),
    ({"email": "a" * 300, "password": PASSWORD}, "Почта: слишком длинное значение (не более 254 символов)"),
])
def test_too_long_fields_are_refused_in_russian(anonymous, body, message):
    response = anonymous.post("/api/auth/register", json=body)
    assert response.status_code == 422
    assert response.json()["detail"] == message
