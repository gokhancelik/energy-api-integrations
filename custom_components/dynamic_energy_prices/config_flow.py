"""Config flow for Dynamic Energy Prices integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_PROVIDER, DOMAIN
from .providers import PROVIDER_REGISTRY, ProviderConnectionError, ProviderResponseError


class DynamicEnergyPricesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dynamic Energy Prices."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            provider_id = user_input[CONF_PROVIDER]
            provider_cls = PROVIDER_REGISTRY.get(provider_id)

            if provider_cls is None:
                errors["base"] = "unknown_provider"
            else:
                unique_id = f"{DOMAIN}_{provider_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                provider = provider_cls()
                try:
                    await provider.async_fetch_prices()
                except ProviderConnectionError:
                    errors["base"] = "cannot_connect"
                except ProviderResponseError:
                    errors["base"] = "invalid_response"
                except Exception:
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title=provider_cls.display_name,
                        data={
                            CONF_PROVIDER: provider_id,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_PROVIDER): vol.In(
                    {
                        pid: cls.display_name
                        for pid, cls in PROVIDER_REGISTRY.items()
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
