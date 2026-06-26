"""Binary sensors for Dynamic Energy Prices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_AVERAGE_PRICE, ATTR_CURRENT_PRICE, ATTR_THRESHOLD, DOMAIN, SERVICE_FORCE_UPDATE
from .coordinator import DynamicPriceCoordinator
from .entity import DynamicPriceEntity
from .providers import PROVIDER_REGISTRY, ProviderPrices, calculate_average_price, find_current_price


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: DynamicPriceCoordinator = hass.data[DOMAIN][entry.entry_id]
    provider_id = entry.data.get("provider", "")
    provider_cls = PROVIDER_REGISTRY.get(provider_id)
    provider_display_name = provider_cls.display_name if provider_cls else provider_id

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_FORCE_UPDATE,
        {},
        "async_force_update",
    )

    async_add_entities([
        CheapElectricityBinarySensor(coordinator, provider_id, provider_display_name),
    ])


class CheapElectricityBinarySensor(DynamicPriceEntity, BinarySensorEntity):
    """Binary sensor indicating when current electricity price is cheap."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: DynamicPriceCoordinator,
        provider_id: str,
        provider_display_name: str = "",
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = BinarySensorEntityDescription(
            key="cheap_electricity",
            translation_key="cheap_electricity",
            name="Cheap electricity",
        )
        self._provider_id = provider_id
        self._attr_name = f"{provider_display_name} Cheap electricity"
        super().__init__(coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the current price is below the threshold."""
        prices = self.coordinator.data
        if prices is None:
            return None
        series = prices.electricity
        if series is None:
            return None
        current = find_current_price(series.prices)
        if current is None:
            return None
        avg = calculate_average_price(series.prices)
        if avg is None:
            return None
        return current.total_price < avg

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        prices = self.coordinator.data
        if prices is None:
            return None
        series = prices.electricity
        if series is None:
            return None
        current = find_current_price(series.prices)
        avg = calculate_average_price(series.prices)
        if current is None or avg is None:
            return None
        return {
            ATTR_CURRENT_PRICE: current.total_price,
            ATTR_AVERAGE_PRICE: avg,
            ATTR_THRESHOLD: avg,
        }

    async def async_force_update(self) -> None:
        """Force refresh price data from the provider."""
        await self.coordinator.async_request_refresh()
