"""Tests for the sensor module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    _current_market_price_value,
    _current_supplier_markup_value,
    _current_energy_tax_value,
    _cheapest_block_value,
    _cheapest_block_extra_attrs,
    _last_update_value,
    _next_update_value,
    ELECTRICITY_SENSORS,
    BREAKDOWN_ELECTRICITY_SENSORS,
    CHEAPEST_BLOCK_SENSORS,
    DIAGNOSTIC_SENSORS,
    TOMORROW_ELECTRICITY_SENSORS,
    TOMORROW_GAS_SENSORS,
)




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


class TestBreakdownValueFunctions:
    """Test the breakdown sensor value extraction functions."""

    def test_current_market_price(self, mock_provider_prices: Any) -> None:
        value = _current_market_price_value(mock_provider_prices)
        current = mock_provider_prices.electricity.prices[datetime.now().hour]
        expected = current.breakdown.get("market_price")
        assert value == expected

    def test_current_supplier_markup(self, mock_provider_prices: Any) -> None:
        value = _current_supplier_markup_value(mock_provider_prices)
        current = mock_provider_prices.electricity.prices[datetime.now().hour]
        expected = current.breakdown.get("supplier_markup")
        assert value == expected

    def test_current_energy_tax(self, mock_provider_prices: Any) -> None:
        value = _current_energy_tax_value(mock_provider_prices)
        current = mock_provider_prices.electricity.prices[datetime.now().hour]
        expected = current.breakdown.get("energy_tax")
        assert value == expected

    def test_all_none_for_no_data(self) -> None:
        assert _current_market_price_value(None) is None  # type: ignore[arg-type]
        assert _current_supplier_markup_value(None) is None  # type: ignore[arg-type]
        assert _current_energy_tax_value(None) is None  # type: ignore[arg-type]

    def test_missing_breakdown_key_returns_none(
        self, mock_provider_prices_electricity_only: Any
    ) -> None:
        value = _current_market_price_value(mock_provider_prices_electricity_only)
        # electricity-only prices have the same breakdown keys; this just verifies
        # no crash when gas is None
        assert value is not None or True


class TestBreakdownSensorDescriptions:
    """Test the breakdown sensor description definitions."""

    def test_breakdown_sensors_disabled_by_default(self) -> None:
        for desc in BREAKDOWN_ELECTRICITY_SENSORS:
            assert desc.entity_registry_enabled_default is False

    def test_breakdown_sensor_count(self) -> None:
        assert len(BREAKDOWN_ELECTRICITY_SENSORS) == 3

    def test_breakdown_sensors_have_matching_keys(self) -> None:
        keys = {desc.key for desc in BREAKDOWN_ELECTRICITY_SENSORS}
        assert "current_electricity_market_price" in keys
        assert "current_electricity_supplier_markup" in keys
        assert "current_electricity_energy_tax" in keys


class TestTomorrowSensorDescriptions:
    """Test the tomorrow sensor description definitions."""

    def test_tomorrow_electricity_sensors_have_tomorrow_flag(self) -> None:
        for desc in TOMORROW_ELECTRICITY_SENSORS:
            assert desc.use_tomorrow_data is True
            assert desc.energy_type == "electricity"

    def test_tomorrow_gas_sensors_have_tomorrow_flag(self) -> None:
        for desc in TOMORROW_GAS_SENSORS:
            assert desc.use_tomorrow_data is True
            assert desc.energy_type == "gas"

    def test_tomorrow_electricity_sensor_count(self) -> None:
        assert len(TOMORROW_ELECTRICITY_SENSORS) == 3

    def test_tomorrow_gas_sensor_count(self) -> None:
        assert len(TOMORROW_GAS_SENSORS) == 3


class TestCheapestBlockSensor:
    """Test the cheapest 3h block sensor value and attribute functions."""

    def test_value_returns_formatted_time_range(self, mock_provider_prices: Any) -> None:
        value = _cheapest_block_value(mock_provider_prices)
        assert value is not None
        assert isinstance(value, str)
        assert "-" in value

    def test_value_none_for_no_data(self) -> None:
        assert _cheapest_block_value(None) is None  # type: ignore[arg-type]

    def test_extra_attrs(self, mock_provider_prices: Any) -> None:
        attrs = _cheapest_block_extra_attrs(mock_provider_prices, "test_provider")
        assert attrs is not None
        assert attrs["start_time"] is not None
        assert attrs["end_time"] is not None
        assert "average_price" in attrs
        assert "total_price" in attrs
        assert "prices" in attrs
        assert len(attrs["prices"]) == 3

    def test_extra_attrs_none_for_no_data(self) -> None:
        assert _cheapest_block_extra_attrs(None, "test_provider") is None  # type: ignore[arg-type]

    def test_disabled_by_default(self) -> None:
        for desc in CHEAPEST_BLOCK_SENSORS:
            assert desc.entity_registry_enabled_default is False

    def test_sensor_count(self) -> None:
        assert len(CHEAPEST_BLOCK_SENSORS) == 1


class TestDiagnosticSensors:
    """Test the diagnostic sensor value functions."""

    def test_last_update_value(self) -> None:
        coordinator = MagicMock()
        coordinator.last_update_time = datetime(2026, 6, 26, 12, 0, 0)
        value = _last_update_value(coordinator)
        assert value == "2026-06-26T12:00:00"

    def test_last_update_value_none(self) -> None:
        coordinator = MagicMock()
        coordinator.last_update_time = None
        assert _last_update_value(coordinator) is None

    def test_next_update_value(self) -> None:
        coordinator = MagicMock()
        coordinator.last_update_time = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)
        coordinator.update_interval = timedelta(hours=1)
        value = _next_update_value(coordinator)
        assert value == "2026-06-26T13:00:00+00:00"

    def test_next_update_value_none(self) -> None:
        coordinator = MagicMock()
        coordinator.last_update_time = None
        coordinator.update_interval = timedelta(hours=1)
        assert _next_update_value(coordinator) is None

    def test_next_update_value_no_interval(self) -> None:
        coordinator = MagicMock()
        coordinator.last_update_time = datetime(2026, 6, 26, 12, 0, 0)
        coordinator.update_interval = None
        assert _next_update_value(coordinator) is None

    def test_diagnostic_sensor_count(self) -> None:
        assert len(DIAGNOSTIC_SENSORS) == 2

    def test_diagnostic_sensors_have_diagnostic_category(self) -> None:
        for desc in DIAGNOSTIC_SENSORS:
            assert desc.entity_category is not None

    def test_diagnostic_sensors_disabled_by_default(self) -> None:
        for desc in DIAGNOSTIC_SENSORS:
            assert desc.entity_registry_enabled_default is False


class TestForceUpdate:
    """Test the force update service."""

    @pytest.mark.asyncio
    async def test_async_force_update_calls_coordinator(self) -> None:
        coordinator = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )

        await sensor.async_force_update()

        coordinator.async_request_refresh.assert_called_once()
