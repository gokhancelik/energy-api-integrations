"""Tests for the sensor module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.dynamic_energy_prices.const import ATTR_PRICE_BREAKDOWN, ATTR_PROVIDER
from custom_components.dynamic_energy_prices.sensor import (
    DynamicEnergySensorDescription,
    DynamicPriceSensor,
    _current_price_value,
    _average_price_value,
    _lowest_price_value,
    _highest_price_value,
    _next_price_value,
    _current_gas_price_value,
    _next_gas_price_value,
)

from .conftest import mock_provider_prices, mock_provider_prices_electricity_only


class TestSensorValueFunctions:
    """Test the sensor value extraction functions."""

    def test_current_price_value(self, mock_provider_prices: Any) -> None:
        value = _current_price_value(mock_provider_prices)
        assert value is not None
        assert isinstance(value, float)

    def test_next_price_value(self, mock_provider_prices: Any) -> None:
        value = _next_price_value(mock_provider_prices)
        assert value is not None
        assert isinstance(value, float)

    def test_average_price_value(self, mock_provider_prices: Any) -> None:
        value = _average_price_value(mock_provider_prices)
        assert value is not None
        expected = sum(p.total_price for p in mock_provider_prices.electricity.prices) / 24
        assert abs(value - expected) < 0.001

    def test_lowest_price_value(self, mock_provider_prices: Any) -> None:
        value = _lowest_price_value(mock_provider_prices)
        assert value is not None
        assert value == 0.198

    def test_highest_price_value(self, mock_provider_prices: Any) -> None:
        value = _highest_price_value(mock_provider_prices)
        assert value is not None
        assert value == 0.400

    def test_current_gas_price(self, mock_provider_prices: Any) -> None:
        value = _current_gas_price_value(mock_provider_prices)
        assert value is not None
        assert isinstance(value, float)

    def test_next_gas_price(self, mock_provider_prices: Any) -> None:
        value = _next_gas_price_value(mock_provider_prices)
        assert value is not None
        assert isinstance(value, float)

    def test_gas_none_when_no_gas(
        self, mock_provider_prices_electricity_only: Any
    ) -> None:
        value = _current_gas_price_value(mock_provider_prices_electricity_only)
        assert value is None

    def test_value_none_for_none_input(self) -> None:
        assert _current_price_value(None) is None  # type: ignore[arg-type]
        assert _next_price_value(None) is None  # type: ignore[arg-type]
        assert _average_price_value(None) is None  # type: ignore[arg-type]
        assert _lowest_price_value(None) is None  # type: ignore[arg-type]
        assert _highest_price_value(None) is None  # type: ignore[arg-type]


class TestSensorDescription:
    """Test the sensor description dataclass."""

    def test_description_creation(self) -> None:
        description = DynamicEnergySensorDescription(
            key="test",
            name="Test",
            value_fn=lambda p: 1.0,
            energy_type="electricity",
        )
        assert description.key == "test"
        assert description.value_fn(None) == 1.0  # type: ignore[arg-type]
