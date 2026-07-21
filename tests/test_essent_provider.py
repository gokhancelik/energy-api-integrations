"""Tests for the Essent provider."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

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

from .conftest import MOCK_ESSENT_RESPONSE, mock_http_response


@pytest.fixture
def provider() -> EssentPriceProvider:
    """Return an EssentPriceProvider instance."""
    return EssentPriceProvider()


@pytest.mark.asyncio
async def test_successful_fetch(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test successful price fetch."""
    resp = mock_http_response(200, MOCK_ESSENT_RESPONSE)
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    prices = await provider.async_fetch_prices()

    assert prices.electricity.unit == "EUR/kWh"
    assert len(prices.electricity.prices) == 2
    assert prices.gas is not None
    assert len(prices.gas.prices) == 1
    assert prices.electricity.prices[0].total_price == 0.254
    assert prices.electricity.prices[0].breakdown["market_price"] == 0.185
    assert prices.gas.prices[0].total_price == 0.789

    mock_aiohttp_session.get.assert_called_once_with(
        API_ENDPOINT,
        headers={"Accept": "application/json", "x-request-origin": "client"},
    )


@pytest.mark.asyncio
async def test_401_unauthorized(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test 401 response handling."""
    resp = mock_http_response(401)
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderConnectionError, match="401"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_500_server_error(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test 500 response handling."""
    resp = mock_http_response(500)
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderConnectionError, match="500"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_connection_error(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test connection error handling."""
    mock_aiohttp_session.get.side_effect = aiohttp.ClientError("Connection refused")

    with pytest.raises(ProviderConnectionError, match="Failed to connect"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_invalid_json(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test invalid JSON response handling."""
    resp = mock_http_response(200)
    resp.json = AsyncMock(side_effect=ValueError("Expecting value"))
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderResponseError, match="Invalid JSON"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_missing_prices_field(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test response missing 'prices' field."""
    resp = mock_http_response(200, {"currency": "EUR"})
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderResponseError, match="Missing"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_empty_prices_list(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test response with empty prices list."""
    resp = mock_http_response(
        200,
        {"prices": [], "currency": "EUR", "electricityUnit": "EUR/kWh"},
    )
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderResponseError, match="no price data"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_header_fix_applied(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Verify the x-request-origin header fix is sent."""
    resp = mock_http_response(200, MOCK_ESSENT_RESPONSE)
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    await provider.async_fetch_prices()

    call_args = mock_aiohttp_session.get.call_args
    assert call_args is not None
    headers = call_args[1].get("headers", {})
    assert headers.get("x-request-origin") == "client"
    assert headers.get("Accept") == "application/json"


@pytest.mark.asyncio
async def test_fetch_for_date(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Verify Essent returns cached data for a specific date."""
    resp = mock_http_response(200, MOCK_ESSENT_RESPONSE)
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    await provider.async_fetch_prices()

    result = await provider.async_fetch_prices_for_date("2026-06-17")
    assert result is not None
    assert len(result.electricity.prices) == 2
    assert result.electricity.prices[0].total_price == 0.254

    missing = await provider.async_fetch_prices_for_date("2026-06-19")
    assert missing is None


@pytest.mark.asyncio
async def test_breakdown_fields(
    provider: EssentPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Verify breakdown includes the correct field names from live API."""
    resp = mock_http_response(200, MOCK_ESSENT_RESPONSE)
    mock_aiohttp_session.get.return_value.__aenter__.return_value = resp

    prices = await provider.async_fetch_prices()

    for point in prices.electricity.prices:
        assert "market_price" in point.breakdown
        assert "supplier_markup" in point.breakdown
        assert "energy_tax" in point.breakdown
