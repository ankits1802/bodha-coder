from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.adapters.billing_providers import build_billing_providers
from app.adapters.dns_txt import DnsTxtResolver
from app.adapters.image_models import build_image_model
from app.adapters.messenger import build_messenger
from app.adapters.object_store import S3ObjectStore
from app.adapters.oidc import build_identity_providers
from app.adapters.record_signers import build_record_signer
from app.adapters.saml_fetch import HttpsMetadataSource
from app.adapters.sftp import ParamikoLink
from app.api.routes import (
    account,
    auth,
    billing,
    health,
    hq,
    identity,
    inbox,
    memberships,
    notes,
    plan,
    practice,
    respond,
    signatures,
    signup,
    team,
    tours,
    uploads,
    verify,
    work,
)
from app.api.routes.blind_review import router as blind_review_router
from app.api.routes.claims import router as claims_router
from app.api.routes.clearinghouse import router as clearinghouse_router
from app.api.routes.defensibility import router as defensibility_router
from app.api.routes.domains import router as domains_router
from app.api.routes.email_intake import router as email_intake_router
from app.api.routes.expenditure import router as expenditure_router
from app.api.routes.hq_organizations import router as hq_organizations_router
from app.api.routes.intake import router as intake_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.practice_measures import router as practice_measures_router
from app.api.routes.quality import router as quality_router
from app.api.routes.query_governance import router as query_governance_router
from app.api.routes.remittances import router as remittances_router
from app.api.routes.review_records import router as review_records_router
from app.api.routes.saml import router as saml_router
from app.api.routes.sso import router as sso_router
from app.api.routes.usage import router as usage_router
from app.codes.icd import load_catalog
from app.core.config import get_settings
from app.core.error_reports import start_error_reports
from app.core.errors import CODE_BY_STATUS, SERVER_ERROR_MESSAGE, AppError, Invalid
from app.core.logging import RequestLog, configure_logging

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.refuse_unready_signup()
    start_error_reports(settings, process="api")
    app.state.signer = build_record_signer(settings)
    app.state.store = S3ObjectStore(settings)
    app.state.messenger = build_messenger(settings)
    app.state.identity_providers = build_identity_providers(settings)
    app.state.billing_providers = build_billing_providers(settings)
    app.state.icd = await asyncio.to_thread(load_catalog)
    app.state.image_model = build_image_model(settings)
    app.state.txt_resolver = DnsTxtResolver()
    app.state.metadata_source = HttpsMetadataSource()
    app.state.file_link = ParamikoLink(timeout_seconds=settings.clearinghouse_timeout_seconds)
    yield
    await app.state.image_model.aclose()


app = FastAPI(
    title="Bodha Assure", lifespan=lifespan, docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json"
)

for module in (
    health,
    auth,
    identity,
    signup,
    account,
    tours,
    memberships,
    work,
    inbox,
    notes,
    uploads,
    billing,
    practice,
    plan,
    team,
    respond,
    signatures,
    verify,
    hq,
):
    app.include_router(module.router, prefix="/api")
app.include_router(defensibility_router, prefix="/api")
app.include_router(quality_router, prefix="/api")
app.include_router(blind_review_router, prefix="/api")
app.include_router(remittances_router, prefix="/api")
app.include_router(intake_router, prefix="/api")
app.include_router(email_intake_router, prefix="/api")
app.include_router(query_governance_router, prefix="/api")
app.include_router(claims_router, prefix="/api")
app.include_router(clearinghouse_router, prefix="/api")
app.include_router(expenditure_router, prefix="/api")
app.include_router(review_records_router, prefix="/api")
app.include_router(organizations_router, prefix="/api")
app.include_router(domains_router, prefix="/api")
app.include_router(hq_organizations_router, prefix="/api")
app.include_router(practice_measures_router, prefix="/api")
app.include_router(usage_router, prefix="/api")
app.include_router(saml_router, prefix="/api")
app.include_router(sso_router, prefix="/api")


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


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException) -> JSONResponse:
    code = CODE_BY_STATUS.get(error.status_code, AppError.code)
    return JSONResponse({"error": code, "message": str(error.detail).lower()}, error.status_code, error.headers)


@app.exception_handler(Exception)
async def server_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse({"error": CODE_BY_STATUS[500], "message": SERVER_ERROR_MESSAGE}, status_code=500)


@app.middleware("http")
async def no_store(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.add_middleware(RequestLog)
