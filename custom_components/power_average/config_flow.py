"""Config flow for Power Average Calculator integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
)

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Get the schema for the form."""
    if user_input is None:
        user_input = {}
    
    return vol.Schema(
        {
            vol.Required("name", default=user_input.get("name", "Power Average")): TextSelector(),
            vol.Required("current_l1", default=user_input.get("current_l1", "")): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="current")
            ),
            vol.Required("current_l2", default=user_input.get("current_l2", "")): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="current")
            ),
            vol.Required("current_l3", default=user_input.get("current_l3", "")): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="current")
            ),
            vol.Required("voltage_l1", default=user_input.get("voltage_l1", "")): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),
            vol.Required("voltage_l2", default=user_input.get("voltage_l2", "")): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),
            vol.Required("voltage_l3", default=user_input.get("voltage_l3", "")): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Power Average Calculator."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            await self.async_set_unique_id(user_input["name"])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=user_input["name"],
                data=user_input,
            )
        
        return self.async_show_form(
            step_id="user",
            data_schema=get_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=get_schema(self.config_entry.data),
        )