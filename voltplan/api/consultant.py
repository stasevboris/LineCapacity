from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..consultant import Consultant
from .session import Signed, site

router = APIRouter(prefix="/api/consultant", tags=["Консультант"])


class Turn(BaseModel):
    role: str = Field(max_length=10)
    text: str = Field(max_length=4000)


class Question(BaseModel):
    question: str = Field(max_length=2000)
    history: list[Turn] = Field(default_factory=list, max_length=20)


def consultant(request: Request) -> Consultant:
    return Consultant(site(request).store)


@router.get("")
def state(user: Signed, request: Request) -> dict:
    return {"available": consultant(request).available()}


@router.post("")
def ask(user: Signed, data: Question, request: Request) -> dict:
    return consultant(request).ask(user, data.question, [turn.model_dump() for turn in data.history])
