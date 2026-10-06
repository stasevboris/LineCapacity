from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..accounts.collab import FILE_LIMIT
from ..accounts.security import Refused
from .session import Signed, site

router = APIRouter(prefix="/api", tags=["Совместная работа"])


class NewTeam(BaseModel):
    name: str = Field(max_length=120)


class RoleChange(BaseModel):
    role: str = Field(max_length=10)


class Invitation(BaseModel):
    email: str = Field(max_length=254)
    team: int | None = None
    role: str = Field("reader", max_length=10)


class Answer(BaseModel):
    accept: bool


class Seen(BaseModel):
    ids: list[int] | None = None


@router.get("/teams")
def teams(user: Signed, request: Request) -> list[dict]:
    return site(request).collab.teams(user)


@router.post("/teams")
def create_team(user: Signed, data: NewTeam, request: Request) -> dict:
    return site(request).collab.create_team(user, data.name)


@router.delete("/teams/{team_id}")
def disband(user: Signed, team_id: int, request: Request) -> dict:
    site(request).collab.disband(user, team_id)
    return {"ok": True}


@router.patch("/teams/{team_id}/members/{member}")
def set_role(user: Signed, team_id: int, member: int, data: RoleChange, request: Request) -> dict:
    return site(request).collab.set_role(user, team_id, member, data.role)


@router.delete("/teams/{team_id}/members/{member}")
def remove_member(user: Signed, team_id: int, member: int, request: Request) -> dict:
    return site(request).collab.remove_member(user, team_id, member)


@router.get("/invitations")
def invitations(user: Signed, request: Request) -> dict:
    return site(request).collab.invitations(user)


@router.post("/invitations")
def invite(user: Signed, data: Invitation, request: Request) -> dict:
    return site(request).collab.invite(user, data.email, data.team, data.role)


@router.post("/invitations/{invitation_id}")
def answer(user: Signed, invitation_id: int, data: Answer, request: Request) -> dict:
    return site(request).collab.answer(user, invitation_id, data.accept)


@router.get("/friends")
def friends(user: Signed, request: Request) -> list[dict]:
    return site(request).collab.friends(user)


@router.delete("/friends/{other}")
def unfriend(user: Signed, other: int, request: Request) -> dict:
    site(request).collab.unfriend(user, other)
    return {"ok": True}


@router.get("/messages")
def history(user: Signed, request: Request, user_id: int | None = None, team: int | None = None) -> list[dict]:
    return site(request).collab.history(user, user_id, team)


@router.post("/messages")
async def send(user: Signed, request: Request, body: Annotated[str, Form(max_length=4000)] = "",
               to_user: Annotated[int | None, Form()] = None, team: Annotated[int | None, Form()] = None,
               file: Annotated[UploadFile | None, File()] = None) -> dict:
    content = None
    name = None
    if file is not None and file.filename:
        content = await file.read(FILE_LIMIT + 1)
        if len(content) > FILE_LIMIT:
            raise Refused("Файл больше 5 МБ", 413)
        name = file.filename
    return site(request).collab.send(user, body, to_user, team, name, content)


@router.get("/messages/{message_id}/file")
def download(user: Signed, message_id: int, request: Request) -> Response:
    name, content = site(request).collab.file(user, message_id)
    disposition = f"attachment; filename*=UTF-8''{quote(name)}"
    return Response(content, media_type="application/octet-stream", headers={"Content-Disposition": disposition})


@router.get("/notifications")
def notifications(user: Signed, request: Request) -> dict:
    return site(request).collab.notifications(user)


@router.post("/notifications/seen")
def seen(user: Signed, data: Seen, request: Request) -> dict:
    return site(request).collab.mark_seen(user, data.ids)
