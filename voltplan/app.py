from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .api import calc, catalog, exchange, scheme
from .config import LOGS, WEB
from .errors import describe
from .scheme.editor import EditError

log = logging.getLogger("voltplan")


def setup_logging() -> None:
    if log.handlers:
        return
    LOGS.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOGS / "server.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def too_large(request: Request) -> bool:
    declared = request.headers.get("content-length", "")
    return (request.url.path == "/api/exchange/import" and declared.isdigit()
            and int(declared) > exchange.MAX_REQUEST_BYTES)


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="VoltPlan", docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/openapi.json")

    @app.middleware("http")
    async def journal(request: Request, call_next) -> Response:
        started = time.perf_counter()
        if too_large(request):
            response = JSONResponse({"detail": exchange.TOO_LARGE}, status_code=413)
        else:
            response = await call_next(request)
        if request.url.path.startswith("/api/"):
            spent = (time.perf_counter() - started) * 1000
            log.info("%s %s %s %.1f мс", request.method, request.url.path,
                     response.status_code, spent)
        return response

    @app.exception_handler(EditError)
    async def edit_refused(request: Request, exc: EditError) -> JSONResponse:
        log.info("отказ %s: %s", request.url.path, exc)
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        message = describe(exc.errors())
        log.info("неверный запрос %s: %s", request.url.path, message)
        return JSONResponse({"detail": message}, status_code=422)

    app.include_router(catalog.router)
    app.include_router(scheme.router)
    app.include_router(exchange.router)
    app.include_router(calc.router)
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app
