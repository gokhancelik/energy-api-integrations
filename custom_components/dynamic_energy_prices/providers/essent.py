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

    async def async_fetch_prices(self) -> ProviderPrices:
        """Fetch dynamic energy prices from Essent's public API."""
        headers = {
            "Accept": "application/json",
            "x-request-origin": "client",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
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

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> ProviderPrices:
        """Parse the Essent API response into ProviderPrices."""
        try:
            raw_prices = data["prices"]
        except KeyError as err:
            raise ProviderResponseError(
                f"Missing 'prices' field in Essent response: {err}"
            ) from err

        electricity_prices: list[PricePoint] = []
        gas_prices: list[PricePoint] = []
        currency = data.get("currency", "EUR")

        for day_entry in raw_prices:
            electricity_data = day_entry.get("electricity")
            gas_data = day_entry.get("gas")

            if electricity_data:
                unit = electricity_data.get("unitOfMeasurement", "kWh")
                for tariff in electricity_data.get("tariffs", []):
                    try:
                        point = self._parse_tariff(tariff, currency)
                        electricity_prices.append(point)
                    except (KeyError, ValueError) as err:
                        raise ProviderResponseError(
                            f"Failed to parse electricity tariff: {err}"
                        ) from err

            if gas_data:
                unit = gas_data.get("unitOfMeasurement", "m\u00b3")
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
                "Essent response contains no electricity prices"
            )

        electricity_unit = "EUR/kWh"
        gas_unit = "EUR/m\u00b3"

        return ProviderPrices(
            electricity=EnergyPriceSeries(
                prices=electricity_prices,
                unit=electricity_unit,
            ),
            gas=EnergyPriceSeries(
                prices=gas_prices,
                unit=gas_unit,
            ) if gas_prices else None,
        )

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
