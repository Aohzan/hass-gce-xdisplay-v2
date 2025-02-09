"""Config flow for Hello World integration."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.mqtt.const import (
    DOMAIN as MQTT_DOMAIN,
)
from homeassistant.components.mqtt.util import valid_subscribe_topic
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import (
    CONF_PREFIX_TOPIC,
    CONF_SCREEN_ID,
    CONF_SCREEN_LINKED_ENTITY,
    CONF_SCREEN_TYPE_NAME,
    CONF_SCREENS,
    DOMAIN,
    XDISPLAY_SCREEN_TYPE_DEVICE_CLASSES,
    XDISPLAY_SCREEN_TYPE_DOMAINS,
    XDisplayScreenTypes,
)
from .tools_mqtt import (
    xdisplay_mqtt_add_screen,
    xdisplay_mqtt_delete_last_screen,
    xdisplay_mqtt_update_screen_name,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult

_LOGGER = logging.getLogger(__name__)


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PREFIX_TOPIC, default="x-display_"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hello World."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if MQTT_DOMAIN not in self.hass.config.components:
            errors["base"] = "mqtt_not_setup"
        elif user_input is not None:
            try:
                entry_data = {
                    CONF_PREFIX_TOPIC: user_input[CONF_PREFIX_TOPIC].rstrip("/"),
                    CONF_SCREENS: [],
                }

                valid_subscribe_topic(entry_data[CONF_PREFIX_TOPIC] + "/temp")

                entry_data[CONF_DEVICE_ID] = entry_data[CONF_PREFIX_TOPIC].split("_")[
                    -1
                ]
                return self.async_create_entry(
                    title=f"X-Display {entry_data[CONF_DEVICE_ID]}", data=entry_data
                )
            except vol.Invalid:
                errors["base"] = "invalid_topic"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Define the config flow to handle options."""
        return XdisplayOptionsFlowHandler(config_entry)


class XdisplayOptionsFlowHandler(OptionsFlow):
    """Handle a RFPLayer options flow."""

    device_registry: dr.DeviceRegistry

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self.config_entry = config_entry
        self.user_input: dict[str, Any] | None = None
        self.config = config_entry.data | config_entry.options
        self.screens_list: list = [
            f"{screen_id}-{screen_options[CONF_SCREEN_TYPE_NAME]} {screen_options.get(CONF_NAME, '')}"
            for screen_id, screen_options in enumerate(self.config[CONF_SCREENS])
        ]

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        self.device_registry = dr.async_get(self.hass)

        return self.async_show_menu(
            step_id="init",
            menu_options={
                "add_screen": "Add a screen",
                "update_screen": "Edit a screen",
                "remove_last_screen": "Remove last screen",
            },
        )

    async def async_step_add_screen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a screen."""
        errors: dict[str, Any] = {}
        data_schema = vol.Schema(
            {
                vol.Required(CONF_SCREEN_TYPE_NAME): vol.In(
                    [t.name for t in XDisplayScreenTypes]
                )
            }
        )

        if user_input is None:
            return self.async_show_form(
                step_id="add_screen",
                data_schema=data_schema,
                errors=errors,
            )

        self.user_input = user_input
        return await self.async_step_add_screen_step_2()

    async def async_step_add_screen_step_2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a screen step 2."""
        errors: dict[str, Any] = {}
        data_schema = vol.Schema({})

        if not self.user_input:
            return await self.async_step_add_screen()

        domains = XDISPLAY_SCREEN_TYPE_DOMAINS[self.user_input[CONF_SCREEN_TYPE_NAME]]
        # if entity must be linked to the screen
        if domains:
            devices_classes = XDISPLAY_SCREEN_TYPE_DEVICE_CLASSES.get(
                self.user_input[CONF_SCREEN_TYPE_NAME]
            )
            if devices_classes:
                selector_config = selector.EntitySelectorConfig(
                    domain=domains, device_class=devices_classes
                )
            else:
                selector_config = selector.EntitySelectorConfig(domain=domains)

            data_schema = vol.Schema(
                {
                    vol.Required(CONF_SCREEN_LINKED_ENTITY): selector.EntitySelector(
                        selector_config
                    ),
                }
            )

        if not user_input:
            return self.async_show_form(
                step_id="add_screen_step_2",
                data_schema=data_schema,
                errors=errors,
            )

        if domains:
            if self.hass.states.get(user_input[CONF_SCREEN_LINKED_ENTITY]) is None:
                errors["base"] = "entity_not_found"
            if (
                user_input[CONF_SCREEN_LINKED_ENTITY].split(".")[0]
                not in XDISPLAY_SCREEN_TYPE_DOMAINS[
                    self.user_input[CONF_SCREEN_TYPE_NAME]
                ]
            ):
                errors["base"] = "entity_wrong_domain"

        if errors:
            return self.async_show_form(
                step_id="add_screen_step_2",
                data_schema=data_schema,
                errors=errors,
            )

        _LOGGER.info(
            "Adding screen %s linked to %s",
            self.user_input[CONF_SCREEN_TYPE_NAME],
            user_input[CONF_SCREEN_LINKED_ENTITY],
        )

        await xdisplay_mqtt_add_screen(
            self.hass,
            self.config_entry.data[CONF_PREFIX_TOPIC],
            XDisplayScreenTypes[self.user_input[CONF_SCREEN_TYPE_NAME]],
        )

        self.update_screen_config_data(
            screen_id=None,
            options={
                CONF_SCREEN_TYPE_NAME: self.user_input[CONF_SCREEN_TYPE_NAME],
                CONF_SCREEN_LINKED_ENTITY: user_input[CONF_SCREEN_LINKED_ENTITY],
                CONF_NAME: "",
            },
        )

        return self.async_create_entry(title="", data={})

    async def async_step_update_screen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update a screen."""
        errors: dict[str, Any] = {}

        if not self.screens_list:
            return self.async_abort(
                reason="no_screens_registered",
            )

        data_schema = vol.Schema(
            {vol.Required(CONF_SCREEN_ID): vol.In(self.screens_list)}
        )

        if user_input is None:
            return self.async_show_form(
                step_id="update_screen",
                data_schema=data_schema,
                errors=errors,
            )

        self.user_input = user_input
        return await self.async_step_update_screen_name()

    async def async_step_update_screen_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update a screen step name."""
        errors: dict[str, Any] = {}

        if not self.user_input:
            return await self.async_step_update_screen()

        screen_id = int(self.user_input[CONF_SCREEN_ID].split("-")[0])

        screen_config: dict[str, Any] = self.config_entry.data[CONF_SCREENS][screen_id]

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME,
                    default=screen_config.get(
                        CONF_NAME, screen_config.get(CONF_SCREEN_TYPE_NAME)
                    ),
                ): str,
            }
        )

        if not user_input:
            return self.async_show_form(
                step_id="update_screen_name",
                data_schema=data_schema,
                errors=errors,
            )

        _LOGGER.info(
            "Updating screen #%s name to %s",
            screen_id,
            user_input[CONF_NAME],
        )

        await xdisplay_mqtt_update_screen_name(
            self.hass,
            prefix_topic=self.config_entry.data[CONF_PREFIX_TOPIC],
            screen_id=screen_id,
            screen_name=user_input[CONF_NAME],
        )

        self.update_screen_config_data(
            screen_id=screen_id,
            options={CONF_NAME: user_input[CONF_NAME]},
        )

        return self.async_create_entry(title="", data={})

    async def async_step_remove_last_screen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove a screen."""
        if user_input is None or not user_input.get("confirm"):
            return self.async_show_form(
                step_id="remove_last_screen",
                data_schema=vol.Schema({vol.Required("confirm"): bool}),
            )

        _LOGGER.info(
            "Removing last screen from %s", self.config_entry.data[CONF_PREFIX_TOPIC]
        )

        await xdisplay_mqtt_delete_last_screen(
            self.hass, self.config_entry.data[CONF_PREFIX_TOPIC]
        )

        self.update_screen_config_data()

        return self.async_create_entry(title="", data={})

    @callback
    def update_screen_config_data(
        self,
        screen_id: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Update data in ConfigEntry."""
        entry_data = self.config_entry.data.copy()
        entry_data[CONF_SCREENS] = copy.deepcopy(
            list(self.config_entry.data[CONF_SCREENS])
        )

        if not options:
            _LOGGER.debug("Deleting last screen")
            if len(entry_data[CONF_SCREENS]) > 0:
                del entry_data[CONF_SCREENS][-1]
        elif screen_id is None:
            _LOGGER.debug("Adding screen #%s", screen_id)
            entry_data[CONF_SCREENS].append(options)
        else:
            _LOGGER.debug("Updating screen #%s", screen_id)
            entry_data[CONF_SCREENS][screen_id] = (
                entry_data[CONF_SCREENS][screen_id] | options
            )

        self.hass.config_entries.async_update_entry(self.config_entry, data=entry_data)
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self.config_entry.entry_id)
        )
