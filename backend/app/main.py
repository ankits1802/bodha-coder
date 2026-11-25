from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.google_oidc import build_google_sign_in
from app.adapters.messenger import build_messenger
from app.adapters.object_store import S3ObjectStore
from app.api.routes import account, auth, billing, google, hq, notes, practice, respond, team, uploads, work
from app.codes.icd import load_catalog
from app.core.config import get_settings
from app.core.errors import AppError, Invalid


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.store = S3ObjectStore(settings)
    app.state.messenger = build_messenger(settings)
    app.state.google = build_google_sign_in(settings)
    app.state.icd = await asyncio.to_thread(load_catalog)
    yield


app = FastAPI(
    title="Bodha Coder", lifespan=lifespan, docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json"
)

for module in (auth, google, account, work, notes, uploads, billing, practice, team, respond, hq):
    app.include_router(module.router, prefix="/api")


@app.exception_handler(AppError)
async def app_error(request: Request, error: AppError) -> JSONResponse:
    return JSONResponse({"error": error.code, "message": error.message}, status_code=error.status_code)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
    problems = error.errors()
    first = problems[0] if problems else {}
    field = ".".join(str(part) for part in first.get("loc", ())[1:])
    reason = first.get("msg", "the request is not valid")
    message = f"{field}: {reason}" if field else reason
    return JSONResponse({"error": Invalid.code, "message": message}, status_code=Invalid.status_code)


@app.middleware("http")
async def no_store(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
