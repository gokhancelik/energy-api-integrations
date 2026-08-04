"""Dashboard generation and installation for Dynamic Energy Prices.

Builds a provider-aware Lovelace dashboard from the entity registry, so the
correct entity IDs are used for whichever provider(s) are configured, and
installs it into Home Assistant's (storage-mode) Lovelace at runtime.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from .const import (
    CONF_INCLUDE_PRICE_CURVE,
    CONF_PROVIDER,
    DOMAIN,
    DynamicEnergyPricesConfigEntry,
)
from .providers import PROVIDER_REGISTRY

_LOGGER = logging.getLogger(__name__)

DASHBOARD_URL_PATH = "energy-prices"
DASHBOARD_TITLE = "Energy Prices"
DASHBOARD_ICON = "mdi:flash"

_SENSOR_KEYS = (
    "current_electricity_price",
    "next_electricity_price",
    "average_electricity_price",
    "cheapest_3h_block_electricity",
    "tomorrow_average_electricity_price",
    "tomorrow_lowest_electricity_price",
    "tomorrow_highest_electricity_price",
    "current_gas_price",
    "next_gas_price",
    "last_updated",
    "next_update",
)
_BINARY_KEYS = ("cheap_electricity",)


def _entity_id(
    entities: dict[str, str],
    key: str,
    expected_platform: str,
) -> str | None:
    """Return the resolved entity ID for ``key`` or None when not present."""
    entity_id = entities.get(key)
    if entity_id is None:
        return None
    platform = entity_id.split(".", 1)[0]
    if platform != expected_platform:
        return None
    return entity_id


def _required(entities: dict[str, str], *keys: str) -> bool:
    """Return True when every key resolves to an entity ID."""
    return all(entities.get(key) for key in keys)


def build_provider_view(
    provider_name: str,
    entities: dict[str, str],
    *,
    include_price_curve: bool,
    icon: str = DASHBOARD_ICON,
) -> dict[str, Any] | None:
    """Build a single view (tab) for one provider entry.

    Only cards whose entities actually exist are included, so electricity-only
    vs gas/tomorrow setups render correctly.
    """
    current = _entity_id(entities, "current_electricity_price", "sensor")
    next_elec = _entity_id(entities, "next_electricity_price", "sensor")
    average = _entity_id(entities, "average_electricity_price", "sensor")
    cheap = _entity_id(entities, "cheap_electricity", "binary_sensor")
    current_gas = _entity_id(entities, "current_gas_price", "sensor")
    next_gas = _entity_id(entities, "next_gas_price", "sensor")

    if all(eid is None for eid in (current, next_elec, average, current_gas, next_gas)):
        # No usable sensors at all for this entry.
        return None

    cards: list[dict[str, Any]] = []

    grid_cards: list[dict[str, Any]] = []
    if current is not None:
        grid_cards.append(
            {"type": "tile", "entity": current, "name": "Current price", "icon": "mdi:flash"}
        )
    if next_elec is not None:
        grid_cards.append(
            {"type": "tile", "entity": next_elec, "name": "Next hour", "icon": "mdi:flash-outline"}
        )
    if average is not None:
        grid_cards.append(
            {"type": "tile", "entity": average, "name": "Today's average", "icon": "mdi:chart-line"}
        )
    if cheap is not None:
        grid_cards.append(
            {"type": "tile", "entity": cheap, "name": "Cheap now?", "icon": "mdi:cash-check"}
        )
    if grid_cards:
        cards.append({"type": "grid", "columns": 2, "square": False, "cards": grid_cards})

    if include_price_curve and current is not None and average is not None:
        cards.append(_price_curve_card(current, average))

    cheapest = _entity_id(entities, "cheapest_3h_block_electricity", "sensor")
    if cheapest is not None:
        cards.append(
            {
                "type": "entities",
                "title": "Cheapest 3-hour block",
                "entities": [
                    {"entity": cheapest, "name": "Starts"},
                    {"entity": cheapest, "type": "attribute", "attribute": "end_time", "name": "Ends"},
                    {"entity": cheapest, "type": "attribute", "attribute": "average_price", "name": "Average price in block"},
                ],
            }
        )

    tomorrow_average = _entity_id(entities, "tomorrow_average_electricity_price", "sensor")
    tomorrow_lowest = _entity_id(entities, "tomorrow_lowest_electricity_price", "sensor")
    tomorrow_highest = _entity_id(entities, "tomorrow_highest_electricity_price", "sensor")
    if tomorrow_average is not None or tomorrow_lowest is not None or tomorrow_highest is not None:
        tomorrow_entities: list[dict[str, Any]] = []
        if tomorrow_average is not None:
            tomorrow_entities.append({"entity": tomorrow_average, "name": "Average"})
        if tomorrow_lowest is not None:
            tomorrow_entities.append({"entity": tomorrow_lowest, "name": "Lowest"})
        if tomorrow_highest is not None:
            tomorrow_entities.append({"entity": tomorrow_highest, "name": "Highest"})
        cards.append({"type": "entities", "title": "Tomorrow", "entities": tomorrow_entities})

    current_gas = _entity_id(entities, "current_gas_price", "sensor")
    next_gas = _entity_id(entities, "next_gas_price", "sensor")
    if current_gas is not None or next_gas is not None:
        gas_entities: list[dict[str, Any]] = []
        if current_gas is not None:
            gas_entities.append({"entity": current_gas, "name": "Current"})
        if next_gas is not None:
            gas_entities.append({"entity": next_gas, "name": "Next hour"})
        cards.append({"type": "entities", "title": "Gas", "entities": gas_entities})

    last_updated = _entity_id(entities, "last_updated", "sensor")
    next_update = _entity_id(entities, "next_update", "sensor")
    _ = next_update
    dbg_entities: list[dict[str, Any]] = []
    if last_updated is not None:
        dbg_entities.append({"entity": last_updated, "name": "Last updated"})
    if next_update is not None:
        dbg_entities.append({"entity": next_update, "name": "Next update"})
    if current is not None:
        dbg_entities.append(
            {
                "type": "button",
                "name": "Force refresh",
                "icon": "mdi:refresh",
                "tap_action": {
                    "action": "call-service",
                    "service": f"{DOMAIN}.force_update",
                    "target": {"entity_id": current},
                },
            }
        )
    if dbg_entities:
        cards.append(
            {
                "type": "entities",
                "title": "Diagnostics",
                "show_header_toggle": False,
                "entities": dbg_entities,
            }
        )

    return {
        "title": provider_name,
        "icon": icon,
        "path": _slugify(provider_name or "provider"),
        "cards": cards,
    }


def _slugify(value: str) -> str:
    """Create a simple url-safe path slug from a display name."""
    out = []
    for char in value.lower():
        if char.isalnum():
            out.append(char)
        elif char in " _-":
            out.append("-")
    slug = "".join(out).strip("-")
    return slug or "provider"


def _price_curve_card(current: str, average: str) -> dict[str, Any]:
    """Build the apexcharts-card price-curve card."""
    return {
        "type": "custom:apexcharts-card",
        "header": {"show": True, "title": "Today's electricity price"},
        "graph_span": "24h",
        "span": {"start": "day"},
        "now": {"show": True, "label": "Now"},
        "yaxis": [{"decimals": 3}],
        "series": [
            {
                "entity": current,
                "name": "Price",
                "type": "column",
                "color": "var(--primary-color)",
                "data_generator": "return entity.attributes.hourly_prices.map((p) => {\n"
                'const [h, m] = p.start.split(":").map(Number);\n'
                "const d = new Date();\n"
                "d.setHours(h, m, 0, 0);\n"
                "return [d.getTime(), p.price];\n"
                "});",
            },
            {
                "entity": average,
                "name": "Average",
                "type": "line",
                "color": "var(--secondary-text-color)",
                "curve": "straight",
                "data_generator": (
                    'const curve = hass.states["'
                    + current
                    + '"].attributes.hourly_prices;\n'
                    "const avg = parseFloat(entity.state);\n"
                    "return curve.map((p) => {\n"
                    'const [h, m] = p.start.split(":").map(Number);\n'
                    "const d = new Date();\n"
                    "d.setHours(h, m, 0, 0);\n"
                    "return [d.getTime(), avg];\n"
                    "});"
                ),
            },
        ],
    }


async def resolve_entities(
    hass: HomeAssistant,
    entry: DynamicEnergyPricesConfigEntry,
) -> dict[str, str]:
    """Resolve real entity IDs for a config entry from the entity registry."""
    reg = entity_registry.async_get(hass)
    entities: dict[str, str] = {}

    for key in _SENSOR_KEYS:
        unique_id = f"{DOMAIN}_{entry.entry_id}_{key}"
        entity_id = reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id is not None:
            entities[key] = entity_id

    for key in _BINARY_KEYS:
        unique_id = f"{DOMAIN}_{entry.entry_id}_{key}"
        entity_id = reg.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
        if entity_id is not None:
            entities[key] = entity_id

    return entities


def _build_dashboard_config(views: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap a list of views into a dashboard config dict."""
    return {"title": DASHBOARD_TITLE, "views": views}


async def build_dashboard_config(
    hass: HomeAssistant,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Build a merged dashboard config for all configured entries.

    Returns ``(config, skipped)`` where ``config`` is None (and ``skipped``
    lists every entry) when no entry has any usable sensors.
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    views: list[dict[str, Any]] = []
    skipped: list[str] = []

    for entry in entries:
        provider_id = entry.data.get(CONF_PROVIDER)
        provider_cls = PROVIDER_REGISTRY.get(provider_id) if provider_id else None
        provider_name = provider_cls.display_name if provider_cls else entry.title

        entities = await resolve_entities(hass, entry)
        include_price_curve = bool(entry.options.get(CONF_INCLUDE_PRICE_CURVE, False))
        view = build_provider_view(
            provider_name,
            entities,
            include_price_curve=include_price_curve,
        )
        if view is None:
            skipped.append(provider_name)
            continue
        views.append(view)

    if not views:
        return None, skipped
    return _build_dashboard_config(views), skipped


async def save_dashboard(
    hass: HomeAssistant,
    config: dict[str, Any],
) -> bool:
    """Persist the dashboard config into Lovelace (storage mode).

    Returns True on success, or False when Lovelace is unavailable (e.g. YAML
    mode) so callers can fall back to raw YAML export.
    """
    lovelace = hass.data.get("lovelace")
    if lovelace is None or getattr(lovelace, "dashboards", None) is None:
        _LOGGER.warning(
            "Lovelace is not editable from this integration (YAML mode or "
            "not available); the dashboard could not be installed automatically."
        )
        return False

    dashboards = lovelace.dashboards
    dashboard = await dashboards.async_get_dashboard(DASHBOARD_URL_PATH)
    if dashboard is None:
        await dashboards.async_create_item(
            {
                "url_path": DASHBOARD_URL_PATH,
                "title": DASHBOARD_TITLE,
                "icon": DASHBOARD_ICON,
                "show_in_sidebar": True,
                "views": [],
            }
        )
        dashboard = await dashboards.async_get_dashboard(DASHBOARD_URL_PATH)

    if dashboard is None:
        _LOGGER.error("Could not create the %s dashboard.", DASHBOARD_TITLE)
        return False

    await dashboard.async_save(config)
    _LOGGER.info("Installed/updated the %s dashboard.", DASHBOARD_TITLE)
    return True


def dashboard_to_yaml(config: dict[str, Any]) -> str:
    """Render a dashboard config to YAML for manual import."""
    import yaml  # local import so import works without PyYAML at module load

    return yaml.dump(
        config,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


async def install_dashboard(hass: HomeAssistant) -> dict[str, Any]:
    """Build and install/update the shared Energy Prices dashboard.

    Returns a dict with ``installed`` (bool) and ``skipped`` (list of entry
    titles with no usable sensors).
    """
    config, skipped = await build_dashboard_config(hass)
    result: dict[str, Any] = {"installed": False, "skipped": skipped}

    if config is None:
        _LOGGER.warning(
            "No configurable sensors found for the Dynamic Energy Prices "
            "dashboards; nothing to install. Skipped: %s",
            skipped,
        )
        return result

    result["installed"] = await save_dashboard(hass, config)
    return result