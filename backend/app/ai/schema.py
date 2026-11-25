from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = ["gemini_schema"]

_SCHEMA_NAME_MAPS = frozenset({"properties", "$defs", "definitions"})


def gemini_schema(model: type[BaseModel]) -> dict[str, Any]:
    return _without_additional_properties(model.model_json_schema())


def _without_additional_properties(node: Any, *, in_name_map: bool = False) -> Any:
    if isinstance(node, dict):
        return {
            key: _without_additional_properties(value, in_name_map=not in_name_map and key in _SCHEMA_NAME_MAPS)
            for key, value in node.items()
            if in_name_map or key != "additionalProperties"
        }
    if isinstance(node, list):
        return [_without_additional_properties(value) for value in node]
    return node
