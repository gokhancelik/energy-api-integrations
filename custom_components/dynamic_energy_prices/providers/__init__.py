"""Providers for the Dynamic Energy Prices integration."""

from __future__ import annotations

from .base import PriceProvider, PricePoint, EnergyPriceSeries, ProviderPrices
from .base import ProviderConnectionError, ProviderResponseError
from .base import PROVIDER_REGISTRY
from .base import (
    BREAKDOWN_MARKET_PRICE,
    BREAKDOWN_SUPPLIER_MARKUP,
    BREAKDOWN_ENERGY_TAX,
)
from .base import (
    calculate_average_price,
    calculate_max_price,
    calculate_min_price,
    find_current_price,
    find_next_price,
    find_cheapest_block,
    CheapestBlock,
)

from . import essent  # noqa: F401 - register the Essent provider
from . import energyzero  # noqa: F401 - register the EnergyZero provider
from . import frank_energie  # noqa: F401 - register the Frank Energie provider
from . import eneco  # noqa: F401 - register the Eneco provider

__all__ = [
    "BREAKDOWN_MARKET_PRICE",
    "BREAKDOWN_SUPPLIER_MARKUP",
    "BREAKDOWN_ENERGY_TAX",
    "PriceProvider",
    "PricePoint",
    "EnergyPriceSeries",
    "ProviderPrices",
    "ProviderConnectionError",
    "ProviderResponseError",
    "PROVIDER_REGISTRY",
    "calculate_average_price",
    "calculate_max_price",
    "calculate_min_price",
    "find_current_price",
    "find_next_price",
    "find_cheapest_block",
    "CheapestBlock",
]
