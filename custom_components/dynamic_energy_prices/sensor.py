"""Sensors for Dynamic Energy Prices."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import ATTR_PRICE_BREAKDOWN, ATTR_PROVIDER, DOMAIN, SERVICE_FORCE_UPDATE
from .coordinator import DynamicPriceCoordinator
from .entity import DynamicPriceEntity
_LOGGER = logging.getLogger(__name__)

from .providers import (
    BREAKDOWN_ENERGY_TAX,
    BREAKDOWN_MARKET_PRICE,
    BREAKDOWN_SUPPLIER_MARKUP,
    PROVIDER_REGISTRY,
    CheapestBlock,
    EnergyPriceSeries,
    PriceProvider,
    ProviderPrices,
    calculate_average_price,
    calculate_max_price,
    calculate_min_price,
    find_cheapest_block,
    find_current_price,
    find_next_price,
)


@dataclass(frozen=True, kw_only=True)
class DynamicEnergySensorDescription(SensorEntityDescription):
    """Description for dynamic energy price sensors."""

    value_fn: Callable[[ProviderPrices], StateType | None]
    coordinator_value_fn: Callable[[DynamicPriceCoordinator], StateType | None] | None = None
    extra_attrs_fn: Callable[[ProviderPrices, str], dict[str, Any] | None] | None = None
    available_fn: Callable[[ProviderPrices], bool] | None = None
    energy_type: str = "electricity"
    use_tomorrow_data: bool = False


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


def _current_breakdown_value(
    prices: ProviderPrices, key: str
) -> float | None:
    """Extract a breakdown value from the current hour's price point."""
    series = _electricity_series(prices)
    if series is None:
        return None
    current = find_current_price(series.prices)
    if current is None:
        return None
    return current.breakdown.get(key)


def _current_market_price_value(prices: ProviderPrices) -> float | None:
    return _current_breakdown_value(prices, BREAKDOWN_MARKET_PRICE)


def _current_supplier_markup_value(prices: ProviderPrices) -> float | None:
    return _current_breakdown_value(prices, BREAKDOWN_SUPPLIER_MARKUP)


def _current_energy_tax_value(prices: ProviderPrices) -> float | None:
    return _current_breakdown_value(prices, BREAKDOWN_ENERGY_TAX)


def _future_prices(prices: list[PricePoint]) -> list[PricePoint]:
    """Filter to only price points that are still in the future."""
    now = datetime.now().astimezone()
    return [p for p in prices if p.end > now]


def _hourly_prices_extra(prices: ProviderPrices) -> list[dict[str, Any]] | None:
    """Extract hourly electricity prices as a list of {time, price} dicts."""
    series = _electricity_series(prices)
    if series is None:
        return None
    return [
        {
            "start": p.start.strftime("%H:%M"),
            "end": p.end.strftime("%H:%M"),
            "price": p.total_price,
        }
        for p in series.prices
    ]


def _cheapest_block_value(prices: ProviderPrices) -> datetime | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    remaining = _future_prices(series.prices)
    block = find_cheapest_block(remaining)
    if block is None:
        return None
    return block.start


def _cheapest_block_extra_attrs(
    prices: ProviderPrices, provider_id: str
) -> dict[str, Any] | None:
    series = _electricity_series(prices)
    if series is None:
        return None
    remaining = _future_prices(series.prices)
    block = find_cheapest_block(remaining)
    if block is None:
        return None
    return {
        ATTR_PROVIDER: provider_id,
        "start_time": block.start.strftime("%H:%M"),
        "end_time": block.end.strftime("%H:%M"),
        "average_price": block.average_price,
        "total_price": block.total_price,
        "prices": block.prices,
    }


def _last_update_value(coordinator: DynamicPriceCoordinator) -> str | None:
    """Return the last update time as an ISO datetime string."""
    if coordinator.last_update_time is None:
        return None
    return coordinator.last_update_time.isoformat()


def _next_update_value(coordinator: DynamicPriceCoordinator) -> str | None:
    """Return the next scheduled update time as an ISO datetime string."""
    if coordinator.last_update_time is None or coordinator.update_interval is None:
        return None
    next_time = coordinator.last_update_time + coordinator.update_interval
    return next_time.isoformat()


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
        "hourly_prices": [
            {
                "start": p.start.strftime("%H:%M"),
                "end": p.end.strftime("%H:%M"),
                "price": p.total_price,
            }
            for p in series.prices
        ],
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

CHEAPEST_BLOCK_SENSORS: tuple[DynamicEnergySensorDescription, ...] = (
    DynamicEnergySensorDescription(
        key="cheapest_3h_block_electricity",
        translation_key="cheapest_3h_block_electricity",
        name="Cheapest 3h block electricity",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_cheapest_block_value,
        extra_attrs_fn=_cheapest_block_extra_attrs,
        entity_registry_enabled_default=False,
    ),
)

DIAGNOSTIC_SENSORS: tuple[DynamicEnergySensorDescription, ...] = (
    DynamicEnergySensorDescription(
        key="last_updated",
        translation_key="last_updated",
        name="Last updated",
        value_fn=lambda _: None,
        coordinator_value_fn=_last_update_value,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    DynamicEnergySensorDescription(
        key="next_update",
        translation_key="next_update",
        name="Next update",
        value_fn=lambda _: None,
        coordinator_value_fn=_next_update_value,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)

BREAKDOWN_ELECTRICITY_SENSORS: tuple[DynamicEnergySensorDescription, ...] = (
    DynamicEnergySensorDescription(
        key="current_electricity_market_price",
        translation_key="current_electricity_market_price",
        name="Current electricity market price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_market_price_value,
        extra_attrs_fn=_price_extra_attrs,
        entity_registry_enabled_default=False,
    ),
    DynamicEnergySensorDescription(
        key="current_electricity_supplier_markup",
        translation_key="current_electricity_supplier_markup",
        name="Current electricity supplier markup",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_supplier_markup_value,
        extra_attrs_fn=_price_extra_attrs,
        entity_registry_enabled_default=False,
    ),
    DynamicEnergySensorDescription(
        key="current_electricity_energy_tax",
        translation_key="current_electricity_energy_tax",
        name="Current electricity energy tax",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_energy_tax_value,
        extra_attrs_fn=_price_extra_attrs,
        entity_registry_enabled_default=False,
    ),
)

TOMORROW_ELECTRICITY_SENSORS: tuple[DynamicEnergySensorDescription, ...] = (
    DynamicEnergySensorDescription(
        key="tomorrow_average_electricity_price",
        translation_key="tomorrow_average_electricity_price",
        name="Tomorrow average electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_average_price_value,
        extra_attrs_fn=_price_extra_attrs,
        use_tomorrow_data=True,
    ),
    DynamicEnergySensorDescription(
        key="tomorrow_lowest_electricity_price",
        translation_key="tomorrow_lowest_electricity_price",
        name="Tomorrow lowest electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_lowest_price_value,
        extra_attrs_fn=_price_extra_attrs,
        entity_registry_enabled_default=False,
        use_tomorrow_data=True,
    ),
    DynamicEnergySensorDescription(
        key="tomorrow_highest_electricity_price",
        translation_key="tomorrow_highest_electricity_price",
        name="Tomorrow highest electricity price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_highest_price_value,
        extra_attrs_fn=_price_extra_attrs,
        entity_registry_enabled_default=False,
        use_tomorrow_data=True,
    ),
)

TOMORROW_GAS_SENSORS: tuple[DynamicEnergySensorDescription, ...] = (
    DynamicEnergySensorDescription(
        key="tomorrow_average_gas_price",
        translation_key="tomorrow_average_gas_price",
        name="Tomorrow average gas price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_average_price_value,
        extra_attrs_fn=_price_extra_attrs,
        available_fn=_gas_available,
        energy_type="gas",
        use_tomorrow_data=True,
    ),
    DynamicEnergySensorDescription(
        key="tomorrow_lowest_gas_price",
        translation_key="tomorrow_lowest_gas_price",
        name="Tomorrow lowest gas price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_lowest_price_value,
        extra_attrs_fn=_price_extra_attrs,
        available_fn=_gas_available,
        entity_registry_enabled_default=False,
        energy_type="gas",
        use_tomorrow_data=True,
    ),
    DynamicEnergySensorDescription(
        key="tomorrow_highest_gas_price",
        translation_key="tomorrow_highest_gas_price",
        name="Tomorrow highest gas price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_highest_price_value,
        extra_attrs_fn=_price_extra_attrs,
        available_fn=_gas_available,
        entity_registry_enabled_default=False,
        energy_type="gas",
        use_tomorrow_data=True,
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
        energy_type="gas",
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
        energy_type="gas",
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

    for description in CHEAPEST_BLOCK_SENSORS:
        entities.append(
            DynamicPriceSensor(coordinator, description, provider_id, provider_display_name)
        )

    for description in DIAGNOSTIC_SENSORS:
        entities.append(
            DynamicPriceSensor(coordinator, description, provider_id, provider_display_name)
        )

    for description in GAS_SENSORS:
        entities.append(
            DynamicPriceSensor(coordinator, description, provider_id, provider_display_name)
        )

    for description in BREAKDOWN_ELECTRICITY_SENSORS:
        entities.append(
            DynamicPriceSensor(coordinator, description, provider_id, provider_display_name)
        )

    supports_tomorrow = (
        provider_cls is not None
        and provider_cls.async_fetch_prices_for_date
        is not PriceProvider.async_fetch_prices_for_date
    )

    if supports_tomorrow:
        for description in TOMORROW_ELECTRICITY_SENSORS:
            entities.append(
                DynamicPriceSensor(coordinator, description, provider_id, provider_display_name)
            )

        for description in TOMORROW_GAS_SENSORS:
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

    def _get_prices(self) -> ProviderPrices | None:
        """Return the appropriate price data source."""
        if self.entity_description.use_tomorrow_data:
            return self.coordinator.tomorrow_data
        return self.coordinator.data

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if self.entity_description.coordinator_value_fn:
            return None
        if self.entity_description.device_class is None or self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            return None
        prices = self._get_prices()
        if prices is None:
            return None
        if self.entity_description.energy_type == "gas" and prices.gas:
            return prices.gas.unit
        return prices.electricity.unit

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.entity_description.coordinator_value_fn:
            return self.entity_description.coordinator_value_fn(self.coordinator)
        prices = self._get_prices()
        if prices is None:
            return None
        return self.entity_description.value_fn(prices)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        prices = self._get_prices()
        if prices is None:
            return None
        if self.entity_description.extra_attrs_fn:
            return self.entity_description.extra_attrs_fn(prices, self._provider_id)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            _LOGGER.warning(
                "Sensor %s is unavailable: coordinator fetch failed",
                getattr(self, "entity_id", None) or self.name,
            )
            return False
        prices = self._get_prices()
        if prices is None:
            _LOGGER.warning(
                "Sensor %s is unavailable: no price data",
                getattr(self, "entity_id", None) or self.name,
            )
            return False
        if self.entity_description.available_fn:
            available = self.entity_description.available_fn(prices)
            if not available:
                _LOGGER.warning(
                    "Sensor %s is unavailable: availability check failed",
                    getattr(self, "entity_id", None) or self.name,
                )
            return available
        return True

    async def async_force_update(self) -> None:
        """Force refresh price data from the provider."""
        await self.coordinator.async_request_refresh()
