"""Dynamic Energy Prices integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DynamicEnergyPricesConfigEntry
from .coordinator import DynamicPriceCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: DynamicEnergyPricesConfigEntry
) -> bool:
    """Set up Dynamic Energy Prices from a config entry."""
    coordinator = DynamicPriceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: DynamicEnergyPricesConfigEntry
) -> bool:
    """Unload a config entry."""
    coordinator = entry.runtime_data
    await coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data = None  # type: ignore[arg-type]

    return unload_ok
