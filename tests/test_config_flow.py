"""Tests for the config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.dynamic_energy_prices.const import CONF_PROVIDER, DOMAIN
from custom_components.dynamic_energy_prices.providers.base import (
    PROVIDER_REGISTRY,
    ProviderConnectionError,
    ProviderResponseError,
)


@pytest.fixture
def config_flow(hass: HomeAssistant) -> config_entries.ConfigFlow:
    """Return a config flow instance."""
    return config_entries.ConfigFlow(
        hass,
        {
            "source": config_entries.SOURCE_USER,
            "handler": DOMAIN,
        },
        config_entries.CONN_CLASS_CLOUD_POLL,
    )


@pytest.mark.asyncio
async def test_show_user_form(hass: HomeAssistant) -> None:
    """Test that the user form is shown initially."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_PROVIDER in result["data_schema"].schema


@pytest.mark.asyncio
async def test_create_entry_with_essent(hass: HomeAssistant) -> None:
    """Test creating an entry with Essent provider."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.return_value = type(
            "ProviderPrices",
            (),
            {
                "electricity": type(
                    "EnergyPriceSeries",
                    (),
                    {"prices": [], "unit": "EUR/kWh"},
                )(),
                "gas": None,
            },
        )()

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PROVIDER: "essent"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Essent"
        assert result["data"][CONF_PROVIDER] == "essent"


@pytest.mark.asyncio
async def test_connection_error_on_create(hass: HomeAssistant) -> None:
    """Test connection error is handled during flow."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.side_effect = ProviderConnectionError("Cannot connect")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PROVIDER: "essent"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_response_error_on_create(hass: HomeAssistant) -> None:
    """Test response error is handled during flow."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.side_effect = ProviderResponseError("Invalid response")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PROVIDER: "essent"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_response"


@pytest.mark.asyncio
async def test_abort_if_already_configured(hass: HomeAssistant) -> None:
    """Test abort when provider is already configured."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.return_value = type(
            "ProviderPrices",
            (),
            {
                "electricity": type(
                    "EnergyPriceSeries",
                    (),
                    {"prices": [], "unit": "EUR/kWh"},
                )(),
                "gas": None,
            },
        )()

        result1 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PROVIDER: "essent"},
        )
        assert result1["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

        result2 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PROVIDER: "essent"},
        )
        assert result2["type"] == data_entry_flow.FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_unknown_provider(hass: HomeAssistant) -> None:
    """Test error when provider is not in registry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_PROVIDER: "nonexistent"},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "unknown_provider"
