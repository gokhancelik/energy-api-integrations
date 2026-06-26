"""Tests for the config flow."""

from __future__ import annotations
from typing import Any
from unittest.mock import AsyncMock, patch

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("pytest_homeassistant_custom_component") is None,
    reason="requires pytest-homeassistant-custom-component",
)

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.dynamic_energy_prices.const import CONF_COUNTRY, CONF_PROVIDER, CONF_THRESHOLD, DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry
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


@pytest.mark.asyncio
async def test_frank_energie_shows_provider_options(hass: HomeAssistant) -> None:
    """Test that selecting Frank Energie goes to provider_options step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_PROVIDER: "frank_energie"},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "provider_options"


@pytest.mark.asyncio
async def test_frank_energie_create_with_be(hass: HomeAssistant) -> None:
    """Test creating a Frank Energie entry with Belgium selected."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.frank_energie.FrankEnergiePriceProvider.async_fetch_prices"
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
            data={CONF_PROVIDER: "frank_energie"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "provider_options"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_COUNTRY: "BE"},
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Frank Energie"
        assert result2["data"][CONF_PROVIDER] == "frank_energie"
        assert result2["data"][CONF_COUNTRY] == "BE"


@pytest.mark.asyncio
async def test_frank_energie_create_with_nl_default(hass: HomeAssistant) -> None:
    """Test creating a Frank Energie entry with default NL."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.frank_energie.FrankEnergiePriceProvider.async_fetch_prices"
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
            data={CONF_PROVIDER: "frank_energie"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "provider_options"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_COUNTRY: "NL"},
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Frank Energie"
        assert result2["data"][CONF_PROVIDER] == "frank_energie"
        assert result2["data"][CONF_COUNTRY] == "NL"


@pytest.mark.asyncio
async def test_frank_energie_provider_options_error(hass: HomeAssistant) -> None:
    """Test connection error in provider_options step."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.frank_energie.FrankEnergiePriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.side_effect = ProviderConnectionError("Cannot connect")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_PROVIDER: "frank_energie"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "provider_options"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_COUNTRY: "NL"},
        )
        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["step_id"] == "provider_options"
        assert result2["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_options_flow_init(
    hass: HomeAssistant,
    mock_essent_config_entry: config_entries.ConfigEntry,
) -> None:
    """Test that options flow shows the init form."""
    result = await hass.config_entries.options.async_init(
        mock_essent_config_entry.entry_id,
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_set_threshold(
    hass: HomeAssistant,
    mock_essent_config_entry: config_entries.ConfigEntry,
) -> None:
    """Test setting a custom price threshold via options flow."""
    result = await hass.config_entries.options.async_init(
        mock_essent_config_entry.entry_id,
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_THRESHOLD: 0.20},
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_THRESHOLD] == 0.20


@pytest.mark.asyncio
async def test_options_flow_clear_threshold(
    hass: HomeAssistant,
    mock_essent_config_entry: config_entries.ConfigEntry,
) -> None:
    """Test clearing the threshold (set to None) removes it from options."""
    # Set threshold first
    result = await hass.config_entries.options.async_init(
        mock_essent_config_entry.entry_id,
    )
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_THRESHOLD: 0.20},
    )

    # Clear it
    result2 = await hass.config_entries.options.async_init(
        mock_essent_config_entry.entry_id,
    )
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        user_input={CONF_THRESHOLD: None},
    )
    assert result3["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert CONF_THRESHOLD not in result3["data"]


@pytest.fixture
def mock_essent_config_entry(hass: HomeAssistant) -> config_entries.ConfigEntry:
    """Create a mock Essent config entry."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Essent",
        data={CONF_PROVIDER: "essent"},
        source="user",
        options={},
        entry_id="test_essent",
        pref_disable_new_entities=False,
        pref_disable_polling=False,
        unique_id=f"{DOMAIN}_essent",
    )
    entry.add_to_hass(hass)
    return entry
