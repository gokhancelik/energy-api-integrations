"""Base classes and types for energy price providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import voluptuous as vol


@dataclass
class PricePoint:
    """A single price point with a time window."""

    start: datetime
    end: datetime
    total_price: float
    currency: str = "EUR"
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class EnergyPriceSeries:
    """A time series of prices for a single energy type."""

    prices: list[PricePoint]
    unit: str


@dataclass
class ProviderPrices:
    """Aggregate prices from a provider."""

    electricity: EnergyPriceSeries
    gas: EnergyPriceSeries | None = None


class ProviderConnectionError(Exception):
    """Raised when a connection to the provider fails."""


class ProviderResponseError(Exception):
    """Raised when the provider returns an unexpected response."""


PROVIDER_REGISTRY: dict[str, type[PriceProvider]] = {}


class PriceProvider(ABC):
    """Abstract base class for energy price providers."""

    provider_id: str = ""
    display_name: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.provider_id and cls.display_name:
            PROVIDER_REGISTRY[cls.provider_id] = cls

    @abstractmethod
    async def async_fetch_prices(self) -> ProviderPrices:
        """Fetch current energy prices from the provider."""

    @classmethod
    def config_schema(cls) -> vol.Schema | None:
        """Return the config schema for this provider, or None if no extra config needed."""
        return None


def calculate_average_price(prices: list[PricePoint]) -> float | None:
    """Calculate the average price across a list of price points."""
    if not prices:
        return None
    return sum(p.total_price for p in prices) / len(prices)


def calculate_min_price(prices: list[PricePoint]) -> float | None:
    """Find the lowest price in a list of price points."""
    if not prices:
        return None
    return min(p.total_price for p in prices)


def calculate_max_price(prices: list[PricePoint]) -> float | None:
    """Find the highest price in a list of price points."""
    if not prices:
        return None
    return max(p.total_price for p in prices)


def find_current_price(prices: list[PricePoint]) -> PricePoint | None:
    """Find the price point covering the current time."""
    now = datetime.now().astimezone()
    for p in prices:
        if p.start <= now < p.end:
            return p
    return None


def find_next_price(prices: list[PricePoint]) -> PricePoint | None:
    """Find the first upcoming price point."""
    now = datetime.now().astimezone()
    upcoming = [p for p in prices if p.start > now]
    if not upcoming:
        return None
    return min(upcoming, key=lambda p: p.start)
