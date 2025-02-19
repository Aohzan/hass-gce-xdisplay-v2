"""The gce_xdisplay_v2 component."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from homeassistant.components.mqtt.client import async_subscribe
from homeassistant.components.mqtt.util import async_wait_for_mqtt_client
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_SCREEN_TYPE_NAME,
    CONF_SCREENS,
    DOMAIN,
    XDisplayScreenTypes,
)
from .sync.button import XDisplayButtonSync
from .sync.cover import XDisplayCoverSync
from .sync.energy import XDisplayEnergySync
from .sync.media_player import XDisplayMediaPlayerSync
from .sync.sensor import XDisplaySensorSync
from .sync.thermostat import XDisplayThermostatSync
from .sync.weather import XDisplayWeatherSync

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
    if len(config[CONF_SCREENS]) == 0:
        _LOGGER.error("No screens configured")
    for screen_id, screen_options in enumerate(config[CONF_SCREENS]):
        _LOGGER.debug("Screen #%s: %s", screen_id, screen_options)
        if screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.BUTTON.name:
            button_sync = XDisplayButtonSync(
                hass,
                config_entry,
                screen_id,
                screen_options,
            )
            await async_subscribe(
                hass=hass,
                topic=button_sync.topic_sub,
                msg_callback=button_sync.update_entity,
            )
        elif screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.COVER.name:
            cover_sync = XDisplayCoverSync(
                hass, config_entry, screen_id, screen_options
            )
            await async_subscribe(
                hass=hass,
                topic=cover_sync.sub_topic_position,
                msg_callback=cover_sync.update_entity,
            )
        elif (
            screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.THERMOSTAT.name
        ):
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
        elif (
            screen_options[CONF_SCREEN_TYPE_NAME]
            == XDisplayScreenTypes.TEMPERATURE.name
        ):
            XDisplaySensorSync(hass, config_entry, screen_id, screen_options, "temp")
        elif screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.HUMIDITY.name:
            XDisplaySensorSync(hass, config_entry, screen_id, screen_options, "hum")
        elif (
            screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.LUMINOSITY.name
        ):
            XDisplaySensorSync(hass, config_entry, screen_id, screen_options, "lum")
        elif screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.WEATHER.name:
            XDisplayWeatherSync(hass, config_entry, screen_id, screen_options)
        elif screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.PLAYER.name:
            player_sync = XDisplayMediaPlayerSync(
                hass, config_entry, screen_id, screen_options
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_vol_down,
                msg_callback=partial(player_sync.update_entity, action="volume_down"),
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_vol_up,
                msg_callback=partial(player_sync.update_entity, action="volume_up"),
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_mute,
                msg_callback=partial(player_sync.update_entity, action="volume_mute"),
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_next,
                msg_callback=partial(
                    player_sync.update_entity, action="media_next_track"
                ),
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_prev,
                msg_callback=partial(
                    player_sync.update_entity, action="media_previous_track"
                ),
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_pause,
                msg_callback=partial(
                    player_sync.update_entity, action="media_play_pause"
                ),
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_loop,
                msg_callback=partial(player_sync.update_entity, action="repeat_set"),
            )
            await async_subscribe(
                hass=hass,
                topic=player_sync.sub_topic_random,
                msg_callback=partial(player_sync.update_entity, action="shuffle_set"),
            )
        elif screen_options[CONF_SCREEN_TYPE_NAME] == XDisplayScreenTypes.ENERGY.name:
            energy = XDisplayEnergySync(hass, config_entry, screen_id, screen_options)
            await energy.initialize()
        else:
            _LOGGER.info(
                "Screen #%s: %s is not supported or not implemented",
                screen_id,
                screen_options[CONF_SCREEN_TYPE_NAME],
            )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
