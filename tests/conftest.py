"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import sys
from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest


def _mock_homeassistant() -> None:
    """Mock the homeassistant module to allow imports without full HA installation."""
    if "homeassistant" not in sys.modules:
        ha_mock = MagicMock()
        ha_mock.config_entries = MagicMock()
        ha_mock.const = MagicMock()
        ha_mock.core = MagicMock()
        ha_mock.helpers = MagicMock()
        ha_mock.helpers.update_coordinator = MagicMock()
        ha_mock.helpers.entity_platform = MagicMock()
        ha_mock.data_entry_flow = MagicMock()
        sys.modules["homeassistant"] = ha_mock
        sys.modules["homeassistant.config_entries"] = ha_mock.config_entries
        sys.modules["homeassistant.const"] = ha_mock.const
        sys.modules["homeassistant.core"] = ha_mock.core
        sys.modules["homeassistant.helpers"] = ha_mock.helpers
        sys.modules["homeassistant.helpers.update_coordinator"] = (
            ha_mock.helpers.update_coordinator
        )
        sys.modules["homeassistant.helpers.entity_platform"] = (
            ha_mock.helpers.entity_platform
        )
        sys.modules["homeassistant.data_entry_flow"] = ha_mock.data_entry_flow
        sys.modules["homeassistant.components"] = MagicMock()
        sys.modules["homeassistant.components.sensor"] = MagicMock()
        sys.modules["homeassistant.helpers.device_registry"] = MagicMock()
        sys.modules["homeassistant.helpers.typing"] = MagicMock()
        sys.modules["homeassistant.loader"] = MagicMock()


_mock_homeassistant()


MOCK_ESSENT_RESPONSE: dict[str, Any] = {
    "prices": [
        {
            "date": "2026-06-17",
            "electricity": {
                "energyType": "electricity",
                "unitOfMeasurement": "kWh",
                "vatPercentage": 21,
                "tariffs": [
                    {
                        "startDateTime": "2026-06-17T00:00:00",
                        "endDateTime": "2026-06-17T01:00:00",
                        "totalAmount": 0.254,
                        "totalAmountEx": 0.20992,
                        "totalAmountVat": 0.04408,
                        "groups": [
                            {
                                "description": "Beursprijs",
                                "type": "MARKET_PRICE",
                                "amount": 0.185,
                                "amountEx": 0.15289,
                            },
                            {
                                "description": "Inkoopvergoeding",
                                "type": "PURCHASING_FEE",
                                "amount": 0.010,
                                "amountEx": 0.00826,
                            },
                            {
                                "description": "Energiebelasting",
                                "type": "TAX",
                                "amount": 0.059,
                                "amountEx": 0.04876,
                            },
                        ],
                    },
                    {
                        "startDateTime": "2026-06-17T01:00:00",
                        "endDateTime": "2026-06-17T02:00:00",
                        "totalAmount": 0.231,
                        "totalAmountEx": 0.19091,
                        "totalAmountVat": 0.04009,
                        "groups": [
                            {
                                "description": "Beursprijs",
                                "type": "MARKET_PRICE",
                                "amount": 0.162,
                                "amountEx": 0.13388,
                            },
                            {
                                "description": "Inkoopvergoeding",
                                "type": "PURCHASING_FEE",
                                "amount": 0.010,
                                "amountEx": 0.00826,
                            },
                            {
                                "description": "Energiebelasting",
                                "type": "TAX",
                                "amount": 0.059,
                                "amountEx": 0.04876,
                            },
                        ],
                    },
                ],
            },
            "gas": {
                "energyType": "gas",
                "unitOfMeasurement": "m\u00b3",
                "vatPercentage": 21,
                "tariffs": [
                    {
                        "startDateTime": "2026-06-17T07:00:00",
                        "endDateTime": "2026-06-17T08:00:00",
                        "totalAmount": 0.789,
                        "totalAmountEx": 0.65207,
                        "totalAmountVat": 0.13693,
                        "groups": [
                            {
                                "description": "Beursprijs",
                                "type": "MARKET_PRICE",
                                "amount": 0.720,
                                "amountEx": 0.59504,
                            },
                            {
                                "description": "Inkoopvergoeding",
                                "type": "PURCHASING_FEE",
                                "amount": 0.07872,
                                "amountEx": 0.06506,
                            },
                            {
                                "description": "Energiebelasting",
                                "type": "TAX",
                                "amount": 0.7268,
                                "amountEx": 0.60066,
                            },
                        ],
                    },
                ],
            },
        },
    ],
    "currency": "EUR",
}


from custom_components.dynamic_energy_prices.providers import PricePoint  # noqa: E402


def _make_pricepoint(
    hour: int,
    total_price: float,
    energy_type: str = "ELECTRICITY",
) -> Any:
    """Create a mock PricePoint with the given parameters."""
    today = datetime.now().astimezone().date()
    return PricePoint(
        start=datetime(today.year, today.month, today.day, hour, 0, 0).astimezone(),
        end=datetime(today.year, today.month, today.day, hour + 1, 0, 0).astimezone(),
        total_price=total_price,
        currency="EUR",
        breakdown={
            "market_price": total_price - 0.069,
            "purchasing_fee": 0.010,
            "tax": 0.059,
        },
    )
