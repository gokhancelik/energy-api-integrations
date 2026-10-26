"""Register the bundled Lovelace price chart card."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_TAG = "dynamic-energy-prices-chart"
CARD_FILENAME = f"{CARD_TAG}.js"
CARD_URL_PATH = f"/{DOMAIN}/frontend"
CARD_URL = f"{CARD_URL_PATH}/{CARD_FILENAME}"
_REGISTERED_KEY = "dynamic_energy_prices_frontend_registered"


def _card_version() -> str:
    """Return the integration version for cache busting."""
    try:
        manifest = json.loads(
            (Path(__file__).parent / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return "0"
    return str(manifest.get("version", "0"))


def is_card_registered(hass: HomeAssistant) -> bool:
    """Return True when the bundled card was registered with the frontend."""
    data = getattr(hass, "data", None)
    return isinstance(data, dict) and bool(data.get(_REGISTERED_KEY))


def _frontend_api():
    """Return the Home Assistant frontend helpers used for registration."""
    from homeassistant.components import frontend
    from homeassistant.components.http import StaticPathConfig

    return frontend, StaticPathConfig


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve and load the bundled chart card, best effort.

    Existing dashboards reference ``custom:dynamic-energy-prices-chart``; if
    the frontend is unavailable we log the failure instead of blocking the
    integration setup.
    """
    if is_card_registered(hass):
        return

    http = getattr(hass, "http", None)
    if http is None:
        return

    card_dir = Path(__file__).parent / "frontend"
    card_file = card_dir / CARD_FILENAME
    if not card_file.is_file():
        _LOGGER.warning("Bundled dashboard chart card is missing: %s", card_file)
        return

    try:
        frontend, static_path_config = _frontend_api()
    except ImportError:  # pragma: no cover - mocked/test environments
        return

    try:
        await http.async_register_static_paths(
            [static_path_config(CARD_URL_PATH, str(card_dir), True)]
        )
        frontend.add_extra_js_url(hass, f"{CARD_URL}?v={_card_version()}")
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to register the dashboard chart card.")
        return

    data = getattr(hass, "data", None)
    if isinstance(data, dict):
        data[_REGISTERED_KEY] = True
