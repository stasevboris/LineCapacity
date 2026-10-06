from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from ..config import SESSION_COOKIE
from .session import Signed, close_session, open_session, optional_user, site

router = APIRouter(prefix="/api", tags=["Вход и профиль"])


class Registration(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
    name: str = Field("", max_length=80)


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class PasswordChange(BaseModel):
    current: str = Field(max_length=128)
    new: str = Field(max_length=128)


class Profile(BaseModel):
    name: str | None = Field(None, max_length=80)
    language: str | None = Field(None, max_length=2)


@router.post("/auth/register")
def register(data: Registration, request: Request, response: Response) -> dict:
    user = site(request).users.register(data.email, data.password, data.name)
    open_session(response, request, user)
    return user.public()


@router.post("/auth/login")
def login(data: Login, request: Request, response: Response) -> dict:
    user = site(request).users.authenticate(data.email, data.password)
    open_session(response, request, user)
    site(request).store.audit(user.id, "вход")
    return user.public()


@router.post("/auth/logout")
def logout(request: Request, response: Response) -> dict:
    site(request).revoke(request.cookies.get(SESSION_COOKIE))
    close_session(response)
    return {"ok": True}


@router.get("/auth/state")
def state(request: Request) -> dict:
    user = optional_user(request)
    return {"user": user.public() if user else None}


@router.get("/auth/me")
def me(user: Signed) -> dict:
    return user.public()


@router.post("/account/password")
def change_password(user: Signed, data: PasswordChange, request: Request, response: Response) -> dict:
    updated = site(request).users.change_password(user, data.current, data.new)
    open_session(response, request, updated)
    return updated.public()


@router.post("/account/profile")
def profile(user: Signed, data: Profile, request: Request) -> dict:
    return site(request).users.update_profile(user, data.name, data.language).public()
