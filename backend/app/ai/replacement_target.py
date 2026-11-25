from __future__ import annotations

from pydantic import BaseModel, model_validator

__all__ = ["ReplacementTarget"]


class ReplacementTarget(BaseModel):
    replacesIcdCode: str = ""
    suggestedIcdCode: str = ""
    suggestedDiagnosis: str = ""

    @model_validator(mode="after")
    def _suggested_code_or_nothing(self) -> ReplacementTarget:
        suggested = self.suggestedIcdCode.strip()
        if not suggested or self.replacesIcdCode.strip().upper() == suggested.upper():
            self.replacesIcdCode = ""
            self.suggestedIcdCode = ""
            self.suggestedDiagnosis = ""
            return self
        if "[" in self.suggestedDiagnosis or "]" in self.suggestedDiagnosis:
            self.suggestedDiagnosis = ""
        return self
