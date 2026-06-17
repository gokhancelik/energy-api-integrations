"""Frank Energie dynamic energy price provider."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiohttp

from .base import (
    EnergyPriceSeries,
    PricePoint,
    PriceProvider,
    ProviderConnectionError,
    ProviderPrices,
    ProviderResponseError,
)

API_ENDPOINT = "https://graphql.frankenergie.nl/"
REQUEST_TIMEOUT = 10

MARKET_PRICES_QUERY = """
query MarketPrices($date: String!) {
  marketPrices(date: $date) {
    electricityPrices {
      from
      till
      marketPrice
      marketPriceTax
      sourcingMarkupPrice
      energyTaxPrice
      perUnit
    }
    gasPrices {
      from
      till
      marketPrice
      marketPriceTax
      sourcingMarkupPrice
      energyTaxPrice
      perUnit
    }
  }
}
"""


class FrankEnergiePriceProvider(PriceProvider):
    """Provider for Frank Energie dynamic energy prices."""

    provider_id = "frank_energie"
    display_name = "Frank Energie"

    async def async_fetch_prices(self) -> ProviderPrices:
        """Fetch dynamic energy prices from Frank Energie's public GraphQL API."""
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        payload = {
            "query": MARKET_PRICES_QUERY,
            "variables": {"date": today_str},
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    API_ENDPOINT, json=payload, headers=headers
                ) as response:
                    if response.status != 200:
                        raise ProviderConnectionError(
                            f"Frank Energie API returned HTTP {response.status}"
                        )
                    data: dict[str, Any] = await response.json()
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(
                f"Failed to connect to Frank Energie API: {err}"
            ) from err
        except ValueError as err:
            raise ProviderResponseError(
                f"Invalid JSON from Frank Energie API: {err}"
            ) from err

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> ProviderPrices:
        """Parse the Frank Energie GraphQL response into ProviderPrices."""
        graphql_errors = data.get("errors")
        if graphql_errors:
            raise ProviderResponseError(
                f"Frank Energie GraphQL error: {graphql_errors}"
            )

        market_prices = data.get("data", {}).get("marketPrices")
        if not isinstance(market_prices, dict):
            raise ProviderResponseError(
                "Frank Energie response missing 'marketPrices'"
            )

        electricity_prices = self._parse_prices(
            market_prices.get("electricityPrices", [])
        )
        gas_prices = self._parse_prices(
            market_prices.get("gasPrices", [])
        )

        electricity_prices.sort(key=lambda p: p.start)
        gas_prices.sort(key=lambda p: p.start)

        if not electricity_prices:
            raise ProviderResponseError(
                "Frank Energie response contains no electricity prices"
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

    def _parse_prices(
        self, raw_prices: list[dict[str, Any]]
    ) -> list[PricePoint]:
        """Parse a list of Frank Energie price entries into PricePoints."""
        prices: list[PricePoint] = []

        for entry in raw_prices:
            from_str = entry.get("from")
            till_str = entry.get("till")
            per_unit = entry.get("perUnit")

            if not from_str or not till_str or per_unit is None:
                continue

            start = datetime.fromisoformat(
                from_str.replace("Z", "+00:00")
            )
            end = datetime.fromisoformat(
                till_str.replace("Z", "+00:00")
            )

            breakdown = {}
            if "marketPrice" in entry:
                breakdown["market_price"] = float(entry["marketPrice"])
            if "marketPriceTax" in entry:
                breakdown["market_price_tax"] = float(entry["marketPriceTax"])
            if "sourcingMarkupPrice" in entry:
                breakdown["sourcing_markup_price"] = float(
                    entry["sourcingMarkupPrice"]
                )
            if "energyTaxPrice" in entry:
                breakdown["energy_tax_price"] = float(entry["energyTaxPrice"])

            prices.append(
                PricePoint(
                    start=start,
                    end=end,
                    total_price=float(per_unit),
                    currency="EUR",
                    breakdown=breakdown,
                )
            )

        return prices
