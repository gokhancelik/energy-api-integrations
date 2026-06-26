"""Tests for the binary_sensor module."""

from __future__ import annotations

from typing import Any
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.dynamic_energy_prices.binary_sensor import (
    CheapElectricityBinarySensor,
)
from custom_components.dynamic_energy_prices.const import (
    ATTR_AVERAGE_PRICE,
    ATTR_CURRENT_PRICE,
    ATTR_THRESHOLD,
    CONF_THRESHOLD,
)


def _make_sensor(
    mock_provider_prices: Any,
    options: dict[str, Any] | None = None,
) -> CheapElectricityBinarySensor:
    """Create a CheapElectricityBinarySensor with a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_provider_prices
    coordinator.entry = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.entry.options = options or {}
    coordinator.tomorrow_data = None
    return CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")


class TestCheapElectricityIsOn:
    """Test the is_on property of CheapElectricityBinarySensor."""

    def test_is_on_when_below_average(self, mock_provider_prices: Any) -> None:
        """Hour 5 price 0.198 < avg ~0.289 -> ON."""
        target = mock_provider_prices.electricity.prices[5]
        with patch(
            "custom_components.dynamic_energy_prices.binary_sensor.find_current_price",
            return_value=target,
        ):
            sensor = _make_sensor(mock_provider_prices)
            assert sensor.is_on is True

    def test_is_on_when_above_average(self, mock_provider_prices: Any) -> None:
        """Hour 15 price 0.390 > avg ~0.289 -> OFF."""
        target = mock_provider_prices.electricity.prices[15]
        with patch(
            "custom_components.dynamic_energy_prices.binary_sensor.find_current_price",
            return_value=target,
        ):
            sensor = _make_sensor(mock_provider_prices)
            assert sensor.is_on is False

    def test_is_on_none_when_no_data(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None
        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        assert sensor.is_on is None

    def test_is_on_none_when_no_electricity(
        self, mock_provider_prices_electricity_only: Any
    ) -> None:
        mock_provider_prices_electricity_only.electricity = None
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices_electricity_only
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None
        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        assert sensor.is_on is None

    def test_custom_threshold_overrides_average(self, mock_provider_prices: Any) -> None:
        """Threshold=0.15, current=0.198 -> OFF (0.198 < 0.15 is False)."""
        target = mock_provider_prices.electricity.prices[5]
        with patch(
            "custom_components.dynamic_energy_prices.binary_sensor.find_current_price",
            return_value=target,
        ):
            sensor = _make_sensor(mock_provider_prices, options={CONF_THRESHOLD: 0.15})
            assert sensor.is_on is False
            attrs = sensor.extra_state_attributes
            assert attrs is not None
            assert attrs[ATTR_THRESHOLD] == 0.15

    def test_custom_threshold_higher_than_current(self, mock_provider_prices: Any) -> None:
        """Threshold=0.30, current=0.198 -> ON (0.198 < 0.30)."""
        target = mock_provider_prices.electricity.prices[5]
        with patch(
            "custom_components.dynamic_energy_prices.binary_sensor.find_current_price",
            return_value=target,
        ):
            sensor = _make_sensor(mock_provider_prices, options={CONF_THRESHOLD: 0.30})
            assert sensor.is_on is True


class TestCheapElectricityAttributes:
    """Test the extra_state_attributes property."""

    def test_attributes_contain_price_average_and_threshold(
        self, mock_provider_prices: Any
    ) -> None:
        sensor = _make_sensor(mock_provider_prices)
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert ATTR_CURRENT_PRICE in attrs
        assert ATTR_AVERAGE_PRICE in attrs
        assert ATTR_THRESHOLD in attrs
        assert isinstance(attrs[ATTR_CURRENT_PRICE], float)
        assert isinstance(attrs[ATTR_AVERAGE_PRICE], float)
        assert isinstance(attrs[ATTR_THRESHOLD], float)
        assert attrs[ATTR_THRESHOLD] == attrs[ATTR_AVERAGE_PRICE]

    def test_attributes_none_when_no_data(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None
        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        assert sensor.extra_state_attributes is None


class TestCheapElectricityForceUpdate:
    """Test the force update method."""

    @pytest.mark.asyncio
    async def test_async_force_update_calls_coordinator(self) -> None:
        coordinator = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        coordinator.data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None

        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        await sensor.async_force_update()
        coordinator.async_request_refresh.assert_called_once()


class TestCheapElectricityDisabledByDefault:
    """Test that the cheap electricity binary sensor is disabled by default."""

    def test_disabled_by_default(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None
        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        assert sensor._attr_entity_registry_enabled_default is False


class TestCheapElectricityAvailable:
    """Test the available property of CheapElectricityBinarySensor."""

    def test_available_true_with_data(self, mock_provider_prices: Any) -> None:
        sensor = _make_sensor(mock_provider_prices)
        assert sensor.available is True

    def test_available_false_when_no_data(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None
        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        sensor.entity_id = "binary_sensor.test_cheap_electricity"
        assert sensor.available is False

    def test_is_on_none_when_threshold_cannot_compute(
        self, mock_provider_prices: Any
    ) -> None:
        mock_provider_prices.electricity = None
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None
        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        assert sensor.is_on is None
        assert sensor.extra_state_attributes is None

    def test_extra_state_attributes_all_none_when_missing_data(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.entry.options = {}
        coordinator.tomorrow_data = None
        sensor = CheapElectricityBinarySensor(coordinator, "test_provider", "Test Provider")
        assert sensor.extra_state_attributes is None
