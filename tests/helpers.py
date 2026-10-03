from __future__ import annotations

from pathlib import Path

from voltplan.scheme.actions import Action
from voltplan.scheme.editor import Editor
from voltplan.scheme.model import Scheme

ROOT = Path(__file__).resolve().parents[1]
SCHEMES = sorted((ROOT / "schemes").glob("*.cir"))


def act(scheme: Scheme | None, **action) -> Scheme:
    return Editor(scheme or Scheme()).apply(Action(**action))


def point(x: int, y: int) -> dict:
    return {"x": x, "y": y}
