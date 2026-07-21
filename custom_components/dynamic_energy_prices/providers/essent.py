"""Essent dynamic energy price provider."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import aiohttp
from zoneinfo import ZoneInfo

from .base import (
    BREAKDOWN_MARKET_PRICE,
    BREAKDOWN_SUPPLIER_MARKUP,
    BREAKDOWN_ENERGY_TAX,
    EnergyPriceSeries,
    PricePoint,
    PriceProvider,
    ProviderConnectionError,
    ProviderPrices,
    ProviderResponseError,
)

API_ENDPOINT = "https://www.essent.nl/api/public/dynamicpricing/dynamic-prices/v1"
REQUEST_TIMEOUT = 10
AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")

GROUP_TYPE_MAP = {
    "MARKET_PRICE": BREAKDOWN_MARKET_PRICE,
    "PURCHASING_FEE": BREAKDOWN_SUPPLIER_MARKUP,
    "TAX": BREAKDOWN_ENERGY_TAX,
}


class EssentPriceProvider(PriceProvider):
    """Provider for Essent dynamic energy prices."""

    provider_id = "essent"
    display_name = "Essent"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the provider."""
        super().__init__(config, session)
        self._cached_days: dict[str, ProviderPrices] = {}

    async def async_fetch_prices(self) -> ProviderPrices:
        """Fetch dynamic energy prices from Essent's public API."""
        headers = {
            "Accept": "application/json",
            "x-request-origin": "client",
        }

        session = self._session
        own_session = False
        if session is None:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            session = aiohttp.ClientSession(timeout=timeout)
            own_session = True

        try:
            async with session.get(API_ENDPOINT, headers=headers) as response:
                if response.status == 401:
                    raise ProviderConnectionError(
                        "Essent API returned 401 Unauthorized. "
                        "The x-request-origin header may need updating."
                    )
                if response.status != 200:
                    raise ProviderConnectionError(
                        f"Essent API returned HTTP {response.status}"
                    )
                data: dict[str, Any] = await response.json()
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(
                f"Failed to connect to Essent API: {err}"
            ) from err
        except ValueError as err:
            raise ProviderResponseError(
                f"Invalid JSON from Essent API: {err}"
            ) from err
        finally:
            if own_session:
                await session.close()

        self._cached_days = self._parse_response(data)

        today_str = datetime.now(AMSTERDAM_TZ).strftime("%Y-%m-%d")
        today_prices = self._cached_days.get(today_str)
        if today_prices is not None:
            return today_prices
        return next(iter(self._cached_days.values()))

    def _parse_response(self, data: dict[str, Any]) -> dict[str, ProviderPrices]:
        """Parse Essent API response into per-date ProviderPrices."""
        try:
            raw_prices = data["prices"]
        except KeyError as err:
            raise ProviderResponseError(
                f"Missing 'prices' field in Essent response: {err}"
            ) from err

        currency = data.get("currency", "EUR")
        result: dict[str, ProviderPrices] = {}

        for day_entry in raw_prices:
            date_str = day_entry.get("date")
            if not date_str:
                continue

            electricity_data = day_entry.get("electricity")
            gas_data = day_entry.get("gas")
            electricity_prices: list[PricePoint] = []
            gas_prices: list[PricePoint] = []

            if electricity_data:
                for tariff in electricity_data.get("tariffs", []):
                    try:
                        point = self._parse_tariff(tariff, currency)
                        electricity_prices.append(point)
                    except (KeyError, ValueError) as err:
                        raise ProviderResponseError(
                            f"Failed to parse electricity tariff: {err}"
                        ) from err

            if gas_data:
                for tariff in gas_data.get("tariffs", []):
                    try:
                        point = self._parse_tariff(tariff, currency)
                        gas_prices.append(point)
                    except (KeyError, ValueError) as err:
                        raise ProviderResponseError(
                            f"Failed to parse gas tariff: {err}"
                        ) from err

            if not electricity_prices:
                raise ProviderResponseError(
                    f"Essent response contains no electricity prices for {date_str}"
                )

            result[date_str] = ProviderPrices(
                electricity=EnergyPriceSeries(
                    prices=electricity_prices,
                    unit="EUR/kWh",
                ),
                gas=EnergyPriceSeries(
                    prices=gas_prices,
                    unit="EUR/m\u00b3",
                ) if gas_prices else None,
            )

        if not result:
            raise ProviderResponseError(
                "Essent response contains no price data"
            )

        return result

    async def async_fetch_prices_for_date(
        self, date: str
    ) -> ProviderPrices | None:
        """Return cached prices for a specific date (YYYY-MM-DD)."""
        return self._cached_days.get(date)

    def _parse_tariff(
        self, tariff: dict[str, Any], currency: str
    ) -> PricePoint:
        """Parse a single tariff entry into a PricePoint."""
        start = datetime.fromisoformat(tariff["startDateTime"]).replace(
            tzinfo=AMSTERDAM_TZ
        )
        end = datetime.fromisoformat(tariff["endDateTime"]).replace(
            tzinfo=AMSTERDAM_TZ
        )

        total_price: float = tariff["totalAmount"]

        breakdown: dict[str, float] = {}
        for group in tariff.get("groups", []):
            group_type = group.get("type", "")
            mapped_key = GROUP_TYPE_MAP.get(group_type, group_type.lower())
            breakdown[mapped_key] = group.get("amount", 0.0)

        return PricePoint(
            start=start,
            end=end,
            total_price=total_price,
            currency=currency,
            breakdown=breakdown,
        )
