"""Tests for the diagnostics module."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from custom_components.dynamic_energy_prices.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)


def _make_price_point(dt: datetime, total_price: float) -> Any:
    """Create a mock price point with isoformat support."""
    point = MagicMock()
    point.start.isoformat.return_value = dt.isoformat()
    point.end.isoformat.return_value = dt.isoformat()
    point.total_price = total_price
    point.breakdown = {"market_price": 0.18}
    return point


async def test_diagnostics_with_data(hass: Any) -> None:
    """Test diagnostics returns price data."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.last_exception = None
    coordinator.data = MagicMock()
    coordinator.data.electricity.unit = "EUR/kWh"
    coordinator.data.electricity.prices = [
        _make_price_point(datetime(2026, 6, 26, 0, 0), 0.25),
    ]
    coordinator.data.gas = None

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.as_dict.return_value = {"entry_id": "test_entry"}
    entry.runtime_data = coordinator

    result = await async_get_config_entry_diagnostics(hass, entry)
    assert "entry" in result
    assert "coordinator" in result
    assert "prices" in result
    assert result["coordinator"]["last_update_success"] is True
    assert result["coordinator"]["last_exception"] is None
    assert "gas" not in result["prices"]


async def test_diagnostics_with_gas(hass: Any) -> None:
    """Test diagnostics includes gas section when available."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.last_exception = None
    coordinator.data = MagicMock()
    coordinator.data.electricity.unit = "EUR/kWh"
    coordinator.data.electricity.prices = []
    coordinator.data.gas = MagicMock()
    coordinator.data.gas.unit = "EUR/m³"
    coordinator.data.gas.prices = [
        _make_price_point(datetime(2026, 6, 26, 7, 0), 0.789),
    ]

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.as_dict.return_value = {"entry_id": "test_entry"}
    entry.runtime_data = coordinator

    result = await async_get_config_entry_diagnostics(hass, entry)
    assert "gas" in result["prices"]


async def test_diagnostics_with_exception(hass: Any) -> None:
    """Test diagnostics includes last exception."""
    coordinator = MagicMock()
    coordinator.last_update_success = False
    coordinator.last_exception = ValueError("API error")
    coordinator.data = None

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.as_dict.return_value = {"entry_id": "test_entry"}
    entry.runtime_data = coordinator

    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["coordinator"]["last_update_success"] is False
    assert result["coordinator"]["last_exception"] == "API error"
    assert "prices" not in result


async def test_diagnostics_without_exception(hass: Any) -> None:
    """Test diagnostics when last_exception is None."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.last_exception = None
    coordinator.data = None

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.as_dict.return_value = {"entry_id": "test_entry"}
    entry.runtime_data = coordinator

    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["coordinator"]["last_exception"] is None


async def test_device_diagnostics(hass: Any) -> None:
    """Test device diagnostics delegates to config entry diagnostics."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.last_exception = None
    coordinator.data = None

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.as_dict.return_value = {"entry_id": "test_entry"}
    entry.runtime_data = coordinator

    device = MagicMock()
    result = await async_get_device_diagnostics(hass, entry, device)
    assert "entry" in result
