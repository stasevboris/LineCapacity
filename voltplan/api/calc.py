from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ..calc.results import run
from ..scheme.model import Scheme

router = APIRouter(prefix="/api", tags=["Расчёт"])


class CalcRequest(BaseModel):
    scheme: Scheme
    period: Literal[0, 1, 2] = 2
    min_load: bool = True


@router.post("/calc")
def calc(request: CalcRequest) -> dict:
    return run(request.scheme, request.period, request.min_load)
