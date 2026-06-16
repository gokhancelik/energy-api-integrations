"""Coordinator for fetching and caching energy price data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from random import randrange

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_PROVIDER, DOMAIN, DEFAULT_SCAN_INTERVAL_MINUTES
from .providers import (
    PROVIDER_REGISTRY,
    PriceProvider,
    ProviderConnectionError,
    ProviderPrices,
    ProviderResponseError,
)

_LOGGER = logging.getLogger(__name__)


class DynamicPriceCoordinator(DataUpdateCoordinator[ProviderPrices]):
    """Coordinator for dynamic energy price data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        provider_id = entry.data[CONF_PROVIDER]
        provider_cls = PROVIDER_REGISTRY.get(provider_id)

        if provider_cls is None:
            raise ValueError(f"Unknown provider: {provider_id}")

        self.provider: PriceProvider = provider_cls()
        self._last_successful_data: ProviderPrices | None = None

        randomized_minute = randrange(0, 60)
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(
            minute=randomized_minute, second=0, microsecond=0
        )
        if next_hour <= now:
            next_hour += timedelta(hours=1)

        update_interval = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            update_method=self._async_update_data,
        )

    async def _async_update_data(self) -> ProviderPrices:
        """Fetch data from the provider with fallback to cached data."""
        try:
            async with asyncio.timeout(15):
                data = await self.provider.async_fetch_prices()
        except ProviderConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except ProviderResponseError as err:
            raise UpdateFailed(f"Response error: {err}") from err

        self._last_successful_data = data
        return data

    @property
    def last_successful_data(self) -> ProviderPrices | None:
        """Return the last successfully fetched data."""
        return self._last_successful_data
