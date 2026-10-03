from __future__ import annotations

from fastapi import APIRouter, Query

from .. import catalog
from ..scheme.model import MAX_TEXT

router = APIRouter(prefix="/api", tags=["Справочник"])


@router.get("/catalog")
def marks() -> dict:
    return catalog.load()


@router.get("/catalog/mark")
def mark(type_name: str = Query(max_length=MAX_TEXT), phase_mode: int = Query(0, ge=0, le=1)) -> dict:
    return {"rows": catalog.mark_rows(type_name, phase_mode)}
