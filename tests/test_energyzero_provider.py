"""Tests for the EnergyZero provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from zoneinfo import ZoneInfo

from custom_components.dynamic_energy_prices.providers.base import (
    ProviderConnectionError,
    ProviderResponseError,
)
from custom_components.dynamic_energy_prices.providers.energyzero import (
    API_ENDPOINT,
    EnergyZeroPriceProvider,
)

MOCK_ELECTRICITY_RESPONSE: dict = {
    "Prices": [
        {"readingDate": "2026-06-17T22:00:00Z", "price": 0.08234},
        {"readingDate": "2026-06-17T23:00:00Z", "price": 0.07856},
        {"readingDate": "2026-06-18T00:00:00Z", "price": 0.06543},
    ],
    "average": 0.07544,
    "fromDate": "2026-06-17T22:00:00Z",
    "tillDate": "2026-06-18T21:59:59Z",
    "intervalType": 4,
}

MOCK_GAS_RESPONSE: dict = {
    "Prices": [
        {"readingDate": "2026-06-17T22:00:00Z", "price": 0.78912},
        {"readingDate": "2026-06-18T00:00:00Z", "price": 0.76543},
    ],
    "average": 0.77728,
    "fromDate": "2026-06-17T22:00:00Z",
    "tillDate": "2026-06-18T21:59:59Z",
    "intervalType": 4,
}


@pytest.fixture
def provider() -> EnergyZeroPriceProvider:
    """Return an EnergyZeroPriceProvider instance."""
    return EnergyZeroPriceProvider()


def _make_mock_response(status: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock response with __aenter__ support."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data or {})
    mock_response.__aenter__.return_value = mock_response
    mock_response.__aexit__.return_value = None
    return mock_response


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock aiohttp.ClientSession to prevent real connector creation."""
    mock_get = MagicMock()
    mock_session = MagicMock()
    mock_session.get = mock_get
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session_class.return_value.__aenter__.return_value = mock_session
        yield mock_session


@pytest.mark.asyncio
async def test_successful_fetch(
    provider: EnergyZeroPriceProvider, mock_session: MagicMock
) -> None:
    """Test successful price fetch."""
    elec_resp = _make_mock_response(json_data=MOCK_ELECTRICITY_RESPONSE)
    gas_resp = _make_mock_response(json_data=MOCK_GAS_RESPONSE)
    mock_session.get.side_effect = [elec_resp, gas_resp]

    prices = await provider.async_fetch_prices()

    assert prices.electricity.unit == "EUR/kWh"
    assert len(prices.electricity.prices) == 3
    assert prices.gas is not None
    assert len(prices.gas.prices) == 2
    assert prices.electricity.prices[0].total_price == 0.08234
    assert prices.gas.prices[0].total_price == 0.78912


@pytest.mark.asyncio
async def test_successful_fetch_electricity_only(
    provider: EnergyZeroPriceProvider, mock_session: MagicMock
) -> None:
    """Test successful fetch with only electricity prices."""
    elec_resp = _make_mock_response(json_data=MOCK_ELECTRICITY_RESPONSE)
    gas_resp = _make_mock_response(json_data={"Prices": []})
    mock_session.get.side_effect = [elec_resp, gas_resp]

    prices = await provider.async_fetch_prices()

    assert prices.electricity is not None
    assert prices.gas is None


@pytest.mark.asyncio
async def test_http_error(
    provider: EnergyZeroPriceProvider, mock_session: MagicMock
) -> None:
    """Test HTTP error handling."""
    elec_resp = _make_mock_response(status=500)
    mock_session.get.return_value = elec_resp

    with pytest.raises(ProviderConnectionError, match="500"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_connection_error(
    provider: EnergyZeroPriceProvider, mock_session: MagicMock
) -> None:
    """Test connection error handling."""
    mock_session.get.side_effect = aiohttp.ClientError("Connection refused")

    with pytest.raises(ProviderConnectionError, match="Failed to connect"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_empty_electricity_prices(
    provider: EnergyZeroPriceProvider, mock_session: MagicMock
) -> None:
    """Test response with empty electricity prices list."""
    empty_resp = _make_mock_response(json_data={"Prices": []})
    mock_session.get.side_effect = [empty_resp, empty_resp]

    with pytest.raises(ProviderResponseError, match="no electricity prices"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_non_dict_response(
    provider: EnergyZeroPriceProvider, mock_session: MagicMock
) -> None:
    """Test non-dict response handling."""
    elec_resp = _make_mock_response(json_data=["not", "a", "dict"])
    mock_session.get.return_value = elec_resp

    with pytest.raises(ProviderResponseError, match="non-dict"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_fetch_for_date(
    provider: EnergyZeroPriceProvider, mock_session: MagicMock
) -> None:
    """Test fetching prices for a specific date."""
    elec_resp = _make_mock_response(json_data=MOCK_ELECTRICITY_RESPONSE)
    gas_resp = _make_mock_response(json_data=MOCK_GAS_RESPONSE)
    mock_session.get.side_effect = [elec_resp, gas_resp]

    prices = await provider.async_fetch_prices_for_date("2026-06-19")

    assert prices is not None
    assert len(prices.electricity.prices) == 3
    assert prices.gas is not None
    assert len(prices.gas.prices) == 2
