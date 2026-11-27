from __future__ import annotations

import base64
import binascii
import hashlib
import struct
from dataclasses import dataclass

from app.core.errors import Invalid

__all__ = [
    "DATA_URL_PREFIX",
    "MAX_IMAGE_BYTES",
    "MAX_IMAGE_DATA_CHARS",
    "MAX_SIDE",
    "MIN_SIDE",
    "SignatureImage",
    "data_url",
    "read_signature_image",
]

DATA_URL_PREFIX = "data:image/png;base64,"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
IHDR = b"IHDR"
IHDR_END = 24
MAX_IMAGE_BYTES = 1_500_000
MAX_IMAGE_DATA_CHARS = len(DATA_URL_PREFIX) + (MAX_IMAGE_BYTES * 4 + 2) // 3 + 4
MIN_SIDE = 24
MAX_SIDE = 2400
NOT_PNG = "send the signature as a PNG image"


@dataclass(frozen=True)
class SignatureImage:
    png: bytes
    sha256: str
    width: int
    height: int


def read_signature_image(text: str) -> SignatureImage:
    raw = _decoded(text)
    width, height = _png_size(raw)
    return SignatureImage(raw, hashlib.sha256(raw).hexdigest(), width, height)


def data_url(png: bytes) -> str:
    return DATA_URL_PREFIX + base64.b64encode(png).decode("ascii")


def _decoded(text: str) -> bytes:
    if not text.startswith(DATA_URL_PREFIX):
        raise Invalid(NOT_PNG)
    try:
        raw = base64.b64decode(text[len(DATA_URL_PREFIX) :], validate=True)
    except (binascii.Error, ValueError) as error:
        raise Invalid("the signature image could not be read") from error
    if len(raw) > MAX_IMAGE_BYTES:
        raise Invalid("the signature image is too large")
    return raw


def _png_size(raw: bytes) -> tuple[int, int]:
    if len(raw) < IHDR_END or not raw.startswith(PNG_MAGIC) or raw[12:16] != IHDR:
        raise Invalid(NOT_PNG)
    width, height = struct.unpack(">II", raw[16:IHDR_END])
    if not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
        raise Invalid(f"a signature image is {MIN_SIDE} to {MAX_SIDE} pixels on each side")
    return width, height
