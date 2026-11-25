from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.ai.cdi import with_undetermined_option
from app.codes.hcc import HCC_MODEL_NAME, payment_year_for

__all__ = ["HccReview", "HccScanOutput", "SuspectedCondition", "hcc_review"]


class SuspectedCondition(BaseModel):
    condition: str
    icd10: str
    indicators: str = ""
    evidence: list[str] = Field(default_factory=list)
    query: str
    options: list[str] = Field(default_factory=list)

    @field_validator("options")
    @classmethod
    def _ends_with_undetermined(cls, value: list[str]) -> list[str]:
        return with_undetermined_option(value) if any(option.strip() for option in value) else []


class HccScanOutput(BaseModel):
    suspected: list[SuspectedCondition]


class HccReview(BaseModel):
    suspected: list[SuspectedCondition] = Field(default_factory=list)
    model: str = HCC_MODEL_NAME
    paymentYear: str | None = None


def hcc_review(scan: HccScanOutput, service_date: date) -> HccReview:
    kept: dict[str, SuspectedCondition] = {}
    for item in scan.suspected:
        key = item.icd10.strip().upper()
        if key and item.query.strip() and key not in kept:
            kept[key] = item
    return HccReview(suspected=list(kept.values()), paymentYear=payment_year_for(service_date))
