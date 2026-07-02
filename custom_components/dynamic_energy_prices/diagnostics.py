"""Diagnostics support for Dynamic Energy Prices."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DynamicEnergyPricesConfigEntry
from .coordinator import DynamicPriceCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DynamicEnergyPricesConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DynamicPriceCoordinator = entry.runtime_data
    prices = coordinator.data

    diagnostics_data: dict[str, Any] = {
        "entry": entry.as_dict(),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
        },
    }

    if prices:
        diagnostics_data["prices"] = {
            "electricity": {
                "unit": prices.electricity.unit,
                "price_count": len(prices.electricity.prices),
                "prices": [
                    {
                        "start": p.start.isoformat(),
                        "end": p.end.isoformat(),
                        "total_price": p.total_price,
                        "breakdown": p.breakdown,
                    }
                    for p in prices.electricity.prices
                ],
            },
        }
        if prices.gas:
            diagnostics_data["prices"]["gas"] = {
                "unit": prices.gas.unit,
                "price_count": len(prices.gas.prices),
                "prices": [
                    {
                        "start": p.start.isoformat(),
                        "end": p.end.isoformat(),
                        "total_price": p.total_price,
                        "breakdown": p.breakdown,
                    }
                    for p in prices.gas.prices
                ],
            }

    return diagnostics_data


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: DynamicEnergyPricesConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    return await async_get_config_entry_diagnostics(hass, entry)
