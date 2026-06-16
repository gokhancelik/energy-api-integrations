"""Tests for the __init__ module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_entry() -> Mock:
    """Create a mock config entry."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.data = {"provider": "essent"}
    entry.title = "Essent"
    return entry


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant, mock_entry: Mock) -> None:
    """Test setting up a config entry."""
    with (
        patch(
            "custom_components.dynamic_energy_prices.DynamicPriceCoordinator"
        ) as mock_coordinator_class,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
    ):
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        from custom_components.dynamic_energy_prices import async_setup_entry

        result = await async_setup_entry(hass, mock_entry)

        assert result is True
        assert "dynamic_energy_prices" in hass.data
        assert mock_entry.entry_id in hass.data["dynamic_energy_prices"]


@pytest.mark.asyncio
async def test_unload_entry(hass: HomeAssistant, mock_entry: Mock) -> None:
    """Test unloading a config entry."""
    with (
        patch(
            "custom_components.dynamic_energy_prices.DynamicPriceCoordinator"
        ) as mock_coordinator_class,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
    ):
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        from custom_components.dynamic_energy_prices import (
            async_setup_entry,
            async_unload_entry,
        )

        await async_setup_entry(hass, mock_entry)
        result = await async_unload_entry(hass, mock_entry)

        assert result is True
        assert mock_entry.entry_id not in hass.data["dynamic_energy_prices"]
