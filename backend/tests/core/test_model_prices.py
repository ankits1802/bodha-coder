import json
import logging
from dataclasses import dataclass
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.model_prices import Costing, ModelPrice, PriceBook, usd_from_microusd

FLASH = "gemini-3.8-flash"
FLASH_PRICE = ModelPrice(input=Decimal("0.50"), output=Decimal("3.00"))
SPEND_LOGGER = "bodha.spend"


@dataclass(frozen=True)
class Call:
    model: str
    input_tokens: int
    output_tokens: int


def test_a_call_costs_its_tokens_at_the_price_per_million():
    costing = PriceBook({FLASH: FLASH_PRICE}).costing([Call(FLASH, 12_000, 2_500)])
    assert costing == Costing(13_500, {FLASH: {"input": 0.5, "output": 3.0}})


def test_top_up_calls_are_summed_before_rounding_once():
    costing = PriceBook({FLASH: FLASH_PRICE}).costing([Call(FLASH, 3, 0), Call(FLASH, 3, 0)])
    assert costing is not None and costing.microusd == 3


def test_half_a_microdollar_rounds_up():
    costing = PriceBook({FLASH: FLASH_PRICE}).costing([Call(FLASH, 3, 0)])
    assert costing is not None and costing.microusd == 2


def test_each_model_is_priced_at_its_own_rate():
    pro = ModelPrice(input=Decimal("1.25"), output=Decimal("10"))
    costing = PriceBook({FLASH: FLASH_PRICE, "gemini-3.8-pro": pro}).costing(
        [Call(FLASH, 1_000, 100), Call("gemini-3.8-pro", 2_000, 400)]
    )
    assert costing == Costing(
        800 + 6_500, {FLASH: {"input": 0.5, "output": 3.0}, "gemini-3.8-pro": {"input": 1.25, "output": 10.0}}
    )


def test_no_call_costs_nothing():
    assert PriceBook({}).costing([]) == Costing(0, {})


def test_a_model_without_a_price_leaves_the_cost_unknown_and_warns_once(caplog):
    caplog.set_level(logging.WARNING, logger=SPEND_LOGGER)
    book = PriceBook({FLASH: FLASH_PRICE})
    assert book.costing([Call(FLASH, 10, 10), Call("gemini-unlisted", 10, 10)]) is None
    assert book.costing([Call("gemini-unlisted", 5, 5)]) is None
    warnings = [record.getMessage() for record in caplog.records if record.name == SPEND_LOGGER]
    assert warnings == ["model gemini-unlisted has no price in MODEL_PRICES; its analyses record no cost"]


def test_microdollars_become_dollars_to_the_cent_or_finer():
    assert usd_from_microusd(1_234_567) == 1.23
    assert usd_from_microusd(1_235_000) == 1.24
    assert usd_from_microusd(13_500) == 0.01
    assert usd_from_microusd(Decimal(100_000) / 3, places=4) == 0.0333


def test_the_default_prices_cover_the_default_model():
    settings = Settings(_env_file=None)
    assert settings.model_prices[settings.gemini_model] == FLASH_PRICE


def test_model_prices_are_read_from_a_json_object(monkeypatch):
    prices = {"gemini-3.8-pro": {"input": "1.25", "output": 10}}
    monkeypatch.setenv("MODEL_PRICES", json.dumps(prices))
    assert Settings(_env_file=None).model_prices == {
        "gemini-3.8-pro": ModelPrice(input=Decimal("1.25"), output=Decimal("10"))
    }


@pytest.mark.parametrize(
    "prices",
    [{FLASH: {"input": -1, "output": 3}}, {FLASH: {"input": 0.5}}, {FLASH: {"input": 0.5, "output": 3, "cached": 1}}],
)
def test_a_negative_missing_or_unknown_price_is_refused(monkeypatch, prices):
    monkeypatch.setenv("MODEL_PRICES", json.dumps(prices))
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
