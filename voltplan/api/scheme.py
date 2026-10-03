from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ..scheme import forms
from ..scheme.actions import Action, Point
from ..scheme.editor import ACTION_TITLES, EditError, Editor, restore
from ..scheme.model import Scheme

router = APIRouter(prefix="/api/scheme", tags=["Схема"])
NEW_SCHEME_TITLE = "Новая схема"


class MenuRequest(BaseModel):
    scheme: Scheme
    point: Point


class ApplyRequest(BaseModel):
    scheme: Scheme | None = None
    action: Action


class UndoRequest(BaseModel):
    scheme: Scheme
    block: Scheme


class FormRequest(BaseModel):
    scheme: Scheme | None = None
    kind: Literal["new", "outgoing", "span", "branch_line", "branch_consumer", "pole", "consumer"]
    point: Point | None = None


@router.post("/menu")
def menu(request: MenuRequest) -> dict:
    editor = Editor(request.scheme)
    x, y = request.point.x, request.point.y
    editor.click_point(x, y)
    kinds = editor.menu(x, y)
    return {
        "point": request.point.model_dump(),
        "point_kind": editor.point_kind_at(x, y),
        "actions": [{"kind": kind, "title": ACTION_TITLES[kind]} for kind in kinds],
        "scheme": editor.s.model_dump(),
    }


@router.post("/apply")
def apply(request: ApplyRequest) -> dict:
    if request.scheme is None and request.action.kind != "new":
        raise EditError("Схема не передана")
    editor = Editor(request.scheme or Scheme())
    scheme = editor.apply(request.action)
    current = {"x": editor.current[0], "y": editor.current[1]} if editor.current else None
    return {
        "scheme": scheme.model_dump(),
        "current": current,
        "snapshots": [snapshot.model_dump() for snapshot in editor.snapshots],
    }


@router.post("/undo")
def undo(request: UndoRequest) -> dict:
    return {"scheme": restore(request.scheme, request.block).model_dump()}


@router.get("/titles")
def titles() -> dict:
    return {"new": NEW_SCHEME_TITLE, **ACTION_TITLES}


@router.post("/form")
def form(request: FormRequest) -> dict:
    x = request.point.x if request.point else None
    y = request.point.y if request.point else None
    title = NEW_SCHEME_TITLE if request.kind == "new" else ACTION_TITLES[request.kind]
    return {"title": title, **forms.dialog(request.scheme, request.kind, x, y)}
