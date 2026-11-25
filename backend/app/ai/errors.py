from __future__ import annotations

__all__ = ["ModelError", "ModelNotConfigured", "ModelRefused", "ModelRequestRejected", "ModelUnavailable"]


class ModelError(Exception):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class ModelNotConfigured(ModelError):
    pass


class ModelUnavailable(ModelError):
    pass


class ModelRequestRejected(ModelError):
    pass


class ModelRefused(ModelError):
    pass
