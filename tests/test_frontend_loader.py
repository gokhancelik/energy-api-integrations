"""Tests for the bundled Lovelace card registration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from custom_components.dynamic_energy_prices import frontend_loader as fl


class FakeHttp:
    def __init__(self) -> None:
        self.registered: list[object] = []

    async def async_register_static_paths(self, configs: list[object]) -> None:
        self.registered.extend(configs)


class FakeStaticPathConfig:
    def __init__(self, url_path: str, path: str, cache_headers: bool) -> None:
        self.url_path = url_path
        self.path = path
        self.cache_headers = cache_headers


class FakeFrontend:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def add_extra_js_url(self, hass: object, url: str) -> None:
        self.urls.append(url)


def test_card_version_has_semver_shape() -> None:
    parts = fl._card_version().split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_is_card_registered() -> None:
    hass = SimpleNamespace(data={})
    assert fl.is_card_registered(hass) is False
    hass.data[fl._REGISTERED_KEY] = True
    assert fl.is_card_registered(hass) is True


def test_is_card_registered_handles_missing_data() -> None:
    hass = SimpleNamespace(data=None)
    assert fl.is_card_registered(hass) is False


async def test_register_serves_card_and_adds_js_url() -> None:
    http = FakeHttp()
    frontend = FakeFrontend()
    hass = SimpleNamespace(data={}, http=http)

    def fake_api() -> tuple[FakeFrontend, type[FakeStaticPathConfig]]:
        return frontend, FakeStaticPathConfig

    with patch.object(fl, "_frontend_api", fake_api):
        await fl.async_register_frontend(hass)

    assert fl.is_card_registered(hass) is True
    assert len(http.registered) == 1
    config = http.registered[0]
    assert config.url_path == fl.CARD_URL_PATH
    assert config.cache_headers is True
    assert str(config.path).endswith("frontend")
    assert len(frontend.urls) == 1
    assert frontend.urls[0].startswith(fl.CARD_URL)
    assert "?v=" in frontend.urls[0]


async def test_register_skips_without_http() -> None:
    hass = SimpleNamespace(data={}, http=None)
    await fl.async_register_frontend(hass)
    assert fl.is_card_registered(hass) is False


async def test_register_skips_when_already_registered() -> None:
    http = FakeHttp()
    hass = SimpleNamespace(data={fl._REGISTERED_KEY: True}, http=http)

    await fl.async_register_frontend(hass)

    assert http.registered == []
