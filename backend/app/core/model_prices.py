from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "MICROUSD_PER_USD",
    "Costing",
    "MeteredCall",
    "ModelPrice",
    "PriceBook",
    "usd_from_microusd",
]

MICROUSD_PER_USD = 1_000_000
CENT_PLACES = 2
logger = logging.getLogger("bodha.spend")


class ModelPrice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input: Decimal = Field(ge=0)
    output: Decimal = Field(ge=0)

    def snapshot(self) -> dict[str, float]:
        return {"input": float(self.input), "output": float(self.output)}


class MeteredCall(Protocol):
    @property
    def model(self) -> str: ...

    @property
    def input_tokens(self) -> int: ...

    @property
    def output_tokens(self) -> int: ...


@dataclass(frozen=True)
class Costing:
    microusd: int
    snapshot: dict[str, dict[str, float]]


@dataclass
class PriceBook:
    prices: Mapping[str, ModelPrice]
    unpriced: set[str] = field(default_factory=set)

    def costing(self, calls: Iterable[MeteredCall]) -> Costing | None:
        priced = [(call, self.price_of(call.model)) for call in calls]
        exact, snapshot = Decimal(0), {}
        for call, price in priced:
            if price is None:
                return None
            exact += price.input * call.input_tokens + price.output * call.output_tokens
            snapshot[call.model] = price.snapshot()
        return Costing(int(exact.to_integral_value(rounding=ROUND_HALF_UP)), snapshot)

    def price_of(self, model: str) -> ModelPrice | None:
        price = self.prices.get(model)
        if price is None and model not in self.unpriced:
            self.unpriced.add(model)
            logger.warning("model %s has no price in MODEL_PRICES; its analyses record no cost", model)
        return price


def usd_from_microusd(amount: int | Decimal, *, places: int = CENT_PLACES) -> float:
    quantum = Decimal(1).scaleb(-places)
    return float((Decimal(amount) / MICROUSD_PER_USD).quantize(quantum, rounding=ROUND_HALF_UP))
