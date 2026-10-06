from __future__ import annotations

import itertools
from pathlib import Path

from fastapi.testclient import TestClient

from voltplan.app import create_app
from voltplan.scheme.actions import Action
from voltplan.scheme.editor import Editor
from voltplan.scheme.model import Scheme

ROOT = Path(__file__).resolve().parents[1]
SCHEMES = sorted((ROOT / "schemes").glob("*.cir"))


def act(scheme: Scheme | None, **action) -> Scheme:
    return Editor(scheme or Scheme()).apply(Action(**action))


def point(x: int, y: int) -> dict:
    return {"x": x, "y": y}


PASSWORD = "proverka2026"
NUMBERS = itertools.count(1)


def fresh_email(prefix: str = "user") -> str:
    return f"{prefix}{next(NUMBERS)}@example.by"


def sign_up(client: TestClient, email: str | None = None, name: str = "") -> dict:
    response = client.post("/api/auth/register",
                           json={"email": email or fresh_email(), "password": PASSWORD, "name": name})
    assert response.status_code == 200, response.text
    return response.json()


def upgrade(app, user_id: int, tier: str = "max") -> None:
    app.state.site.users.set_tier(user_id, tier, None)


def signed_client(data_dir: Path, email: str | None = None, name: str = "", tier: str = "max") -> TestClient:
    client = TestClient(create_app(data_dir))
    card = sign_up(client, email, name)
    upgrade(client.app, card["id"], tier)
    return client
