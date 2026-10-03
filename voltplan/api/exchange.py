from __future__ import annotations

from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError, field_validator

from ..errors import describe
from ..exchange import cir
from ..scheme.model import Scheme

router = APIRouter(prefix="/api/exchange", tags=["Обмен"])

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_FILE_BYTES + 64 * 1024
TOO_LARGE = "Файл больше 8 МБ"
MAX_NAME = 120
FORBIDDEN = set('\\/:*?"<>|')


def clean_name(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch not in FORBIDDEN and ord(ch) >= 32).strip()
    return cleaned[:MAX_NAME].strip() or "схема"


class ExportRequest(BaseModel):
    scheme: Scheme
    name: str = "схема"

    @field_validator("name", mode="before")
    @classmethod
    def short_name(cls, value: object) -> str:
        return clean_name(str(value or ""))


@router.post("/import")
async def import_cir(file: Annotated[UploadFile, File()]) -> dict:
    name = file.filename or "схема.cir"
    if Path(name).suffix.lower() != ".cir":
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .cir")
    raw = await file.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=TOO_LARGE)
    try:
        scheme = cir.load_bytes(raw)
    except cir.CirFormatError as exc:
        raise HTTPException(status_code=400, detail=f"Файл .cir повреждён: {exc}") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Файл .cir не поддерживается: {describe(exc.errors())}") from exc
    return {"scheme": scheme.model_dump(), "name": clean_name(Path(name).stem)}


@router.post("/export")
def export_cir(request: ExportRequest) -> Response:
    filename = request.name if request.name.lower().endswith(".cir") else request.name + ".cir"
    return Response(
        content=cir.dump_bytes(request.scheme),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"scheme.cir\"; filename*=UTF-8''{quote(filename)}"},
    )
