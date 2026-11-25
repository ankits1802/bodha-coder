from __future__ import annotations

import json
import re
from typing import Any

__all__ = ["extract_json", "parse_json_loose", "render_json_template"]

_JSON_FENCE = re.compile(r"```json\s*\n?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_ANY_FENCE = re.compile(r"```\s*\n?\s*([\s\S]*?)\s*```")
_TEMPLATE_SLOT = "{{json .}}"


def extract_json(text: str) -> str:
    text = text.strip()
    for fence in (_JSON_FENCE, _ANY_FENCE):
        match = fence.search(text)
        if match:
            return match.group(1).strip()
    array_start, object_start = text.find("["), text.find("{")
    if array_start != -1 and (object_start == -1 or array_start < object_start):
        array_end = text.rfind("]")
        if array_end > array_start:
            return text[array_start : array_end + 1].strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        extracted = text[start : end + 1].strip()
        if '"' in extracted and ":" in extracted:
            return extracted
    return text


def parse_json_loose(text: str) -> Any:
    try:
        return json.loads(extract_json(text))
    except (ValueError, TypeError):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def render_json_template(template: str, data: Any) -> str:
    return template.replace(_TEMPLATE_SLOT, json.dumps(data, indent=2))
