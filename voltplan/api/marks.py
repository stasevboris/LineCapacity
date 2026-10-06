from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..accounts import tiers
from .session import Signed, site

router = APIRouter(prefix="/api", tags=["Свои марки и тарифы"])


class NewMark(BaseModel):
    kind: Literal["line", "transformer"]
    data: dict


@router.get("/marks")
def marks(user: Signed, request: Request) -> dict:
    return site(request).marks.listing(user)


@router.post("/marks")
def add_mark(user: Signed, data: NewMark, request: Request) -> dict:
    return site(request).marks.add(user, data.kind, data.data)


@router.delete("/marks/{mark_id}")
def delete_mark(user: Signed, mark_id: int, request: Request) -> dict:
    return site(request).marks.delete(user, mark_id)


@router.get("/tiers")
def tier_list() -> dict:
    return {"tiers": [tiers.describe(tiers.TIERS[code]) for code in tiers.ORDER], "features": tiers.FEATURE_NAMES}


@router.get("/account/tier")
def my_tier(user: Signed) -> dict:
    return {"tier": tiers.describe(tiers.effective(user)), "until": user.tier_until}
