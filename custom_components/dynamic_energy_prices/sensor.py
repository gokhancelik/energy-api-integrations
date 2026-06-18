"""Sensors for Dynamic Energy Prices."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import ATTR_PRICE_BREAKDOWN, ATTR_PROVIDER, DOMAIN, SERVICE_FORCE_UPDATE
from .coordinator import DynamicPriceCoordinator
from .entity import DynamicPriceEntity
from .providers import (
    PROVIDER_REGISTRY,
    EnergyPriceSeries,
    ProviderPrices,
    calculate_average_price,
    calculate_max_price,
    calculate_min_price,
    find_current_price,
    find_next_price,
)


@dataclass(frozen=True, kw_only=True)
class DynamicEnergySensorDescription(SensorEntityDescription):
    """Description for dynamic energy price sensors."""

    value_fn: Callable[[ProviderPrices], StateType | None]
    extra_attrs_fn: Callable[[ProviderPrices, str], dict[str, Any] | None] | None = None
    available_fn: Callable[[ProviderPrices], bool] | None = None
    energy_type: str = "electricity"


def _electricity_series(prices: ProviderPrices | None) -> EnergyPriceSeries | None:
    if prices is None:
        return None
    return prices.electricity


def _gas_series(prices: ProviderPrices | None) -> EnergyPriceSeries | None:
    if prices is None:
        return None
    return prices.gas


def _current_price_value(prices: ProviderPrices) -> float | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    current = find_current_price(series.prices)
    return current.total_price if current else None


def _next_price_value(prices: ProviderPrices) -> float | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    next_price = find_next_price(series.prices)
    return next_price.total_price if next_price else None


def _average_price_value(prices: ProviderPrices) -> float | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    return calculate_average_price(series.prices)


def _lowest_price_value(prices: ProviderPrices) -> float | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    return calculate_min_price(series.prices)


def _highest_price_value(prices: ProviderPrices) -> float | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    return calculate_max_price(series.prices)


def _current_gas_price_value(prices: ProviderPrices) -> float | None:
    series = _gas_series(prices)
    if series is None:
        return None
    current = find_current_price(series.prices)
    return current.total_price if current else None


def _next_gas_price_value(prices: ProviderPrices) -> float | None:
    series = _gas_series(prices)
    if series is None:
        return None
    next_price = find_next_price(series.prices)
    return next_price.total_price if next_price else None


def _price_extra_attrs(
    prices: ProviderPrices, provider_id: str
) -> dict[str, Any] | None:
    data: dict[str, Any] = {
        ATTR_PROVIDER: provider_id,
    }
    return data


def _current_price_extra_attrs(
    prices: ProviderPrices, provider_id: str
) -> dict[str, Any] | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    current = find_current_price(series.prices)
    if current is None:
        return None
    data: dict[str, Any] = {
        ATTR_PROVIDER: provider_id,
        ATTR_PRICE_BREAKDOWN: current.breakdown,
    }
    return data


def _gas_available(prices: ProviderPrices) -> bool:
    return prices.gas is not None and len(prices.gas.prices) > 0


ELECTRICITY_SENSORS: tuple[DynamicEnergySensorDescription, ...] = (
    DynamicEnergySensorDescription(
        key="current_electricity_price",
        translation_key="current_electricity_price",
        name="Current electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_price_value,
        extra_attrs_fn=_current_price_extra_attrs,
    ),
    DynamicEnergySensorDescription(
        key="next_electricity_price",
        translation_key="next_electricity_price",
        name="Next electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_next_price_value,
        extra_attrs_fn=_price_extra_attrs,
    ),
    DynamicEnergySensorDescription(
        key="average_electricity_price",
        translation_key="average_electricity_price",
        name="Average electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_average_price_value,
        extra_attrs_fn=_price_extra_attrs,
    ),
    DynamicEnergySensorDescription(
        key="lowest_electricity_price",
        translation_key="lowest_electricity_price",
        name="Lowest electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_lowest_price_value,
        extra_attrs_fn=_price_extra_attrs,
        entity_registry_enabled_default=False,
    ),
    DynamicEnergySensorDescription(
        key="highest_electricity_price",
        translation_key="highest_electricity_price",
        name="Highest electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_highest_price_value,
        extra_attrs_fn=_price_extra_attrs,
        entity_registry_enabled_default=False,
    ),
)

GAS_SENSORS: tuple[DynamicEnergySensorDescription, ...] = (
    DynamicEnergySensorDescription(
        key="current_gas_price",
        translation_key="current_gas_price",
        name="Current gas price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_gas_price_value,
        extra_attrs_fn=_current_price_extra_attrs,
        available_fn=_gas_available,
    ),
    DynamicEnergySensorDescription(
        key="next_gas_price",
        translation_key="next_gas_price",
        name="Next gas price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_next_gas_price_value,
        extra_attrs_fn=_price_extra_attrs,
        available_fn=_gas_available,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: DynamicPriceCoordinator = hass.data[DOMAIN][entry.entry_id]
    provider_id = entry.data.get("provider", "")
    provider_cls = PROVIDER_REGISTRY.get(provider_id)
    provider_display_name = provider_cls.display_name if provider_cls else provider_id

    entities: list[DynamicPriceSensor] = []

    for description in ELECTRICITY_SENSORS:
        entities.append(
            DynamicPriceSensor(coordinator, description, provider_id, provider_display_name)
        )

    for description in GAS_SENSORS:
        entities.append(
            DynamicPriceSensor(coordinator, description, provider_id, provider_display_name)
        )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_FORCE_UPDATE,
        {},
        "async_force_update",
    )

    async_add_entities(entities)


class DynamicPriceSensor(DynamicPriceEntity, SensorEntity):
    """Representation of a dynamic energy price sensor."""

    entity_description: DynamicEnergySensorDescription

    def __init__(
        self,
        coordinator: DynamicPriceCoordinator,
        description: DynamicEnergySensorDescription,
        provider_id: str,
        provider_display_name: str = "",
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._provider_id = provider_id
        self._attr_name = f"{provider_display_name} {description.name}"
        super().__init__(coordinator)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        prices = self.coordinator.data
        if prices is None:
            return None
        if self.entity_description.energy_type == "gas" and prices.gas:
            return prices.gas.unit
        return prices.electricity.unit

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        prices = self.coordinator.data
        if prices is None:
            return None
        return self.entity_description.value_fn(prices)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        prices = self.coordinator.data
        if prices is None:
            return None
        if self.entity_description.extra_attrs_fn:
            return self.entity_description.extra_attrs_fn(prices, self._provider_id)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        prices = self.coordinator.data
        if prices is None:
            return False
        if self.entity_description.available_fn:
            return self.entity_description.available_fn(prices)
        return True

    async def async_force_update(self) -> None:
        """Force refresh price data from the provider."""
        await self.coordinator.async_request_refresh()
