from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class Invalid(AppError):
    status_code = 422
    code = "invalid"


class Unavailable(AppError):
    status_code = 503
    code = "unavailable"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, minutes: int) -> None:
        unit = "minute" if minutes == 1 else "minutes"
        super().__init__(f"Too many attempts. Try again in {minutes} {unit}.")
        self.minutes = minutes
