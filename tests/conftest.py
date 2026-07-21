"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import sys
from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_homeassistant() -> None:
    """Mock the homeassistant module to allow imports without full HA installation.

    Only mocks when pytest-homeassistant-custom-component is not installed,
    so CI with real HA fixtures works properly.
    """
    try:
        import pytest_homeassistant_custom_component  # noqa: F401
        return  # real HA fixtures available, skip mocking
    except ImportError:
        pass

    if "homeassistant" not in sys.modules:
        from dataclasses import dataclass

        ha_mock = MagicMock()
        ha_mock.config_entries = MagicMock()
        ha_mock.const = MagicMock()
        ha_mock.core = MagicMock()
        ha_mock.helpers = MagicMock()
        ha_mock.helpers.update_coordinator = MagicMock()
        ha_mock.helpers.entity_platform = MagicMock()
        ha_mock.helpers.event = MagicMock()
        ha_mock.data_entry_flow = MagicMock()
        sys.modules["homeassistant"] = ha_mock
        sys.modules["homeassistant.config_entries"] = ha_mock.config_entries
        sys.modules["homeassistant.const"] = ha_mock.const
        sys.modules["homeassistant.core"] = ha_mock.core
        sys.modules["homeassistant.helpers"] = ha_mock.helpers
        sys.modules["homeassistant.helpers.update_coordinator"] = (
            ha_mock.helpers.update_coordinator
        )
        sys.modules["homeassistant.helpers.entity_platform"] = (
            ha_mock.helpers.entity_platform
        )
        sys.modules["homeassistant.data_entry_flow"] = ha_mock.data_entry_flow
        sys.modules["homeassistant.helpers.event"] = ha_mock.helpers.event
        sys.modules["homeassistant.components"] = MagicMock()

        # Provide real dataclass bases so DynamicEnergySensorDescription can inherit
        class SensorDeviceClass:
            MONETARY = "monetary"
            TIMESTAMP = "timestamp"

        class SensorStateClass:
            MEASUREMENT = "measurement"

        @dataclass(frozen=True, kw_only=True)
        class SensorEntityDescription:
            key: str = ""
            name: str = ""
            translation_key: str | None = None
            device_class: str | None = None
            state_class: str | None = None
            entity_registry_enabled_default: bool = True
            entity_category: Any = None

        class SensorEntity:
            pass

        sensor_module = MagicMock()
        sensor_module.SensorDeviceClass = SensorDeviceClass
        sensor_module.SensorStateClass = SensorStateClass
        sensor_module.SensorEntityDescription = SensorEntityDescription
        sensor_module.SensorEntity = SensorEntity
        sys.modules["homeassistant.components.sensor"] = sensor_module

        class BinarySensorEntity:
            pass

        class BinarySensorEntityDescription:
            def __init__(self, **kwargs: Any) -> None:
                for k, v in kwargs.items():
                    setattr(self, k, v)

        binary_sensor_module = MagicMock()
        binary_sensor_module.BinarySensorEntity = BinarySensorEntity
        binary_sensor_module.BinarySensorEntityDescription = BinarySensorEntityDescription
        sys.modules["homeassistant.components.binary_sensor"] = binary_sensor_module

        # Provide real base classes for entity hierarchy (no metaclass conflicts)
        class CoordinatorEntity:
            def __init__(self, coordinator=None):
                self.coordinator = coordinator
                self._attr_unique_id = ""
                self._attr_has_entity_name = True

            def __class_getitem__(cls, item):  # type: ignore[misc]
                return cls

            @property
            def available(self) -> bool:
                return True

        class UpdateFailed(Exception):
            pass

        class MockDataUpdateCoordinator:
            def __init__(self, hass, logger, **kwargs: Any):
                self.hass = hass
                self.logger = logger
                self.data = None

            def __class_getitem__(cls, item):  # type: ignore[misc]
                return cls

            @property
            def available(self) -> bool:
                return True

        ha_mock.helpers.update_coordinator.UpdateFailed = UpdateFailed

        class ConfigEntry:
            entry_id: str = "test_entry"

        ha_mock.helpers.update_coordinator.CoordinatorEntity = CoordinatorEntity
        ha_mock.helpers.update_coordinator.DataUpdateCoordinator = MockDataUpdateCoordinator
        ha_mock.config_entries.ConfigEntry = ConfigEntry
        sys.modules["homeassistant.helpers.device_registry"] = MagicMock()
        sys.modules["homeassistant.helpers.typing"] = MagicMock()
        sys.modules["homeassistant.loader"] = MagicMock()


_mock_homeassistant()

_HAS_HA_FIXTURES: bool
try:
    import pytest_homeassistant_custom_component  # noqa: F401
    _HAS_HA_FIXTURES = True
except ImportError:
    _HAS_HA_FIXTURES = False


if _HAS_HA_FIXTURES:

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(  # type: ignore[misc]
        enable_custom_integrations,  # type: ignore[name-defined]
    ) -> None:
        """Enable custom component discovery for HA test fixtures."""
else:

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations() -> None:
        """No-op when pytest-homeassistant-custom-component is not installed."""

    @pytest.fixture
    def hass() -> MagicMock:
        """Provide a mock hass when pytest-homeassistant-custom-component is not available."""
        return MagicMock()


MOCK_ESSENT_RESPONSE: dict[str, Any] = {
    "prices": [
        {
            "date": "2026-06-17",
            "electricity": {
                "energyType": "electricity",
                "unitOfMeasurement": "kWh",
                "vatPercentage": 21,
                "tariffs": [
                    {
                        "startDateTime": "2026-06-17T00:00:00",
                        "endDateTime": "2026-06-17T01:00:00",
                        "totalAmount": 0.254,
                        "totalAmountEx": 0.20992,
                        "totalAmountVat": 0.04408,
                        "groups": [
                            {
                                "description": "Beursprijs",
                                "type": "MARKET_PRICE",
                                "amount": 0.185,
                                "amountEx": 0.15289,
                            },
                            {
                                "description": "Inkoopvergoeding",
                                "type": "PURCHASING_FEE",
                                "amount": 0.010,
                                "amountEx": 0.00826,
                            },
                            {
                                "description": "Energiebelasting",
                                "type": "TAX",
                                "amount": 0.059,
                                "amountEx": 0.04876,
                            },
                        ],
                    },
                    {
                        "startDateTime": "2026-06-17T01:00:00",
                        "endDateTime": "2026-06-17T02:00:00",
                        "totalAmount": 0.231,
                        "totalAmountEx": 0.19091,
                        "totalAmountVat": 0.04009,
                        "groups": [
                            {
                                "description": "Beursprijs",
                                "type": "MARKET_PRICE",
                                "amount": 0.162,
                                "amountEx": 0.13388,
                            },
                            {
                                "description": "Inkoopvergoeding",
                                "type": "PURCHASING_FEE",
                                "amount": 0.010,
                                "amountEx": 0.00826,
                            },
                            {
                                "description": "Energiebelasting",
                                "type": "TAX",
                                "amount": 0.059,
                                "amountEx": 0.04876,
                            },
                        ],
                    },
                ],
            },
            "gas": {
                "energyType": "gas",
                "unitOfMeasurement": "m\u00b3",
                "vatPercentage": 21,
                "tariffs": [
                    {
                        "startDateTime": "2026-06-17T07:00:00",
                        "endDateTime": "2026-06-17T08:00:00",
                        "totalAmount": 0.789,
                        "totalAmountEx": 0.65207,
                        "totalAmountVat": 0.13693,
                        "groups": [
                            {
                                "description": "Beursprijs",
                                "type": "MARKET_PRICE",
                                "amount": 0.720,
                                "amountEx": 0.59504,
                            },
                            {
                                "description": "Inkoopvergoeding",
                                "type": "PURCHASING_FEE",
                                "amount": 0.07872,
                                "amountEx": 0.06506,
                            },
                            {
                                "description": "Energiebelasting",
                                "type": "TAX",
                                "amount": 0.7268,
                                "amountEx": 0.60066,
                            },
                        ],
                    },
                ],
            },
        },
    ],
    "currency": "EUR",
}


from custom_components.dynamic_energy_prices.providers import (  # noqa: E402
    EnergyPriceSeries,
    PricePoint,
    ProviderPrices,
)


def _make_pricepoint(
    hour: int,
    total_price: float,
    energy_type: str = "ELECTRICITY",
) -> Any:
    """Create a mock PricePoint with the given parameters."""
    from datetime import timedelta
    today = datetime.now().astimezone()
    start = today.replace(hour=hour, minute=0, second=0, microsecond=0)
    end = today.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return PricePoint(
        start=start,
        end=end,
        total_price=total_price,
        currency="EUR",
        breakdown={
            "market_price": total_price - 0.069,
            "purchasing_fee": 0.010,
            "tax": 0.059,
        },
    )


MOCK_ELECTRICITY_PRICES = [
    _make_pricepoint(h, p)
    for h, p in enumerate([0.250, 0.231, 0.220, 0.210, 0.200, 0.198, 0.205, 0.215,
                           0.230, 0.250, 0.280, 0.320, 0.350, 0.370, 0.380, 0.390,
                           0.400, 0.390, 0.370, 0.340, 0.310, 0.290, 0.270, 0.255])
]

MOCK_GAS_PRICES = [
    _make_pricepoint(h, p, energy_type="GAS")
    for h, p in enumerate([0.720, 0.710, 0.700, 0.690, 0.680, 0.670, 0.660, 0.650,
                           0.640, 0.630, 0.620, 0.610, 0.600, 0.590, 0.580, 0.570,
                           0.560, 0.550, 0.540, 0.530, 0.520, 0.510, 0.500, 0.490])
]

@pytest.fixture
def mock_provider_prices() -> ProviderPrices:
    return ProviderPrices(
        electricity=EnergyPriceSeries(unit="EUR/kWh", prices=MOCK_ELECTRICITY_PRICES),
        gas=EnergyPriceSeries(unit="EUR/m³", prices=MOCK_GAS_PRICES),
    )


@pytest.fixture
def mock_provider_prices_electricity_only() -> ProviderPrices:
    return ProviderPrices(
        electricity=EnergyPriceSeries(unit="EUR/kWh", prices=MOCK_ELECTRICITY_PRICES),
        gas=None,
    )


@pytest.fixture
def mock_aiohttp_session() -> Generator[MagicMock, None, None]:
    """Mock aiohttp.ClientSession entirely to prevent cleanup thread creation.

    Patches the whole class, so the constructor never runs and no daemon
    thread is spawned. Works for both ``.get`` and ``.post`` calls, and
    supports both ``async with ClientSession() as session`` and direct
    ``session = ClientSession()`` patterns.
    """
    mock_session = MagicMock()
    mock_session.get = MagicMock()
    mock_session.post = MagicMock()
    mock_session.close = AsyncMock()

    with patch("aiohttp.ClientSession") as mock_cls:
        mock_cls.return_value = mock_session
        mock_cls.return_value.__aenter__.return_value = mock_session
        yield mock_session


def mock_http_response(
    status: int = 200,
    json_data: dict | None = None,
) -> AsyncMock:
    """Create a mock aiohttp response with ``__aenter__`` support."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.__aenter__.return_value = resp
    resp.__aexit__.return_value = None
    return resp
