"""Coordinator for fetching and caching energy price data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging


import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_PROVIDER,
    CONSECUTIVE_FAILURE_LIMIT,
    DOMAIN,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    ISSUE_ID_PROVIDER_UNREACHABLE,
)
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

        session: aiohttp.ClientSession = aiohttp_client.async_get_clientsession(hass)
        self.provider: PriceProvider = provider_cls(entry.data, session=session)
        self._last_successful_data: ProviderPrices | None = None
        self._tomorrow_data: ProviderPrices | None = None
        self._last_update_time: datetime | None = None
        self._consecutive_failures = 0
        self._hourly_sync_unsub: Callable[[], None] | None = None

        update_interval = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            update_method=self._async_update_data,
        )

        self._schedule_next_hourly_sync()

    async def _async_update_data(self) -> ProviderPrices:
        """Fetch data from the provider with fallback to cached data."""
        try:
            async with asyncio.timeout(15):
                data = await self.provider.async_fetch_prices()
        except ProviderConnectionError as err:
            await self._handle_failure(err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except ProviderResponseError as err:
            await self._handle_failure(err)
            raise UpdateFailed(f"Response error: {err}") from err

        self._consecutive_failures = 0
        await self._clear_issue()
        self._last_successful_data = data
        self._last_update_time = datetime.now(timezone.utc)

        tomorrow_str = (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        try:
            async with asyncio.timeout(15):
                self._tomorrow_data = await self.provider.async_fetch_prices_for_date(
                    tomorrow_str
                )
        except (ProviderConnectionError, ProviderResponseError):
            self._tomorrow_data = None

        return data

    async def _handle_failure(self, err: Exception) -> None:
        """Handle a fetch failure and raise a repair issue if threshold exceeded."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
            issues = getattr(self.hass, "issues", None)
            if issues is not None:
                translation_placeholders = {
                    "provider": self.provider.display_name,
                    "error": str(err),
                }
                issues.async_create_issue(
                    DOMAIN,
                    ISSUE_ID_PROVIDER_UNREACHABLE,
                    is_fixable=False,
                    severity="error",
                    translation_key="provider_unreachable",
                    translation_placeholders=translation_placeholders,
                )

    async def _clear_issue(self) -> None:
        """Clear the repair issue if one was raised."""
        issues = getattr(self.hass, "issues", None)
        if issues is not None:
            issues.async_delete_issue(DOMAIN, ISSUE_ID_PROVIDER_UNREACHABLE)

    @property
    def last_successful_data(self) -> ProviderPrices | None:
        """Return the last successfully fetched data."""
        return self._last_successful_data

    @property
    def tomorrow_data(self) -> ProviderPrices | None:
        """Return tomorrow's price data, if available."""
        return self._tomorrow_data

    @property
    def last_update_time(self) -> datetime | None:
        """Return the timestamp of the last successful update."""
        return self._last_update_time

    @callback
    def _schedule_next_hourly_sync(self) -> None:
        """Schedule a listener update at the next local hour boundary."""
        now = datetime.now().astimezone()
        next_hour = (now + timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
        self._hourly_sync_unsub = async_track_point_in_time(
            self.hass, self._on_hourly_sync, next_hour
        )

    @callback
    def _on_hourly_sync(self, _: datetime) -> None:
        """Fire listener updates at the hour boundary."""
        self.async_update_listeners()
        self._schedule_next_hourly_sync()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and cancel hourly sync."""
        if self._hourly_sync_unsub is not None:
            self._hourly_sync_unsub()
            self._hourly_sync_unsub = None
