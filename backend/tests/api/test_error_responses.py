from typing import Any

from httpx import ASGITransport, AsyncClient

from app.core.db import get_session
from app.core.errors import CODE_BY_STATUS, CODE_STATUS_EXTRAS, SERVER_ERROR_MESSAGE, AppError
from app.main import app

ERROR_REF = {"$ref": "#/components/schemas/ErrorResponse"}
DECLARED_BODIES = {("get", "/api/health/ready", "503")}


def _operations() -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (method, path, operation)
        for path, methods in app.openapi()["paths"].items()
        for method, operation in methods.items()
    ]


def _is_error(method: str, path: str, status: str) -> bool:
    return status == "default" or (status[0] in "45" and (method, path, status) not in DECLARED_BODIES)


def _error_schemas(method: str, path: str, operation: dict[str, Any]) -> dict[str, Any]:
    return {
        status: response.get("content", {}).get("application/json", {}).get("schema")
        for status, response in operation["responses"].items()
        if _is_error(method, path, status)
    }


def _subclasses(kind: type[AppError]) -> set[type[AppError]]:
    found = set(kind.__subclasses__())
    return found | {grandchild for child in found for grandchild in _subclasses(child)}


async def _send(method: str, path: str) -> tuple[int, Any]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://app.test") as client:
        response = await client.request(method, path)
    return response.status_code, response.json()


def test_every_operation_describes_its_errors_with_the_shared_shape():
    errors = {(method, path): _error_schemas(method, path, operation) for method, path, operation in _operations()}
    wrong = [
        f"{method.upper()} {path}"
        for (method, path), schemas in errors.items()
        if "default" not in schemas or any(schema != ERROR_REF for schema in schemas.values())
    ]
    assert wrong == []
    assert "HTTPValidationError" not in app.openapi()["components"]["schemas"]


def test_described_errors_follow_the_route_s_dependencies():
    paths = app.openapi()["paths"]
    assert sorted(paths["/api/practice/setup"]["get"]["responses"]) == ["200", "401", "403", "default"]
    assert sorted(paths["/api/auth/login"]["post"]["responses"]) == ["200", "422", "default"]
    assert sorted(paths["/api/health"]["get"]["responses"]) == ["200", "default"]


def test_every_error_class_uses_the_code_for_its_status():
    classes = _subclasses(AppError) | {AppError}
    allowed = set(CODE_BY_STATUS.items()) | {(status, code) for code, status in CODE_STATUS_EXTRAS.items()}
    assert {(kind.status_code, kind.code) for kind in classes} <= allowed


async def test_an_unknown_route_or_method_answers_in_the_shared_shape():
    assert await _send("GET", "/api/nowhere") == (404, {"error": "not_found", "message": "not found"})
    assert await _send("DELETE", "/api/health") == (
        405,
        {"error": "method_not_allowed", "message": "method not allowed"},
    )


async def test_an_unexpected_failure_answers_in_the_shared_shape_without_details():
    async def broken() -> None:
        raise RuntimeError("database password rejected")

    app.dependency_overrides[get_session] = broken
    try:
        outcome = await _send("GET", "/api/health/ready")
    finally:
        app.dependency_overrides.pop(get_session)
    assert outcome == (500, {"error": "server_error", "message": SERVER_ERROR_MESSAGE})
