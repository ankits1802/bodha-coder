from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import ResponseValidationError
from httpx import ASGITransport, AsyncClient

from app.api.responses.base import ExactRoute, Omittable, View
from app.main import app

FILE_ROUTES = {
    ("post", "/api/billing/export"): "text/csv",
    ("get", "/api/notes/{note_id}/defense-packet"): "application/pdf",
    ("get", "/api/notes/{note_id}/addendum.txt"): "text/plain",
}


class Reading(View):
    code: str
    note: str | None
    units: Omittable[int] = None


def _reading_app(built: dict[str, Any]) -> FastAPI:
    router = APIRouter(route_class=ExactRoute)

    @router.get("/reading", response_model=Reading)
    async def reading() -> dict[str, Any]:
        return built

    local = FastAPI()
    local.include_router(router)
    return local


async def _get_reading(built: dict[str, Any]) -> dict[str, Any]:
    transport = ASGITransport(app=_reading_app(built))
    async with AsyncClient(transport=transport, base_url="https://app.test") as client:
        return (await client.get("/reading")).json()


def _names_a_model(schema: dict[str, Any]) -> bool:
    if "$ref" in schema:
        return True
    if schema.get("type") == "array":
        return _names_a_model(schema["items"])
    return bool(schema.get("anyOf")) and all(_names_a_model(option) for option in schema["anyOf"])


def _success_contents() -> list[tuple[str, str, str, dict[str, Any]]]:
    return [
        (method, path, kind, body)
        for path, operations in app.openapi()["paths"].items()
        for method, operation in operations.items()
        for status, response in operation["responses"].items()
        if status.startswith("2")
        for kind, body in response.get("content", {}).items()
    ]


def test_every_json_response_names_a_response_model():
    untyped = [
        f"{method.upper()} {path}"
        for method, path, kind, body in _success_contents()
        if kind == "application/json" and not _names_a_model(body["schema"])
    ]
    assert untyped == []


def test_file_downloads_declare_their_media_type():
    declared = {(method, path): kind for method, path, kind, _ in _success_contents() if (method, path) in FILE_ROUTES}
    assert declared == FILE_ROUTES


async def test_a_response_carries_exactly_the_keys_the_service_built():
    assert await _get_reading({"code": "99213", "note": None}) == {"code": "99213", "note": None}
    assert await _get_reading({"code": "99417", "note": "x", "units": 2}) == {"code": "99417", "note": "x", "units": 2}


async def test_a_key_the_model_does_not_declare_fails_the_request():
    with pytest.raises(ResponseValidationError):
        await _get_reading({"code": "99213", "note": None, "label": "99213"})


def test_an_omittable_key_is_optional_and_never_null_in_the_schema():
    schema = Reading.model_json_schema(mode="serialization")
    assert schema["required"] == ["code", "note"]
    assert schema["properties"]["units"] == {"title": "Units", "type": "integer"}
