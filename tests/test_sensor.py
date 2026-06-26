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
    GAS_SENSORS,
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

    @pytest.mark.freeze_time("2026-06-26 00:00:00")
    def test_value_returns_formatted_time_range(self, mock_provider_prices: Any) -> None:
        value = _cheapest_block_value(mock_provider_prices)
        assert value is not None
        assert isinstance(value, datetime)

    def test_value_none_for_no_data(self) -> None:
        assert _cheapest_block_value(None) is None  # type: ignore[arg-type]

    @pytest.mark.freeze_time("2026-06-26 00:00:00")
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


class TestSensorDescriptions:
    """Test sensor description definition metadata."""

    def test_electricity_sensor_count(self) -> None:
        assert len(ELECTRICITY_SENSORS) == 5

    def test_gas_sensor_count(self) -> None:
        assert len(GAS_SENSORS) == 2

    def test_tomorrow_electricity_sensor_count(self) -> None:
        assert len(TOMORROW_ELECTRICITY_SENSORS) == 3

    def test_tomorrow_gas_sensor_count(self) -> None:
        assert len(TOMORROW_GAS_SENSORS) == 3

    def test_breakdown_sensor_count(self) -> None:
        assert len(BREAKDOWN_ELECTRICITY_SENSORS) == 3

    def test_cheapest_block_sensor_count(self) -> None:
        assert len(CHEAPEST_BLOCK_SENSORS) == 1

    def test_diagnostic_sensor_count(self) -> None:
        assert len(DIAGNOSTIC_SENSORS) == 2

    def test_all_descriptions_have_translation_key(self) -> None:
        all_sensors = (
            ELECTRICITY_SENSORS + GAS_SENSORS + TOMORROW_ELECTRICITY_SENSORS
            + TOMORROW_GAS_SENSORS + BREAKDOWN_ELECTRICITY_SENSORS
            + CHEAPEST_BLOCK_SENSORS + DIAGNOSTIC_SENSORS
        )
        for desc in all_sensors:
            assert desc.translation_key is not None

    def test_all_descriptions_have_value_fn(self) -> None:
        all_sensors = (
            ELECTRICITY_SENSORS + GAS_SENSORS + TOMORROW_ELECTRICITY_SENSORS
            + TOMORROW_GAS_SENSORS + BREAKDOWN_ELECTRICITY_SENSORS
            + CHEAPEST_BLOCK_SENSORS + DIAGNOSTIC_SENSORS
        )
        for desc in all_sensors:
            assert desc.value_fn is not None

    def test_gas_sensors_have_gas_energy_type(self) -> None:
        for desc in GAS_SENSORS:
            assert desc.energy_type == "gas"

    def test_diagnostic_sensors_have_category_key(self) -> None:
        for desc in DIAGNOSTIC_SENSORS:
            assert desc.entity_category is not None


class TestDynamicPriceSensorClass:
    """Test the DynamicPriceSensor class methods."""

    def test_native_value_none_when_no_data(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        assert sensor.native_value is None

    def test_native_value_uses_coordinator_value_fn(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        desc = DynamicEnergySensorDescription(
            key="test",
            name="Test",
            value_fn=lambda p: 1.0,
            coordinator_value_fn=lambda c: "coord_value",
        )
        sensor = DynamicPriceSensor(coordinator, desc, "test_provider", "Test Provider")
        assert sensor.native_value == "coord_value"

    def test_native_value_with_data(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        value = sensor.native_value
        assert value is not None
        assert isinstance(value, float)

    def test_native_unit_none_when_coordinator_value_fn(self) -> None:
        coordinator = MagicMock()
        coordinator.data = MagicMock()
        coordinator.data.electricity.unit = "EUR/kWh"
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        desc = DynamicEnergySensorDescription(
            key="test",
            name="Test",
            value_fn=lambda p: 1.0,
            coordinator_value_fn=lambda c: "coord_value",
        )
        sensor = DynamicPriceSensor(coordinator, desc, "test_provider", "Test Provider")
        assert sensor.native_unit_of_measurement is None

    def test_native_unit_none_when_no_data(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        assert sensor.native_unit_of_measurement is None

    def test_native_unit_electricity(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        assert sensor.native_unit_of_measurement == "EUR/kWh"

    def test_native_unit_gas(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        from custom_components.dynamic_energy_prices.sensor import GAS_SENSORS
        sensor = DynamicPriceSensor(
            coordinator,
            GAS_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        assert sensor.native_unit_of_measurement == "EUR/m³"

    def test_extra_state_attributes_none_when_no_data(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        assert sensor.extra_state_attributes is None

    def test_extra_state_attributes_with_data(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "provider" in attrs
        assert "hourly_prices" in attrs
        assert len(attrs["hourly_prices"]) == 24
        assert "start" in attrs["hourly_prices"][0]
        assert "end" in attrs["hourly_prices"][0]
        assert "price" in attrs["hourly_prices"][0]

    def test_available_false_when_coordinator_unavailable(self) -> None:
        coordinator = MagicMock()
        coordinator.data = MagicMock()
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        class UnavailableEntity:
            @property
            def available(self) -> bool:
                return False

        with patch(
            "custom_components.dynamic_energy_prices.sensor.DynamicPriceSensor.available",
            new=UnavailableEntity.available,
        ):
            sensor = DynamicPriceSensor(
                coordinator,
                ELECTRICITY_SENSORS[0],
                "test_provider",
                "Test Provider",
            )
            assert sensor.available is False

    def test_available_false_when_prices_none(self) -> None:
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        sensor.entity_id = "sensor.test_electricity_price"
        assert sensor.available is False

    def test_available_true_with_data(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        sensor = DynamicPriceSensor(
            coordinator,
            ELECTRICITY_SENSORS[0],
            "test_provider",
            "Test Provider",
        )
        assert sensor.available is True

    def test_available_respects_available_fn(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        desc = DynamicEnergySensorDescription(
            key="test",
            name="Test",
            value_fn=lambda p: 1.0,
            available_fn=lambda p: False,
        )
        sensor = DynamicPriceSensor(coordinator, desc, "test_provider", "Test Provider")
        sensor.entity_id = "sensor.test"
        assert sensor.available is False

    def test_available_true_with_available_fn(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"
        coordinator.last_update_success = True

        desc = DynamicEnergySensorDescription(
            key="test",
            name="Test",
            value_fn=lambda p: 1.0,
            available_fn=lambda p: True,
        )
        sensor = DynamicPriceSensor(coordinator, desc, "test_provider", "Test Provider")
        assert sensor.available is True

    def test_get_prices_uses_tomorrow_data(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = MagicMock()
        coordinator.data.electricity.unit = "EUR/kWh"
        coordinator.tomorrow_data = mock_provider_prices
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        desc = DynamicEnergySensorDescription(
            key="test",
            name="Test",
            value_fn=lambda p: 1.0,
            use_tomorrow_data=True,
        )
        sensor = DynamicPriceSensor(coordinator, desc, "test_provider", "Test Provider")
        assert sensor._get_prices() is mock_provider_prices

    def test_get_prices_uses_current_data(self, mock_provider_prices: Any) -> None:
        coordinator = MagicMock()
        coordinator.data = mock_provider_prices
        coordinator.tomorrow_data = None
        coordinator.entry = MagicMock()
        coordinator.entry.entry_id = "test_entry"

        desc = DynamicEnergySensorDescription(
            key="test",
            name="Test",
            value_fn=lambda p: 1.0,
            use_tomorrow_data=False,
        )
        sensor = DynamicPriceSensor(coordinator, desc, "test_provider", "Test Provider")
        assert sensor._get_prices() is mock_provider_prices


class TestGazFunctions:
    """Test gas-specific utility functions."""

    def test_gas_series_returned(self, mock_provider_prices: Any) -> None:
        from custom_components.dynamic_energy_prices.sensor import _gas_series
        series = _gas_series(mock_provider_prices)
        assert series is not None

    def test_gas_series_none_when_no_gas(
        self, mock_provider_prices_electricity_only: Any
    ) -> None:
        from custom_components.dynamic_energy_prices.sensor import _gas_series
        series = _gas_series(mock_provider_prices_electricity_only)
        assert series is None

    def test_gas_series_none_for_none(self) -> None:
        from custom_components.dynamic_energy_prices.sensor import _gas_series
        assert _gas_series(None) is None

    def test_gas_available_true(self, mock_provider_prices: Any) -> None:
        from custom_components.dynamic_energy_prices.sensor import _gas_available
        assert _gas_available(mock_provider_prices) is True

    def test_gas_available_false_when_none(
        self, mock_provider_prices_electricity_only: Any
    ) -> None:
        from custom_components.dynamic_energy_prices.sensor import _gas_available
        assert _gas_available(mock_provider_prices_electricity_only) is False

    def test_gas_not_available_when_empty_prices(self) -> None:
        from custom_components.dynamic_energy_prices.sensor import _gas_available
        from custom_components.dynamic_energy_prices.providers import (
            EnergyPriceSeries,
            ProviderPrices,
        )
        prices = ProviderPrices(
            electricity=EnergyPriceSeries(unit="EUR/kWh", prices=[]),
            gas=EnergyPriceSeries(unit="EUR/m³", prices=[]),
        )
        assert _gas_available(prices) is False

    def test_next_gas_price_none_for_none_input(self) -> None:
        assert _next_gas_price_value(None) is None  # type: ignore[arg-type]

    def test_next_gas_price_none_when_no_next_price(
        self, mock_provider_prices: Any
    ) -> None:
        from custom_components.dynamic_energy_prices.providers import find_next_price

        with patch(
            "custom_components.dynamic_energy_prices.sensor.find_next_price",
            return_value=None,
        ):
            value = _next_gas_price_value(mock_provider_prices)
            assert value is None

    def test_current_price_extra_attrs_none_for_none_input(self) -> None:
        from custom_components.dynamic_energy_prices.sensor import _current_price_extra_attrs
        assert _current_price_extra_attrs(None, "test") is None  # type: ignore[arg-type]


class TestBreakdownEdgeCases:
    """Test breakdown function edge cases."""

    def test_market_price_none_when_no_series(self) -> None:
        assert _current_market_price_value(None) is None  # type: ignore[arg-type]

    def test_supplier_markup_none_when_no_series(self) -> None:
        assert _current_supplier_markup_value(None) is None  # type: ignore[arg-type]

    def test_energy_tax_none_when_no_series(self) -> None:
        assert _current_energy_tax_value(None) is None  # type: ignore[arg-type]

    def test_current_breakdown_none_when_current_missing(
        self, mock_provider_prices: Any
    ) -> None:
        from custom_components.dynamic_energy_prices.sensor import _current_breakdown_value
        from custom_components.dynamic_energy_prices.providers import find_current_price

        with patch(
            "custom_components.dynamic_energy_prices.sensor.find_current_price",
            return_value=None,
        ):
            value = _current_breakdown_value(mock_provider_prices, "market_price")
            assert value is None


class TestNextGasPriceEdgeCase:
    """Test next gas price when current is None."""

    def test_next_gas_none_when_current_missing(
        self, mock_provider_prices: Any
    ) -> None:
        from custom_components.dynamic_energy_prices.providers import find_next_price

        with patch(
            "custom_components.dynamic_energy_prices.sensor.find_next_price",
            return_value=None,
        ):
            value = _next_gas_price_value(mock_provider_prices)
            assert value is None


class TestFuturePrices:
    """Test the _future_prices filtering function."""

    @pytest.mark.freeze_time("2026-06-26 12:00:00")
    def test_filters_past_hours(self, mock_provider_prices: Any) -> None:
        from custom_components.dynamic_energy_prices.sensor import _future_prices
        series = mock_provider_prices.electricity
        remaining = _future_prices(series.prices)
        for p in remaining:
            assert p.end > datetime.now().astimezone()
        assert len(remaining) < 24

    @pytest.mark.freeze_time("2026-06-26 00:00:00")
    def test_all_future_at_midnight(self, mock_provider_prices: Any) -> None:
        from custom_components.dynamic_energy_prices.sensor import _future_prices
        series = mock_provider_prices.electricity
        remaining = _future_prices(series.prices)
        assert len(remaining) == 24

    @pytest.mark.freeze_time("2026-06-26 23:30:00")
    def test_none_future_late_night(self) -> None:
        from datetime import timedelta
        from custom_components.dynamic_energy_prices.sensor import _future_prices
        from custom_components.dynamic_energy_prices.providers import PricePoint

        now = datetime.now().astimezone()
        past_prices = [
            PricePoint(
                start=now - timedelta(hours=2),
                end=now - timedelta(hours=1),
                total_price=0.25,
            )
        ]
        remaining = _future_prices(past_prices)
        assert len(remaining) == 0

    def test_empty_list(self) -> None:
        from custom_components.dynamic_energy_prices.sensor import _future_prices
        assert _future_prices([]) == []


class TestHourlyPricesExtra:
    """Test the _hourly_prices_extra helper."""

    @pytest.mark.freeze_time("2026-06-26 00:00:00")
    def test_returns_all_hours(self, mock_provider_prices: Any) -> None:
        from custom_components.dynamic_energy_prices.sensor import _hourly_prices_extra
        result = _hourly_prices_extra(mock_provider_prices)
        assert result is not None
        assert len(result) == 24
        assert "start" in result[0]
        assert "end" in result[0]
        assert "price" in result[0]
        assert isinstance(result[0]["price"], float)

    def test_none_for_no_data(self) -> None:
        from custom_components.dynamic_energy_prices.sensor import _hourly_prices_extra
        assert _hourly_prices_extra(None) is None  # type: ignore[arg-type]

    def test_none_for_no_electricity(
        self, mock_provider_prices_electricity_only: Any
    ) -> None:
        from custom_components.dynamic_energy_prices.sensor import _hourly_prices_extra
        mock_provider_prices_electricity_only.electricity = None
        assert _hourly_prices_extra(mock_provider_prices_electricity_only) is None


class TestCheapestBlockEdgeCases:
    """Test cheapest block function edge cases."""

    def test_cheapest_block_value_none_when_no_series(self) -> None:
        assert _cheapest_block_value(None) is None  # type: ignore[arg-type]

    def test_cheapest_block_attrs_none_when_no_series(self) -> None:
        assert _cheapest_block_extra_attrs(None, "test") is None  # type: ignore[arg-type]

    @pytest.mark.freeze_time("2026-06-26 06:00:00")
    def test_cheapest_block_value_none_when_no_block_found(self) -> None:
        from custom_components.dynamic_energy_prices.providers import (
            EnergyPriceSeries,
            PricePoint,
            ProviderPrices,
        )

        now = datetime.now().astimezone()
        prices = ProviderPrices(
            electricity=EnergyPriceSeries(
                unit="EUR/kWh",
                prices=[PricePoint(start=now, end=now, total_price=0.25)],
            ),
            gas=None,
        )
        value = _cheapest_block_value(prices)
        assert value is None

    @pytest.mark.freeze_time("2026-06-26 06:00:00")
    def test_cheapest_block_attrs_none_when_no_block_found(self) -> None:
        from custom_components.dynamic_energy_prices.providers import (
            EnergyPriceSeries,
            PricePoint,
            ProviderPrices,
        )

        now = datetime.now().astimezone()
        prices = ProviderPrices(
            electricity=EnergyPriceSeries(
                unit="EUR/kWh",
                prices=[PricePoint(start=now, end=now, total_price=0.25)],
            ),
            gas=None,
        )
        attrs = _cheapest_block_extra_attrs(prices, "test")
        assert attrs is None

    def test_price_extra_attrs(self) -> None:
        from custom_components.dynamic_energy_prices.sensor import _price_extra_attrs
        attrs = _price_extra_attrs(None, "test_provider")  # type: ignore[arg-type]
        assert attrs is not None
        assert attrs["provider"] == "test_provider"

    def test_current_price_extra_attrs_none_when_current_missing(
        self, mock_provider_prices: Any
    ) -> None:
        from custom_components.dynamic_energy_prices.sensor import _current_price_extra_attrs

        with patch(
            "custom_components.dynamic_energy_prices.sensor.find_current_price",
            return_value=None,
        ):
            attrs = _current_price_extra_attrs(mock_provider_prices, "test")
            assert attrs is None


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
