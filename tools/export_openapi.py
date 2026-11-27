from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "frontend" / "openapi.json"
PLACEHOLDER_ENV = {"SECRET_KEY": "ci-only-secret-key-not-used-anywhere-else-000", "S3_BUCKET": "ci-bucket"}


def openapi_document() -> dict[str, Any]:
    for name, value in PLACEHOLDER_ENV.items():
        os.environ.setdefault(name, value)
    from app.main import app

    return app.openapi()


def document_text(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    TARGET.write_text(document_text(openapi_document()), encoding="utf-8", newline="\n")
    sys.stdout.write(f"wrote {TARGET.relative_to(ROOT).as_posix()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
