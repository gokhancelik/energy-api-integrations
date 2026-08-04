"""Dynamic Energy Prices integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    DynamicEnergyPricesConfigEntry,
    SERVICE_INSTALL_DASHBOARD,
    SERVICE_UNINSTALL_DASHBOARD,
)
from .coordinator import DynamicPriceCoordinator
from .dashboard import install_dashboard, rebuild_installed_dashboard, uninstall_dashboard

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def _async_install_dashboard_service(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """Install or update the Energy Prices dashboard."""
    await install_dashboard(hass)


async def _async_uninstall_dashboard_service(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """Remove the Energy Prices dashboard."""
    await uninstall_dashboard(hass)


async def async_setup_entry(
    hass: HomeAssistant, entry: DynamicEnergyPricesConfigEntry
) -> bool:
    """Set up Dynamic Energy Prices from a config entry."""
    coordinator = DynamicPriceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await rebuild_installed_dashboard(hass)

    hass.services.async_register(
        DOMAIN,
        SERVICE_INSTALL_DASHBOARD,
        _async_install_dashboard_service,
        schema=vol.Schema({}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UNINSTALL_DASHBOARD,
        _async_uninstall_dashboard_service,
        schema=vol.Schema({}),
    )

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
