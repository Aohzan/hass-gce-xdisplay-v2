"""The gce_xdisplay_v2 component."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Any

from homeassistant.components.mqtt.client import async_publish, async_subscribe
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.components.mqtt.util import async_wait_for_mqtt_client
from homeassistant.const import Platform
from homeassistant.core import Event, EventStateChangedData, HassJob, HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from .const import (
    CONF_PREFIX_TOPIC,
    CONF_SCREEN_LINKED_ENTITY,
    CONF_SCREEN_TYPE_NAME,
    CONF_SCREENS,
    DOMAIN,
    XDisplayScreenTypes,
)
from .tools_sync import XDisplayButtonSync, XDisplayThermostatSync

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up entry."""
    hass.data.setdefault(DOMAIN, {})

    if not await async_wait_for_mqtt_client(hass):
        _LOGGER.error("MQTT integration is not available")
        return False
    _LOGGER.debug("MQTT available")

    config = config_entry.data

    # Create base entities
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Create screens pub and sub topics
    for screen_id, screen_options in config.get(CONF_SCREENS, {}).items():
        _LOGGER.debug("Screen #%s: %s", screen_id, screen_options)
        if screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.BUTTON.name:
            button_sync = XDisplayButtonSync(
                hass,
                config_entry,
                screen_id,
                screen_options,
                suffix_pub="IoCmd",
                suffix_sub="IoState",
            )
            await async_subscribe(
                hass=hass,
                topic=button_sync.topic_sub,
                msg_callback=button_sync.update_entity,
            )
            break
        if screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.THERMOSTAT.name:
            thermostat_sync = XDisplayThermostatSync(
                hass, config_entry, screen_id, screen_options
            )

            await async_subscribe(
                hass=hass,
                topic=thermostat_sync.sub_topic_target_temp,
                msg_callback=partial(
                    thermostat_sync.update_entity, action="set_temperature"
                ),
            )
            await async_subscribe(
                hass=hass,
                topic=thermostat_sync.sub_topic_turned_on,
                msg_callback=partial(
                    thermostat_sync.update_entity, action="set_hvac_mode"
                ),
            )
            break
        _LOGGER.info(
            "Screen #%s: %s is not supported or not implemented",
            screen_id,
            screen_options[CONF_SCREEN_TYPE_NAME],
        )
    else:
        _LOGGER.debug("No screens configured")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
