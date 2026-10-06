from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .accounts import Site
from .accounts.security import Refused
from .api import admin, auth, billing, calc, catalog, collab, consultant, exchange, marks, projects, scheme
from .api.session import current_user, optional_user
from .catalog import load as load_catalog
from .config import DATA_DIR, LOGS, WEB
from .consultant import Consultant
from .errors import describe
from .scheme.editor import EditError

log = logging.getLogger("voltplan")
OVERFLOW = ("Расчёт невозможен: числа выходят за пределы вычислений. Проверьте настройки расчёта и данные "
            "объектов схемы.")


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


PAGES = {"/login": "login.html", "/register": "register.html", "/tariffs": "tariffs.html", "/features": "features.html",
         "/about": "about.html", "/faq": "faq.html", "/status": "status.html"}
PRIVATE = {"/app": "app.html", "/account": "account.html", "/collab": "collab.html", "/pay": "pay.html",
           "/admin": "admin.html"}


PRIVATE_FILES = {f"/{name}": path for path, name in PRIVATE.items()}


class Static(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except (OSError, ValueError):
            return JSONResponse({"detail": "Страница не найдена"}, status_code=404)


def private_file(request: Request) -> str | None:
    path = request.url.path
    target = PRIVATE_FILES.get(path.split(":")[0].rstrip("/. ").lower())
    if target is None or path in PRIVATE_FILES:
        return None
    return target + (f"?{request.url.query}" if request.url.query else "")


def create_app(data_dir: Path | None = None) -> FastAPI:
    setup_logging()
    site = Site(data_dir or DATA_DIR)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        site.close()

    app = FastAPI(title="VoltPlan", docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/openapi.json", lifespan=lifespan)
    app.state.site = site

    @app.middleware("http")
    async def journal(request: Request, call_next) -> Response:
        started = time.perf_counter()
        moved = private_file(request)
        if moved:
            response = RedirectResponse(moved, status_code=303)
        elif too_large(request):
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

    @app.exception_handler(Refused)
    async def refused(request: Request, exc: Refused) -> JSONResponse:
        log.info("отказ %s %s: %s", exc.status, request.url.path, exc)
        return JSONResponse({"detail": str(exc)}, status_code=exc.status)

    @app.exception_handler(ArithmeticError)
    async def overflow(request: Request, exc: ArithmeticError) -> JSONResponse:
        log.info("переполнение %s: %s", request.url.path, exc)
        return JSONResponse({"detail": OVERFLOW}, status_code=409)

    @app.exception_handler(ValidationError)
    async def wrong_data(request: Request, exc: ValidationError) -> JSONResponse:
        message = describe(exc.errors())
        log.info("неверные данные %s: %s", request.url.path, message)
        return JSONResponse({"detail": message}, status_code=409)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        message = describe(exc.errors())
        log.info("неверный запрос %s: %s", request.url.path, message)
        return JSONResponse({"detail": message}, status_code=422)

    @app.get("/api/health", tags=["Сервис"])
    def health() -> dict:
        try:
            with site.store.lock:
                site.store.credentials.execute("SELECT 1").fetchone()
                site.store.work.execute("SELECT 1").fetchone()
            storage = True
        except sqlite3.Error:
            storage = False
        marks = load_catalog()
        return {"status": "ok", "storage": storage, "marks": len(marks["lines"]) + len(marks["transformers"]),
                "consultant": Consultant(site.store).available()}

    signed = [Depends(current_user)]
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(collab.router)
    app.include_router(admin.router)
    app.include_router(marks.router)
    app.include_router(billing.router)
    app.include_router(consultant.router)
    app.include_router(catalog.router, dependencies=signed)
    app.include_router(scheme.router, dependencies=signed)
    app.include_router(exchange.router, dependencies=signed)
    app.include_router(calc.router, dependencies=signed)

    def page(name: str):
        async def show() -> FileResponse:
            return FileResponse(WEB / name)
        return show

    def private(name: str):
        async def show(request: Request) -> Response:
            if optional_user(request) is None:
                target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
                return RedirectResponse(f"/login?next={quote(target)}", status_code=303)
            return FileResponse(WEB / name)
        return show

    for path, name in PAGES.items():
        app.add_api_route(path, page(name), include_in_schema=False)

    def renamed(path: str):
        async def move(request: Request) -> RedirectResponse:
            return RedirectResponse(path + (f"?{request.url.query}" if request.url.query else ""), status_code=303)
        return move

    for path, name in PRIVATE.items():
        app.add_api_route(path, private(name), include_in_schema=False)
        app.add_api_route(f"/{name}", renamed(path), include_in_schema=False)
    app.mount("/", Static(directory=WEB, html=True), name="web")
    return app
