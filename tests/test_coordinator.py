"""Tests for the coordinator module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.dynamic_energy_prices.providers.base import (
    ProviderConnectionError,
    ProviderResponseError,
    ProviderPrices,
)


@pytest.mark.asyncio
async def test_coordinator_update_success(hass: Any) -> None:
    """Test successful coordinator update."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        from custom_components.dynamic_energy_prices.coordinator import (
            DynamicPriceCoordinator,
        )

        mock_fetch.return_value = ProviderPrices(
            electricity=type(
                "EnergyPriceSeries",
                (),
                {"prices": [], "unit": "EUR/kWh"},
            )(),
        )

        entry = type(
            "ConfigEntry",
            (),
            {
                "entry_id": "test",
                "data": {"provider": "essent"},
            },
        )()

        coordinator = DynamicPriceCoordinator(hass, entry)
        result = await coordinator._async_update_data()

        assert result is not None
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_coordinator_update_failure_connection(hass: Any) -> None:
    """Test coordinator update failure due to connection error raises UpdateFailed."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        from custom_components.dynamic_energy_prices.coordinator import (
            DynamicPriceCoordinator,
        )

        mock_fetch.side_effect = ProviderConnectionError("API unreachable")

        entry = type(
            "ConfigEntry",
            (),
            {
                "entry_id": "test",
                "data": {"provider": "essent"},
            },
        )()

        coordinator = DynamicPriceCoordinator(hass, entry)
        with pytest.raises(UpdateFailed, match="Connection error"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_failure_response(hass: Any) -> None:
    """Test coordinator update failure due to response error raises UpdateFailed."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        from custom_components.dynamic_energy_prices.coordinator import (
            DynamicPriceCoordinator,
        )

        mock_fetch.side_effect = ProviderResponseError("Bad data")

        entry = type(
            "ConfigEntry",
            (),
            {
                "entry_id": "test",
                "data": {"provider": "essent"},
            },
        )()

        coordinator = DynamicPriceCoordinator(hass, entry)
        with pytest.raises(UpdateFailed, match="Response error"):
            await coordinator._async_update_data()
