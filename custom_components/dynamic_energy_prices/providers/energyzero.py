"""EnergyZero dynamic energy price provider."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiohttp
from zoneinfo import ZoneInfo

from .base import (
    EnergyPriceSeries,
    PricePoint,
    PriceProvider,
    ProviderConnectionError,
    ProviderPrices,
    ProviderResponseError,
)

API_ENDPOINT = "https://api.energyzero.nl/v1/energyprices"
REQUEST_TIMEOUT = 10
AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")


class EnergyZeroPriceProvider(PriceProvider):
    """Provider for EnergyZero (and white-label resellers) dynamic energy prices."""

    provider_id = "energyzero"
    display_name = "EnergyZero"

    @staticmethod
    def _date_range_from_date(
        date_str: str,
    ) -> tuple[str, str]:
        """Convert a YYYY-MM-DD date to EnergyZero fromDate/tillDate strings."""
        date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=AMSTERDAM_TZ)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        from_date = day_start.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        till_date = day_end.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.999Z"
        )
        return from_date, till_date

    @staticmethod
    def _today_date_range() -> tuple[str, str]:
        """Get the fromDate/tillDate for today."""
        now_local = datetime.now(AMSTERDAM_TZ)
        today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now_local.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        from_date = today_start.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        till_date = today_end.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.999Z"
        )
        return from_date, till_date

    async def async_fetch_prices(self) -> ProviderPrices:
        """Fetch dynamic energy prices from the EnergyZero public API."""
        from_date, till_date = self._today_date_range()

        session = self._session
        own_session = False
        if session is None:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            session = aiohttp.ClientSession(timeout=timeout)
            own_session = True

        try:
            electricity_data = await self._fetch_type(
                session, from_date, till_date, usage_type=1
            )
            gas_data = await self._fetch_type(
                session, from_date, till_date, usage_type=3
            )
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(
                f"Failed to connect to EnergyZero API: {err}"
            ) from err
        finally:
            if own_session:
                await session.close()

        return self._parse_response(electricity_data, gas_data)

    async def async_fetch_prices_for_date(self, date: str) -> ProviderPrices | None:
        """Fetch prices for a specific date (YYYY-MM-DD)."""
        from_date, till_date = self._date_range_from_date(date)

        session = self._session
        own_session = False
        if session is None:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            session = aiohttp.ClientSession(timeout=timeout)
            own_session = True

        try:
            electricity_data = await self._fetch_type(
                session, from_date, till_date, usage_type=1
            )
            gas_data = await self._fetch_type(
                session, from_date, till_date, usage_type=3
            )
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(
                f"Failed to connect to EnergyZero API: {err}"
            ) from err
        finally:
            if own_session:
                await session.close()

        return self._parse_response(electricity_data, gas_data)

    async def _fetch_type(
        self,
        session: aiohttp.ClientSession,
        from_date: str,
        till_date: str,
        usage_type: int,
    ) -> dict:
        """Fetch prices for a specific energy type."""
        params = {
            "fromDate": from_date,
            "tillDate": till_date,
            "interval": "4",
            "usageType": str(usage_type),
            "inclBtw": "true",
        }

        async with session.get(API_ENDPOINT, params=params) as response:
            if response.status != 200:
                raise ProviderConnectionError(
                    f"EnergyZero API returned HTTP {response.status} "
                    f"for usageType={usage_type}"
                )
            data = await response.json()

        if not isinstance(data, dict):
            raise ProviderResponseError(
                f"EnergyZero returned non-dict response for usageType={usage_type}"
            )

        return data

    def _parse_response(
        self,
        electricity_data: dict,
        gas_data: dict,
    ) -> ProviderPrices:
        """Parse EnergyZero API responses into ProviderPrices."""
        electricity_prices = self._parse_prices(electricity_data)
        gas_prices = self._parse_prices(gas_data)

        if not electricity_prices:
            raise ProviderResponseError(
                "EnergyZero response contains no electricity prices"
            )

        return ProviderPrices(
            electricity=EnergyPriceSeries(
                prices=electricity_prices,
                unit="EUR/kWh",
            ),
            gas=EnergyPriceSeries(
                prices=gas_prices,
                unit="EUR/m\u00b3",
            ) if gas_prices else None,
        )

    def _parse_prices(self, data: dict) -> list[PricePoint]:
        """Parse a list of prices from an EnergyZero response."""
        raw_prices = data.get("Prices", [])
        prices: list[PricePoint] = []

        for entry in raw_prices:
            reading_date_str = entry.get("readingDate")
            price = entry.get("price")

            if reading_date_str is None or price is None:
                continue

            reading_date = datetime.fromisoformat(
                reading_date_str.replace("Z", "+00:00")
            )

            start = reading_date
            end = start + timedelta(hours=1)

            prices.append(
                PricePoint(
                    start=start,
                    end=end,
                    total_price=float(price),
                    currency="EUR",
                )
            )

        return prices
