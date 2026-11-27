from __future__ import annotations

from typing import Any

from app.adapters.demo_model import DemoImageModel
from app.adapters.gemini import GeminiClient
from app.ai.contracts import ModelReply
from app.ai.errors import ModelNotConfigured
from app.ai.signature_check import ImageModel
from app.core.config import Settings

__all__ = ["UnconfiguredImageModel", "build_image_model"]


class UnconfiguredImageModel:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def inspect_image(self, prompt: str, *, schema: dict[str, Any], image: bytes, mime_type: str) -> ModelReply:
        raise ModelNotConfigured(self._reason)

    async def aclose(self) -> None:
        return None


def build_image_model(settings: Settings) -> ImageModel:
    if settings.gemini_backend == "demo":
        return DemoImageModel()
    try:
        return GeminiClient(settings)
    except ModelNotConfigured as error:
        return UnconfiguredImageModel(str(error))
