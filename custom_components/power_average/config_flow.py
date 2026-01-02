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
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from . import DOMAIN

CONF_POWER_TARGETS = "power_targets"

_LOGGER = logging.getLogger(__name__)


def get_schema(user_input: dict[str, Any] | None = None, include_name: bool = True) -> vol.Schema:
    """Get the schema for the form."""
    if user_input is None:
        user_input = {}

    schema_dict = {}

    if include_name:
        schema_dict[vol.Required("name", default=user_input.get("name", "Power Average"))] = TextSelector()

    schema_dict.update({
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
    })

    return vol.Schema(schema_dict)


def get_power_targets_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Get the schema for power targets configuration."""
    if user_input is None:
        user_input = {}

    existing_targets = user_input.get(CONF_POWER_TARGETS, [])

    return vol.Schema(
        {
            vol.Optional(
                CONF_POWER_TARGETS,
                default=existing_targets,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[],
                    custom_value=True,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Power Average Calculator."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input["name"])
            self._abort_if_unique_id_configured()

            self._data = user_input
            return await self.async_step_power_targets()

        return self.async_show_form(
            step_id="user",
            data_schema=get_schema(user_input),
            errors=errors,
        )

    async def async_step_power_targets(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the power targets step."""
        if user_input is not None:
            power_targets = []
            raw_targets = user_input.get(CONF_POWER_TARGETS, [])
            for target in raw_targets:
                try:
                    power_targets.append(int(float(target)))
                except (ValueError, TypeError):
                    pass

            self._data[CONF_POWER_TARGETS] = power_targets

            return self.async_create_entry(
                title=self._data["name"],
                data=self._data,
            )

        return self.async_show_form(
            step_id="power_targets",
            data_schema=get_power_targets_schema(),
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
        self._data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - entity selection."""
        if user_input is not None:
            self._data = dict(self.config_entry.data)
            self._data.update(user_input)
            return await self.async_step_power_targets()

        return self.async_show_form(
            step_id="init",
            data_schema=get_schema(self.config_entry.data, include_name=False),
        )

    async def async_step_power_targets(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the power targets options step."""
        if user_input is not None:
            power_targets = []
            raw_targets = user_input.get(CONF_POWER_TARGETS, [])
            for target in raw_targets:
                try:
                    power_targets.append(int(float(target)))
                except (ValueError, TypeError):
                    pass

            self._data[CONF_POWER_TARGETS] = power_targets

            return self.async_create_entry(title="", data=self._data)

        existing_targets = list(self.config_entry.data.get(CONF_POWER_TARGETS, []))
        existing_data = {CONF_POWER_TARGETS: [str(t) for t in existing_targets]}

        return self.async_show_form(
            step_id="power_targets",
            data_schema=get_power_targets_schema(existing_data),
        )