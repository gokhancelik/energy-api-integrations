"""Tests for the coordinator module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

import importlib

from datetime import datetime, timezone

from custom_components.dynamic_energy_prices.providers.base import (
    EnergyPriceSeries,
    PricePoint,
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


@pytest.mark.asyncio
async def test_coordinator_tomorrow_data_populated(hass: Any) -> None:
    """Test that tomorrow_data is populated after a successful update."""
    with (
        patch(
            "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
        ) as mock_fetch,
        patch(
            "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices_for_date"
        ) as mock_fetch_tomorrow,
    ):
        from custom_components.dynamic_energy_prices.coordinator import (
            DynamicPriceCoordinator,
        )

        now = datetime.now(timezone.utc)
        mock_fetch.return_value = ProviderPrices(
            electricity=EnergyPriceSeries(
                prices=[PricePoint(start=now, end=now, total_price=0.1)],
                unit="EUR/kWh",
            ),
        )

        mock_fetch_tomorrow.return_value = ProviderPrices(
            electricity=EnergyPriceSeries(
                prices=[PricePoint(start=now, end=now, total_price=0.2)],
                unit="EUR/kWh",
            ),
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
        await coordinator._async_update_data()

        mock_fetch_tomorrow.assert_called_once()
        assert coordinator.tomorrow_data is not None
        assert coordinator.tomorrow_data.electricity.prices[0].total_price == 0.2


@pytest.mark.asyncio
async def test_coordinator_tomorrow_data_none_on_failure(hass: Any) -> None:
    """Test that tomorrow_data is None when tomorrow fetch fails."""
    with (
        patch(
            "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
        ) as mock_fetch,
        patch(
            "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices_for_date"
        ) as mock_fetch_tomorrow,
    ):
        from custom_components.dynamic_energy_prices.coordinator import (
            DynamicPriceCoordinator,
        )

        now = datetime.now(timezone.utc)
        mock_fetch.return_value = ProviderPrices(
            electricity=EnergyPriceSeries(
                prices=[PricePoint(start=now, end=now, total_price=0.1)],
                unit="EUR/kWh",
            ),
        )

        mock_fetch_tomorrow.side_effect = ProviderConnectionError("API unreachable")

        entry = type(
            "ConfigEntry",
            (),
            {
                "entry_id": "test",
                "data": {"provider": "essent"},
            },
        )()

        coordinator = DynamicPriceCoordinator(hass, entry)
        await coordinator._async_update_data()

        assert coordinator.tomorrow_data is None


@pytest.mark.asyncio
async def test_coordinator_issue_raised_after_consecutive_failures(hass: Any) -> None:
    """Test that a repair issue is created after N consecutive failures."""
    from custom_components.dynamic_energy_prices.const import CONSECUTIVE_FAILURE_LIMIT
    from custom_components.dynamic_energy_prices.coordinator import (
        DynamicPriceCoordinator,
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

    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.side_effect = ProviderConnectionError("API unreachable")

        for i in range(CONSECUTIVE_FAILURE_LIMIT):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

    issues = getattr(hass, "issues", None)
    if issues is not None:
        issues.async_create_issue.assert_called_once()
        call_args = issues.async_create_issue.call_args
        assert call_args[0][0] == "dynamic_energy_prices"
        assert call_args[0][1] == "provider_unreachable"
        assert call_args[1]["severity"] == "error"


@pytest.mark.asyncio
@pytest.mark.skipif(
    importlib.util.find_spec("pytest_homeassistant_custom_component") is not None,
    reason="requires mock hass (pytest-homeassistant-custom-component creates real HA with socket conflicts)",
)
async def test_coordinator_issue_cleared_on_success(hass: Any) -> None:
    """Test that the repair issue is deleted when data fetches successfully."""
    from custom_components.dynamic_energy_prices.const import CONSECUTIVE_FAILURE_LIMIT
    from custom_components.dynamic_energy_prices.coordinator import (
        DynamicPriceCoordinator,
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

    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.side_effect = ProviderConnectionError("API unreachable")

        for i in range(CONSECUTIVE_FAILURE_LIMIT):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

    issues = getattr(hass, "issues", None)
    if issues is not None:
        issues.async_delete_issue.assert_not_called()

    mock_fetch.side_effect = None
    mock_fetch.return_value = ProviderPrices(
        electricity=type(
            "EnergyPriceSeries",
            (),
            {"prices": [], "unit": "EUR/kWh"},
        )(),
    )
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices_for_date"
    ) as mock_fetch_tomorrow:
        mock_fetch_tomorrow.return_value = None
        await coordinator._async_update_data()

    issues = getattr(hass, "issues", None)
    if issues is not None:
        issues.async_delete_issue.assert_called_once_with(
            "dynamic_energy_prices", "provider_unreachable"
        )


@pytest.mark.asyncio
async def test_coordinator_no_issue_below_threshold(hass: Any) -> None:
    """Test that no repair issue is created before reaching the failure limit."""
    from custom_components.dynamic_energy_prices.const import CONSECUTIVE_FAILURE_LIMIT
    from custom_components.dynamic_energy_prices.coordinator import (
        DynamicPriceCoordinator,
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

    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        mock_fetch.side_effect = ProviderConnectionError("API unreachable")

        for i in range(CONSECUTIVE_FAILURE_LIMIT - 1):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

    issues = getattr(hass, "issues", None)
    if issues is not None:
        issues.async_create_issue.assert_not_called()


@pytest.mark.asyncio
async def test_coordinator_last_successful_data(hass: Any) -> None:
    """Test the last_successful_data property."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        from custom_components.dynamic_energy_prices.coordinator import (
            DynamicPriceCoordinator,
        )

        now = datetime.now(timezone.utc)
        mock_fetch.return_value = ProviderPrices(
            electricity=EnergyPriceSeries(
                prices=[PricePoint(start=now, end=now, total_price=0.1)],
                unit="EUR/kWh",
            ),
        )
        with patch(
            "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices_for_date"
        ) as mock_fetch_tomorrow:
            mock_fetch_tomorrow.return_value = None

            entry = type(
                "ConfigEntry",
                (),
                {
                    "entry_id": "test",
                    "data": {"provider": "essent"},
                },
            )()

            coordinator = DynamicPriceCoordinator(hass, entry)
            assert coordinator.last_successful_data is None

            await coordinator._async_update_data()

            assert coordinator.last_successful_data is not None
            assert coordinator.last_successful_data.electricity.prices[0].total_price == 0.1


@pytest.mark.asyncio
async def test_coordinator_last_update_time(hass: Any) -> None:
    """Test the last_update_time property."""
    with patch(
        "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices"
    ) as mock_fetch:
        from custom_components.dynamic_energy_prices.coordinator import (
            DynamicPriceCoordinator,
        )

        now = datetime.now(timezone.utc)
        mock_fetch.return_value = ProviderPrices(
            electricity=EnergyPriceSeries(
                prices=[PricePoint(start=now, end=now, total_price=0.1)],
                unit="EUR/kWh",
            ),
        )
        with patch(
            "custom_components.dynamic_energy_prices.providers.essent.EssentPriceProvider.async_fetch_prices_for_date"
        ) as mock_fetch_tomorrow:
            mock_fetch_tomorrow.return_value = None

            entry = type(
                "ConfigEntry",
                (),
                {
                    "entry_id": "test",
                    "data": {"provider": "essent"},
                },
            )()

            coordinator = DynamicPriceCoordinator(hass, entry)
            assert coordinator.last_update_time is None

            await coordinator._async_update_data()

            assert coordinator.last_update_time is not None
            assert isinstance(coordinator.last_update_time, datetime)
