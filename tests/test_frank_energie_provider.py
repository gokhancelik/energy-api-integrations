"""Tests for the Frank Energie provider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import aiohttp
import pytest
import voluptuous as vol

from custom_components.dynamic_energy_prices.const import CONF_COUNTRY
from custom_components.dynamic_energy_prices.providers.base import (
    ProviderConnectionError,
    ProviderResponseError,
)
from custom_components.dynamic_energy_prices.providers.frank_energie import (
    API_ENDPOINT,
    COUNTRY_BE,
    COUNTRY_NL,
    FrankEnergiePriceProvider,
)

from .conftest import mock_http_response

MOCK_MARKET_PRICES_RESPONSE: dict = {
    "data": {
        "marketPrices": {
            "electricityPrices": [
                {
                    "from": "2026-06-17T00:00:00.000Z",
                    "till": "2026-06-17T01:00:00.000Z",
                    "marketPrice": 0.05012,
                    "marketPriceTax": 0.01053,
                    "sourcingMarkupPrice": 0.00850,
                    "energyTaxPrice": 0.11533,
                    "perUnit": 0.18448,
                },
                {
                    "from": "2026-06-17T01:00:00.000Z",
                    "till": "2026-06-17T02:00:00.000Z",
                    "marketPrice": 0.04567,
                    "marketPriceTax": 0.00959,
                    "sourcingMarkupPrice": 0.00850,
                    "energyTaxPrice": 0.11533,
                    "perUnit": 0.17909,
                },
            ],
            "gasPrices": [
                {
                    "from": "2026-06-17T05:00:00.000Z",
                    "till": "2026-06-18T05:00:00.000Z",
                    "marketPrice": 0.32045,
                    "marketPriceTax": 0.06729,
                    "sourcingMarkupPrice": 0.04500,
                    "energyTaxPrice": 0.59253,
                    "perUnit": 1.02527,
                },
            ],
        }
    }
}


@pytest.fixture
def provider() -> FrankEnergiePriceProvider:
    """Return a FrankEnergiePriceProvider instance."""
    return FrankEnergiePriceProvider()


@pytest.mark.asyncio
async def test_successful_fetch(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test successful price fetch."""
    resp = mock_http_response(json_data=MOCK_MARKET_PRICES_RESPONSE)
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    prices = await provider.async_fetch_prices()

    assert prices.electricity.unit == "EUR/kWh"
    assert len(prices.electricity.prices) == 2
    assert prices.gas is not None
    assert len(prices.gas.prices) == 1
    assert prices.electricity.prices[0].total_price == 0.18448
    assert prices.electricity.prices[0].breakdown["market_price"] == 0.05012
    assert prices.electricity.prices[0].breakdown["energy_tax"] == 0.11533
    assert prices.gas.prices[0].total_price == 1.02527


@pytest.mark.asyncio
async def test_successful_fetch_electricity_only(
    provider: FrankEnergiePriceProvider,
    mock_aiohttp_session: Any,
) -> None:
    """Test successful fetch with only electricity prices."""
    mock_data = {
        "data": {
            "marketPrices": {
                "electricityPrices": [
                    {
                        "from": "2026-06-17T00:00:00.000Z",
                        "till": "2026-06-17T01:00:00.000Z",
                        "marketPrice": 0.05,
                        "perUnit": 0.18,
                    },
                ],
                "gasPrices": [],
            }
        }
    }
    resp = mock_http_response(json_data=mock_data)
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    prices = await provider.async_fetch_prices()

    assert prices.electricity is not None
    assert len(prices.electricity.prices) == 1
    assert prices.gas is None


@pytest.mark.asyncio
async def test_http_error(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test HTTP error handling."""
    resp = mock_http_response(status=500)
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderConnectionError, match="500"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_connection_error(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test connection error handling."""
    mock_aiohttp_session.post.side_effect = aiohttp.ClientError("Connection refused")

    with pytest.raises(ProviderConnectionError, match="Failed to connect"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_invalid_json(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test invalid JSON response handling."""
    resp = mock_http_response()
    resp.json = AsyncMock(side_effect=ValueError("Expecting value"))
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderResponseError, match="Invalid JSON"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_graphql_error(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test GraphQL error response handling."""
    resp = mock_http_response(
        json_data={"errors": [{"message": "No marketprices found"}]}
    )
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderResponseError, match="GraphQL error"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_missing_market_prices(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test response missing marketPrices field."""
    resp = mock_http_response(json_data={"data": {}})
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderResponseError, match="marketPrices"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_empty_electricity_prices(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test response with empty electricity prices list."""
    resp = mock_http_response(
        json_data={
            "data": {
                "marketPrices": {
                    "electricityPrices": [],
                    "gasPrices": [],
                }
            }
        }
    )
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    with pytest.raises(ProviderResponseError, match="no electricity prices"):
        await provider.async_fetch_prices()


@pytest.mark.asyncio
async def test_breakdown_fields(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Verify breakdown includes the correct field names."""
    resp = mock_http_response(json_data=MOCK_MARKET_PRICES_RESPONSE)
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    prices = await provider.async_fetch_prices()

    for point in prices.electricity.prices:
        assert "market_price" in point.breakdown
        assert "supplier_markup" in point.breakdown
        assert "energy_tax" in point.breakdown


@pytest.mark.asyncio
async def test_fetch_for_date(
    provider: FrankEnergiePriceProvider, mock_aiohttp_session: Any
) -> None:
    """Test fetching prices for a specific date."""
    resp = mock_http_response(json_data=MOCK_MARKET_PRICES_RESPONSE)
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    prices = await provider.async_fetch_prices_for_date("2026-06-19")

    assert prices is not None
    assert len(prices.electricity.prices) == 2
    assert prices.gas is not None
    assert len(prices.gas.prices) == 1


@pytest.mark.asyncio
async def test_registration() -> None:
    """Verify the provider is registered in the registry."""
    from custom_components.dynamic_energy_prices.providers import PROVIDER_REGISTRY

    assert "frank_energie" in PROVIDER_REGISTRY
    assert PROVIDER_REGISTRY["frank_energie"] is FrankEnergiePriceProvider


def test_config_schema() -> None:
    """Verify config_schema returns the expected schema."""
    schema = FrankEnergiePriceProvider.config_schema()
    assert schema is not None
    assert CONF_COUNTRY in schema.schema
    assert isinstance(schema.schema[CONF_COUNTRY], vol.In)


def test_config_schema_values() -> None:
    """Verify config_schema allows NL and BE values."""
    schema = FrankEnergiePriceProvider.config_schema()
    country_schema = schema.schema[CONF_COUNTRY]
    assert COUNTRY_NL in country_schema.container
    assert COUNTRY_BE in country_schema.container


@pytest.mark.asyncio
async def test_belgium_header_sent(mock_aiohttp_session: Any) -> None:
    """Test that x-country: BE header is sent when BE is configured."""
    provider = FrankEnergiePriceProvider({CONF_COUNTRY: COUNTRY_BE})
    resp = mock_http_response(json_data=MOCK_MARKET_PRICES_RESPONSE)
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    await provider.async_fetch_prices()

    _, kwargs = mock_aiohttp_session.post.call_args
    assert "headers" in kwargs
    assert kwargs["headers"].get("x-country") == COUNTRY_BE


@pytest.mark.asyncio
async def test_nl_default_no_country_header(mock_aiohttp_session: Any) -> None:
    """Test that no x-country header is sent for NL (default)."""
    provider = FrankEnergiePriceProvider()
    resp = mock_http_response(json_data=MOCK_MARKET_PRICES_RESPONSE)
    mock_aiohttp_session.post.return_value.__aenter__.return_value = resp

    await provider.async_fetch_prices()

    _, kwargs = mock_aiohttp_session.post.call_args
    headers = kwargs.get("headers", {})
    assert "x-country" not in headers
