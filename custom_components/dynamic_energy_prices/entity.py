"""Base entity for Dynamic Energy Prices."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DynamicPriceCoordinator


class DynamicPriceEntity(CoordinatorEntity[DynamicPriceCoordinator]):
    """Base entity for dynamic energy prices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DynamicPriceCoordinator,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.entry.entry_id}_{self.entity_description.key}"
        )
