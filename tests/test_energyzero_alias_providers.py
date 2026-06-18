"""Tests for EnergyZero alias providers (Eneco and similar white-label resellers)."""

from __future__ import annotations

import pytest

from custom_components.dynamic_energy_prices.providers.base import PROVIDER_REGISTRY
from custom_components.dynamic_energy_prices.providers.energyzero import EnergyZeroPriceProvider
from custom_components.dynamic_energy_prices.providers.eneco import EnecoPriceProvider


@pytest.mark.asyncio
async def test_eneco_registration() -> None:
    """Verify Eneco is registered in the provider registry."""
    assert "eneco" in PROVIDER_REGISTRY
    assert PROVIDER_REGISTRY["eneco"] is EnecoPriceProvider


@pytest.mark.asyncio
async def test_eneco_is_energyzero_subclass() -> None:
    """Verify Eneco inherits from EnergyZero."""
    assert issubclass(EnecoPriceProvider, EnergyZeroPriceProvider)


@pytest.mark.asyncio
async def test_eneco_provider_ids() -> None:
    """Verify Eneco has distinct provider_id and display_name."""
    assert EnecoPriceProvider.provider_id == "eneco"
    assert EnecoPriceProvider.display_name == "Eneco"
    assert EnecoPriceProvider.provider_id != EnergyZeroPriceProvider.provider_id
