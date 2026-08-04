"""Tests for dashboard generation and installation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.dynamic_energy_prices import dashboard as dash
from custom_components.dynamic_energy_prices.const import DOMAIN


def _sensor(key: str) -> str:
    return f"sensor.essent_{key}"


def _binary(key: str) -> str:
    return f"binary_sensor.essent_{key}"


def _electricity_only_entities() -> dict[str, str]:
    return {
        "current_electricity_price": _sensor("current_electricity_price"),
        "next_electricity_price": _sensor("next_electricity_price"),
        "average_electricity_price": _sensor("average_electricity_price"),
        "cheapest_3h_block_electricity": _sensor("cheapest_3h_block_electricity"),
        "cheap_electricity": _binary("cheap_electricity"),
        "last_updated": _sensor("last_updated"),
        "next_update": _sensor("next_update"),
    }


def _full_entities() -> dict[str, str]:
    entities = _electricity_only_entities()
    entities.update(
        {
            "tomorrow_average_electricity_price": _sensor("tomorrow_average_electricity_price"),
            "tomorrow_lowest_electricity_price": _sensor("tomorrow_lowest_electricity_price"),
            "tomorrow_highest_electricity_price": _sensor("tomorrow_highest_electricity_price"),
            "current_gas_price": _sensor("current_gas_price"),
            "next_gas_price": _sensor("next_gas_price"),
        }
    )
    return entities


def _walk(card: object, matches: list[object]) -> None:
    if isinstance(card, dict):
        matches.append(card)
        for value in card.values():
            _walk(value, matches)
    elif isinstance(card, list):
        for item in card:
            _walk(item, matches)


def _cards_of_type(view: dict, card_type: str) -> list[dict]:
    matches: list[dict] = []
    _walk(view["cards"], matches)
    return [c for c in matches if c.get("type") == card_type]


class TestBuildProviderView:
    def test_electricity_only_no_gas_or_tomorrow(self) -> None:
        view = dash.build_provider_view(
            "Essent",
            _electricity_only_entities(),
            include_price_curve=False,
        )
        assert view is not None
        titles = {c.get("title") for c in view["cards"]}
        assert "Gas" not in titles
        assert "Tomorrow" not in titles
        assert _cards_of_type(view, "custom:apexcharts-card") == []
        grid = _cards_of_type(view, "grid")
        assert grid

    def test_no_sensors_returns_none(self) -> None:
        view = dash.build_provider_view("Essent", {}, include_price_curve=False)
        assert view is None

    def test_uses_resolved_entity_ids(self) -> None:
        entities = _full_entities()
        view = dash.build_provider_view("Essent", entities, include_price_curve=False)
        flat: list[dict] = []
        _walk(view["cards"], flat)
        referenced = {c["entity"] for c in flat if c.get("entity")}
        for entity_id in entities.values():
            assert entity_id in referenced

    def test_full_set_has_gas_and_tomorrow_and_cheapest(self) -> None:
        view = dash.build_provider_view(
            "Essent",
            _full_entities(),
            include_price_curve=False,
        )
        titles = {c.get("title") for c in view["cards"]}
        assert "Gas" in titles
        assert "Tomorrow" in titles
        assert "Cheapest 3-hour block" in titles

    def test_price_curve_only_when_requested_and_electricity_present(self) -> None:
        view = dash.build_provider_view(
            "Essent",
            _electricity_only_entities(),
            include_price_curve=True,
        )
        curves = _cards_of_type(view, "custom:apexcharts-card")
        assert len(curves) == 1

    def test_gas_only_entry(self) -> None:
        entities = {
            "current_gas_price": _sensor("current_gas_price"),
            "next_gas_price": _sensor("next_gas_price"),
        }
        view = dash.build_provider_view("Essent", entities, include_price_curve=True)
        assert view is not None
        titles = {c.get("title") for c in view["cards"]}
        assert "Gas" in titles
        assert _cards_of_type(view, "custom:apexcharts-card") == []

    def test_slugify_provider_name(self) -> None:
        assert dash._slugify("Frank Energie") == "frank-energie"


class FakeRegistry:
    def __init__(self, mapping: dict[tuple[str, str], str | None]) -> None:
        self._mapping = mapping

    def async_get_entity_id(self, platform: str, domain: str, unique_id: str) -> str | None:
        return self._mapping.get((platform, unique_id))


def _make_entry(
    entry_id: str,
    title: str,
    provider: str,
    options: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        entry_id=entry_id,
        title=title,
        data={"provider": provider},
        options=options or {},
    )


def _registry_for(entries: list[SimpleNamespace]) -> dict[tuple[str, str], str | None]:
    mapping: dict[tuple[str, str], str | None] = {}
    for entry in entries:
        suffix = entry.entry_id
        mapping[("sensor", f"{DOMAIN}_{suffix}_current_electricity_price")] = "sensor.essent_current_electricity_price"
        mapping[("sensor", f"{DOMAIN}_{suffix}_next_electricity_price")] = "sensor.essent_next_electricity_price"
        mapping[("sensor", f"{DOMAIN}_{suffix}_average_electricity_price")] = "sensor.essent_average_electricity_price"
        mapping[("sensor", f"{DOMAIN}_{suffix}_last_updated")] = "sensor.essent_last_updated"
        mapping[("sensor", f"{DOMAIN}_{suffix}_next_update")] = "sensor.essent_next_update"
        mapping[("binary_sensor", f"{DOMAIN}_{suffix}_cheap_electricity")] = "binary_sensor.essent_cheap_electricity"
    return mapping


class TestResolveEntities:
    async def test_resolves_sensor_and_binary_entities(self) -> None:
        entry = _make_entry("entry_1", "Essent", "essent")
        mapping = _registry_for([entry])
        fake_registry = FakeRegistry(mapping)
        hass = MagicMock()
        with patch.object(dash.entity_registry, "async_get", return_value=fake_registry):
            result = await dash.resolve_entities(hass, entry)
        assert result["current_electricity_price"] == "sensor.essent_current_electricity_price"
        assert result["cheap_electricity"] == "binary_sensor.essent_cheap_electricity"

    async def test_missing_entities_omitted(self) -> None:
        entry = _make_entry("entry_1", "Essent", "essent")
        mapping = {("sensor", f"{DOMAIN}_entry_1_current_electricity_price"): "sensor.essent_current_electricity_price"}
        fake_registry = FakeRegistry(mapping)
        hass = MagicMock()
        with patch.object(dash.entity_registry, "async_get", return_value=fake_registry):
            result = await dash.resolve_entities(hass, entry)
        assert result == {"current_electricity_price": "sensor.essent_current_electricity_price"}


class TestBuildDashboardConfig:
    async def test_merges_all_entries_into_views(self) -> None:
        entries = [
            _make_entry("entry_1", "Essent", "essent"),
            _make_entry("entry_2", "Eneco", "eneco"),
        ]
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = entries
        mapping = _registry_for(entries)
        fake_registry = FakeRegistry(mapping)
        with patch.object(dash.entity_registry, "async_get", return_value=fake_registry):
            config, skipped = await dash.build_dashboard_config(hass)
        assert skipped == []
        assert config is not None
        views = config["views"]
        assert len(views) == 2
        assert views[0]["title"] == "Essent"
        assert views[1]["title"] == "Eneco"

    async def test_skips_entries_without_sensors(self) -> None:
        entry = _make_entry("empty", "Empty", "essent")
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = [entry]
        fake_registry = FakeRegistry({})
        with patch.object(dash.entity_registry, "async_get", return_value=fake_registry):
            config, skipped = await dash.build_dashboard_config(hass)
        assert config is None
        assert skipped == ["Essent"]


class TestSaveDashboard:
    async def test_updates_existing_dashboard(self) -> None:
        config = {"title": "Energy Prices", "views": []}
        existing = MagicMock()
        existing.async_save = AsyncMock()
        lovelace = MagicMock()
        lovelace.dashboards = {dash.DASHBOARD_URL_PATH: existing}
        hass = MagicMock()
        hass.data = {"lovelace": lovelace}

        ok = await dash.save_dashboard(hass, config)

        assert ok is True
        existing.async_save.assert_awaited_once_with(config)

    async def test_creates_and_saves_dashboard(self) -> None:
        config = {"title": "Energy Prices", "views": []}
        new_dashboard = MagicMock()
        new_dashboard.async_save = AsyncMock()

        fake_store = MagicMock()
        fake_store.async_load = AsyncMock(return_value={"items": []})
        fake_store.async_save = AsyncMock()
        store_cls = MagicMock(return_value=fake_store)

        fake_const = MagicMock()
        fake_const.CONF_REQUIRE_ADMIN = "require_admin"
        fake_const.CONF_ICON = "icon"
        fake_const.CONF_TITLE = "title"
        fake_const.CONF_SHOW_IN_SIDEBAR = "show_in_sidebar"
        fake_const.CONF_MODE = "mode"
        fake_const.CONF_URL_PATH = "url_path"
        fake_const.MODE_STORAGE = "storage"
        fake_const.DOMAIN = "lovelace"

        fake_dashboard_mod = MagicMock()
        fake_dashboard_mod.LovelaceStorage = MagicMock(return_value=new_dashboard)

        lovelace = MagicMock()
        lovelace.dashboards = {}
        hass = MagicMock()
        hass.data = {"lovelace": lovelace}
        ll_frontend = MagicMock()

        with (
            patch.object(dash, "_INTERNAL_IMPORTS_OK", True),
            patch.object(dash, "_ll_const", fake_const),
            patch.object(dash, "_ll_dashboard", fake_dashboard_mod),
            patch.object(dash, "_ll_frontend", ll_frontend),
            patch.object(dash, "_ll_storage", type("S", (), {"Store": store_cls})),
        ):
            ok = await dash.save_dashboard(hass, config)

        assert ok is True
        store_cls.assert_called()
        fake_store.async_save.assert_awaited_once()
        fake_dashboard_mod.LovelaceStorage.assert_called_once()
        new_dashboard.async_save.assert_awaited_once_with(config)
        assert dash.DASHBOARD_URL_PATH in lovelace.dashboards
        ll_frontend.async_register_built_in_panel.assert_called_once()
        panel_kwargs = ll_frontend.async_register_built_in_panel.call_args.kwargs
        assert panel_kwargs["frontend_url_path"] == "energy-prices"
        assert panel_kwargs["show_in_sidebar"] is True

    async def test_without_dashboard_returns_false_when_internals_unavailable(self) -> None:
        lovelace = MagicMock()
        lovelace.dashboards = {}
        hass = MagicMock()
        hass.data = {"lovelace": lovelace}

        with (
            patch.object(dash, "_INTERNAL_IMPORTS_OK", False),
            patch.object(dash, "_ll_dashboard", None),
        ):
            ok = await dash.save_dashboard(hass, {"title": "x", "views": []})
        assert ok is False

    async def test_yaml_mode_returns_false(self) -> None:
        hass = MagicMock()
        hass.data = {"lovelace": MagicMock()}
        # no .dashboards dict -> treat as unavailable
        hass.data["lovelace"].dashboards = None
        ok = await dash.save_dashboard(hass, {"title": "x", "views": []})
        assert ok is False


class TestInstallDashboard:
    async def test_installs_when_entities_exist(self) -> None:
        entry = _make_entry("entry_1", "Essent", "essent")
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = [entry]
        fake_registry = FakeRegistry(_registry_for([entry]))
        with patch.object(dash.entity_registry, "async_get", return_value=fake_registry):
            lovelace = MagicMock()
            existing = MagicMock()
            existing.async_save = AsyncMock()
            lovelace.dashboards = {dash.DASHBOARD_URL_PATH: existing}
            hass.data = {"lovelace": lovelace}

            result = await dash.install_dashboard(hass)

        assert result["installed"] is True
        assert result["skipped"] == []
        saved = existing.async_save.await_args.args[0]
        assert saved["views"][0]["title"] == "Essent"

    async def test_no_entities_does_not_install(self) -> None:
        entry = _make_entry("empty", "Empty", "essent")
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = [entry]
        fake_registry = FakeRegistry({})
        with patch.object(dash.entity_registry, "async_get", return_value=fake_registry):
            hass.data = {}
            result = await dash.install_dashboard(hass)
        assert result["installed"] is False


class TestDashboardToYaml:
    def test_dumps_config(self) -> None:
        config = {"title": "Energy Prices", "views": [{"title": "Essent", "cards": []}]}
        yaml_str = dash.dashboard_to_yaml(config)
        assert "Energy Prices" in yaml_str
        assert "Essent" in yaml_str