"""Tests for the EnergyZero provider."""

from __future__ import annotations

from typing import Any

import aiohttp
import pytest

from custom_components.dynamic_energy_prices.providers.base import (
    ProviderConnectionError,
    ProviderResponseError,
)
from custom_components.dynamic_energy_prices.providers.energyzero import (
    EnergyZeroPriceProvider,
)

from .conftest import mock_http_response

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


@pytest.mark.asyncio
async def test_successful_fetch(
    provider: EnergyZeroPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test successful price fetch."""
    elec_resp = mock_http_response(json_data=MOCK_ELECTRICITY_RESPONSE)
    gas_resp = mock_http_response(json_data=MOCK_GAS_RESPONSE)
    mock_aiohttp_session.get.side_effect = [elec_resp, gas_resp]

    prices = await provider.async_fetch_prices()

    assert prices.electricity.unit == "EUR/kWh"
    assert len(prices.electricity.prices) == 3
    assert prices.gas is not None
    assert len(prices.gas.prices) == 2
    assert prices.electricity.prices[0].total_price == 0.08234
    assert prices.gas.prices[0].total_price == 0.78912


@pytest.mark.asyncio
async def test_successful_fetch_electricity_only(
    provider: EnergyZeroPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test successful fetch with only electricity prices."""
    elec_resp = mock_http_response(json_data=MOCK_ELECTRICITY_RESPONSE)
    gas_resp = mock_http_response(json_data={"Prices": []})
    mock_aiohttp_session.get.side_effect = [elec_resp, gas_resp]

    prices = await provider.async_fetch_prices()

    assert prices.electricity is not None
    assert prices.gas is None


@pytest.mark.asyncio
async def test_http_error(
    provider: EnergyZeroPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test HTTP error handling."""
    elec_resp = mock_http_response(status=500)
    mock_aiohttp_session.get.return_value = elec_resp

    with pytest.raises(ProviderConnectionError, match="500"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_connection_error(
    provider: EnergyZeroPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test connection error handling."""
    mock_aiohttp_session.get.side_effect = aiohttp.ClientError("Connection refused")

    with pytest.raises(ProviderConnectionError, match="Failed to connect"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_empty_electricity_prices(
    provider: EnergyZeroPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test response with empty electricity prices list."""
    empty_resp = mock_http_response(json_data={"Prices": []})
    mock_aiohttp_session.get.side_effect = [empty_resp, empty_resp]

    with pytest.raises(ProviderResponseError, match="no electricity prices"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_non_dict_response(
    provider: EnergyZeroPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test non-dict response handling."""
    elec_resp = mock_http_response(json_data=["not", "a", "dict"])
    mock_aiohttp_session.get.return_value = elec_resp

    with pytest.raises(ProviderResponseError, match="non-dict"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_fetch_for_date(
    provider: EnergyZeroPriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test fetching prices for a specific date."""
    elec_resp = mock_http_response(json_data=MOCK_ELECTRICITY_RESPONSE)
    gas_resp = mock_http_response(json_data=MOCK_GAS_RESPONSE)
    mock_aiohttp_session.get.side_effect = [elec_resp, gas_resp]

    prices = await provider.async_fetch_prices_for_date("2026-06-19")

    assert prices is not None
    assert len(prices.electricity.prices) == 3
    assert prices.gas is not None
    assert len(prices.gas.prices) == 2
