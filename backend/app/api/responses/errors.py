from collections.abc import Callable, Iterator, Sequence
from typing import Any, Literal

from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant
from fastapi.params import Depends

from app.core.deps import ROLE_GUARDS, current_actor, current_provider
from app.core.errors import ERROR_CODES

from .view import View

__all__ = ["ErrorResponse", "error_responses"]

SESSION_DEPENDENCIES = (current_actor, current_provider)


class ErrorResponse(View):
    error: Literal[ERROR_CODES]
    message: str


def _described(description: str) -> dict[str, Any]:
    return {"model": ErrorResponse, "description": description}


def _dependants(dependant: Dependant) -> Iterator[Dependant]:
    yield dependant
    for child in dependant.dependencies:
        yield from _dependants(child)


def _takes_input(dependant: Dependant) -> bool:
    return bool(dependant.body_params or dependant.query_params or dependant.path_params)


def error_responses(
    path: str, endpoint: Callable[..., Any], dependencies: Sequence[Depends] | None
) -> dict[int | str, Any]:
    roots = [get_dependant(path=path, call=endpoint)]
    roots += [get_dependant(path=path, call=item.dependency) for item in dependencies or () if item.dependency]
    every = [node for root in roots for node in _dependants(root)]
    calls = {node.call for node in every}
    found: dict[int | str, Any] = {}
    if any(_takes_input(node) for node in every):
        found[422] = _described("The request is not valid")
    if any(call in calls for call in SESSION_DEPENDENCIES):
        found[401] = _described("Sign-in is missing or has ended")
    if any(call in ROLE_GUARDS for call in calls):
        found[403] = _described("This role cannot do this, or the note is in the reader's blind audit")
    found["default"] = _described("Any other error")
    return found
