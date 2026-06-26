"""Tests for the Essent provider."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import importlib

import aiohttp
import pytest

from custom_components.dynamic_energy_prices.providers.base import (
    ProviderConnectionError,
    ProviderResponseError,
)
from custom_components.dynamic_energy_prices.providers.essent import (
    API_ENDPOINT,
    EssentPriceProvider,
)

from .conftest import MOCK_ESSENT_RESPONSE


@pytest.fixture
def provider() -> EssentPriceProvider:
    """Return an EssentPriceProvider instance."""
    return EssentPriceProvider()


@pytest.mark.asyncio
async def test_successful_fetch(provider: EssentPriceProvider) -> None:
    """Test successful price fetch."""
    if importlib.util.find_spec("pytest_homeassistant_custom_component") is not None:
        pytest.skip("aiohttp cleanup thread leaks on real HA instance")
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_ESSENT_RESPONSE)
        mock_get.return_value.__aenter__.return_value = mock_response

        prices = await provider.async_fetch_prices()

        assert prices.electricity.unit == "EUR/kWh"
        assert len(prices.electricity.prices) == 2
        assert prices.gas is not None
        assert len(prices.gas.prices) == 1
        assert prices.electricity.prices[0].total_price == 0.254
        assert prices.electricity.prices[0].breakdown["market_price"] == 0.185
        assert prices.gas.prices[0].total_price == 0.789

        mock_get.assert_called_once_with(
            API_ENDPOINT,
            headers={"Accept": "application/json", "x-request-origin": "client"},
        )


@pytest.mark.asyncio
async def test_401_unauthorized(provider: EssentPriceProvider) -> None:
    """Test 401 response handling."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ProviderConnectionError, match="401"):
            await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_500_server_error(provider: EssentPriceProvider) -> None:
    """Test 500 response handling."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ProviderConnectionError, match="500"):
            await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_connection_error(provider: EssentPriceProvider) -> None:
    """Test connection error handling."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.side_effect = aiohttp.ClientError("Connection refused")

        with pytest.raises(ProviderConnectionError, match="Failed to connect"):
            await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_invalid_json(provider: EssentPriceProvider) -> None:
    """Test invalid JSON response handling."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=ValueError("Expecting value"))
        mock_get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ProviderResponseError, match="Invalid JSON"):
            await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_missing_prices_field(provider: EssentPriceProvider) -> None:
    """Test response missing 'prices' field."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"currency": "EUR"})
        mock_get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ProviderResponseError, match="Missing"):
            await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_empty_prices_list(provider: EssentPriceProvider) -> None:
    """Test response with empty prices list."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "prices": [],
                "currency": "EUR",
                "electricityUnit": "EUR/kWh",
            }
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ProviderResponseError, match="no electricity prices"):
            await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_header_fix_applied(provider: EssentPriceProvider) -> None:
    """Verify the x-request-origin header fix is sent."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_ESSENT_RESPONSE)
        mock_get.return_value.__aenter__.return_value = mock_response

        await provider.async_fetch_prices()

        call_args = mock_get.call_args
        assert call_args is not None
        headers = call_args[1].get("headers", {})
        assert headers.get("x-request-origin") == "client"
        assert headers.get("Accept") == "application/json"


@pytest.mark.asyncio
async def test_fetch_for_date_not_supported(provider: EssentPriceProvider) -> None:
    """Verify Essent does not support date-specific fetching."""
    result = await provider.async_fetch_prices_for_date("2026-06-19")
    assert result is None


@pytest.mark.asyncio
async def test_breakdown_fields(provider: EssentPriceProvider) -> None:
    """Verify breakdown includes the correct field names from live API."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_ESSENT_RESPONSE)
        mock_get.return_value.__aenter__.return_value = mock_response

        prices = await provider.async_fetch_prices()

        for point in prices.electricity.prices:
            assert "market_price" in point.breakdown
            assert "supplier_markup" in point.breakdown
            assert "energy_tax" in point.breakdown
