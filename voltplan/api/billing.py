from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .session import Signed, site

router = APIRouter(prefix="/api/billing", tags=["Оплата"])


class Checkout(BaseModel):
    tier: str = Field(max_length=10)
    provider: str = Field("demo", max_length=10)


class Card(BaseModel):
    payment: str = Field(max_length=64)
    number: str = Field(max_length=32)
    expiry: str = Field(max_length=8)
    cvv: str = Field(max_length=4)
    holder: str = Field("", max_length=64)


@router.post("/checkout")
def checkout(user: Signed, data: Checkout, request: Request) -> dict:
    back = str(request.base_url).rstrip("/") + "/pay"
    return site(request).billing.checkout(user, data.tier, data.provider, back)


@router.post("/confirm")
def confirm(user: Signed, data: Card, request: Request) -> dict:
    return site(request).billing.confirm(user, data.payment, data.number, data.expiry, data.cvv, data.holder)


@router.get("/poll/{payment_id}")
def poll(user: Signed, payment_id: str, request: Request) -> dict:
    return site(request).billing.poll(user, payment_id)


@router.get("/history")
def history(user: Signed, request: Request) -> list[dict]:
    return site(request).billing.history(user)
