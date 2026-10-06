from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .session import Admin, site

router = APIRouter(prefix="/api/admin", tags=["Администрирование"])
Values = dict[str, float | bool | list[float]]


class ReferenceBody(BaseModel):
    values: Values


@router.get("/reference")
def reference(user: Admin, request: Request) -> dict:
    return {"values": site(request).reference.values(), "stored": site(request).reference.stored()}


@router.put("/reference")
def update_reference(user: Admin, data: ReferenceBody, request: Request) -> dict:
    return {"values": site(request).reference.update(user, data.values)}


@router.delete("/reference")
def reset_reference(user: Admin, request: Request) -> dict:
    return {"values": site(request).reference.reset(user)}


class OptionsBody(BaseModel):
    energy_price_usd: float


@router.get("/options")
def options(user: Admin, request: Request) -> dict:
    return {"energy_price_usd": site(request).options.energy_price()}


@router.put("/options")
def save_options(user: Admin, data: OptionsBody, request: Request) -> dict:
    return {"energy_price_usd": site(request).options.set_energy_price(user, data.energy_price_usd)}


class TierBody(BaseModel):
    tier: str = Field(max_length=10)
    until: float | None = None


class AdminFlag(BaseModel):
    is_admin: bool


class Broadcast(BaseModel):
    text: str = Field(max_length=500)
    user_id: int | None = None


@router.get("/users")
def people(user: Admin, request: Request, query: str = "") -> list[dict]:
    return site(request).desk.people(user, query)


@router.put("/users/{user_id}/tier")
def set_tier(user: Admin, user_id: int, data: TierBody, request: Request) -> dict:
    return site(request).desk.set_tier(user, user_id, data.tier, data.until)


@router.put("/users/{user_id}/admin")
def set_admin(user: Admin, user_id: int, data: AdminFlag, request: Request) -> dict:
    return site(request).desk.set_admin(user, user_id, data.is_admin)


@router.get("/journal")
def journal(user: Admin, request: Request, query: str = "") -> list[dict]:
    return site(request).desk.journal(user, query)


@router.post("/broadcast")
def broadcast(user: Admin, data: Broadcast, request: Request) -> dict:
    return site(request).desk.broadcast(user, data.text, data.user_id)


@router.get("/payments")
def payments(user: Admin, request: Request) -> list[dict]:
    return site(request).desk.payments(user)
