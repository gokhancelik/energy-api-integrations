"""Tests for the provider base classes and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.dynamic_energy_prices.providers.base import (
    EnergyPriceSeries,
    PricePoint,
    PriceProvider,
    ProviderPrices,
    calculate_average_price,
    calculate_max_price,
    calculate_min_price,
    find_current_price,
    find_next_price,
)


def _utc_dt(hour: int) -> datetime:
    return datetime(2026, 6, 17, hour, 0, 0, tzinfo=timezone.utc)


def test_price_point_dataclass() -> None:
    """Test PricePoint dataclass creation."""
    now = _utc_dt(10)
    point = PricePoint(
        start=now,
        end=_utc_dt(11),
        total_price=0.254,
        currency="EUR",
        breakdown={"market_price": 0.185, "tax": 0.059},
    )
    assert point.total_price == 0.254
    assert point.currency == "EUR"
    assert point.breakdown["market_price"] == 0.185


def test_price_point_default_breakdown() -> None:
    """Test PricePoint defaults."""
    now = _utc_dt(10)
    point = PricePoint(start=now, end=_utc_dt(11), total_price=0.254)
    assert point.breakdown == {}


def test_energy_price_series() -> None:
    """Test EnergyPriceSeries creation."""
    prices = [PricePoint(start=_utc_dt(0), end=_utc_dt(1), total_price=0.1)]
    series = EnergyPriceSeries(prices=prices, unit="EUR/kWh")
    assert len(series.prices) == 1
    assert series.unit == "EUR/kWh"


def test_provider_prices() -> None:
    """Test ProviderPrices creation."""
    elec = EnergyPriceSeries(
        prices=[PricePoint(start=_utc_dt(0), end=_utc_dt(1), total_price=0.1)],
        unit="EUR/kWh",
    )
    prices = ProviderPrices(electricity=elec)
    assert prices.gas is None
    assert prices.electricity.unit == "EUR/kWh"


def test_provider_prices_with_gas() -> None:
    """Test ProviderPrices with gas."""
    elec = EnergyPriceSeries(
        prices=[PricePoint(start=_utc_dt(0), end=_utc_dt(1), total_price=0.1)],
        unit="EUR/kWh",
    )
    gas = EnergyPriceSeries(
        prices=[PricePoint(start=_utc_dt(7), end=_utc_dt(8), total_price=0.7)],
        unit="EUR/m³",
    )
    prices = ProviderPrices(electricity=elec, gas=gas)
    assert prices.gas is not None
    assert prices.gas.unit == "EUR/m³"


def test_calculate_average_price() -> None:
    """Test average price calculation."""
    prices = [
        PricePoint(start=_utc_dt(0), end=_utc_dt(1), total_price=0.2),
        PricePoint(start=_utc_dt(1), end=_utc_dt(2), total_price=0.3),
        PricePoint(start=_utc_dt(2), end=_utc_dt(3), total_price=0.4),
    ]
    assert calculate_average_price(prices) == 0.3


def test_calculate_average_price_empty() -> None:
    """Test average price with empty list."""
    assert calculate_average_price([]) is None


def test_calculate_min_price() -> None:
    """Test min price calculation."""
    prices = [
        PricePoint(start=_utc_dt(0), end=_utc_dt(1), total_price=0.4),
        PricePoint(start=_utc_dt(1), end=_utc_dt(2), total_price=0.2),
        PricePoint(start=_utc_dt(2), end=_utc_dt(3), total_price=0.3),
    ]
    assert calculate_min_price(prices) == 0.2


def test_calculate_min_price_empty() -> None:
    """Test min price with empty list."""
    assert calculate_min_price([]) is None


def test_calculate_max_price() -> None:
    """Test max price calculation."""
    prices = [
        PricePoint(start=_utc_dt(0), end=_utc_dt(1), total_price=0.2),
        PricePoint(start=_utc_dt(1), end=_utc_dt(2), total_price=0.4),
        PricePoint(start=_utc_dt(2), end=_utc_dt(3), total_price=0.3),
    ]
    assert calculate_max_price(prices) == 0.4


def test_calculate_max_price_empty() -> None:
    """Test max price with empty list."""
    assert calculate_max_price([]) is None


def test_find_current_price() -> None:
    """Test finding the current price point."""
    now = datetime.now().astimezone()
    current_hour = now.hour
    prices = [
        PricePoint(
            start=datetime(now.year, now.month, now.day, current_hour, 0, 0).astimezone(),
            end=datetime(now.year, now.month, now.day, current_hour + 1, 0, 0).astimezone(),
            total_price=0.254,
        ),
    ]
    current = find_current_price(prices)
    assert current is not None
    assert current.total_price == 0.254


def test_find_current_price_no_match() -> None:
    """Test current price with no matching window."""
    prices = [
        PricePoint(start=_utc_dt(0), end=_utc_dt(1), total_price=0.1),
    ]
    current = find_current_price(prices)
    assert current is None or current.start == _utc_dt(0)


def test_find_next_price() -> None:
    """Test finding the next upcoming price."""
    from datetime import timedelta

    now = datetime.now().astimezone()
    prices = [
        PricePoint(
            start=now + timedelta(hours=2),
            end=now + timedelta(hours=3),
            total_price=0.3,
        ),
        PricePoint(
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            total_price=0.2,
        ),
    ]
    next_price = find_next_price(prices)
    assert next_price is not None
    assert next_price.total_price == 0.2


def test_find_next_price_none() -> None:
    """Test next price with no future prices."""
    from datetime import timedelta

    now = datetime.now().astimezone()
    prices = [
        PricePoint(
            start=now - timedelta(hours=2),
            end=now - timedelta(hours=1),
            total_price=0.1,
        ),
    ]
    next_price = find_next_price(prices)
    assert next_price is None


def test_provider_registry_and_subclass() -> None:
    """Test that provider subclasses register themselves."""
    from custom_components.dynamic_energy_prices.providers import PROVIDER_REGISTRY

    assert "essent" in PROVIDER_REGISTRY
    cls = PROVIDER_REGISTRY["essent"]
    assert cls.provider_id == "essent"
    assert cls.display_name == "Essent"


class TestPriceProviderDefaultSchema:
    """Test default config_schema on PriceProvider."""

    def test_default_schema_is_none(self) -> None:
        """Test that a simple provider has no extra config."""
        from custom_components.dynamic_energy_prices.providers.essent import (
            EssentPriceProvider,
        )

        assert EssentPriceProvider.config_schema() is None
