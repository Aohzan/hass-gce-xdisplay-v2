"""Sync between entities and X-Display screens."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.mqtt.client import async_publish
from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from custom_components.gce_xdisplay_v2.const import (
    CONF_SCREEN_LINKED_ENTITY,
)

from . import XDisplaySync

if TYPE_CHECKING:
    from homeassistant.components.mqtt.models import ReceiveMessage
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, EventStateChangedData, HomeAssistant

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

_LOGGER = logging.getLogger(__name__)


class XDisplayWeatherSync(XDisplaySync):
    """Sync between entity and X-Display weather screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry[Any],
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)

        self.pub_topic_hum = f"{self.topic_prefix}/Wthum"
        self.pub_topic_temp = f"{self.topic_prefix}/Whtemp"
        self.pub_topic_wind = f"{self.topic_prefix}/Whwind"
        # Data : 0 (soleil), 1(éclaircie), 2(nuage)…
        # … 3(brouillard), 4(pluie), 5(orage), 6(neige)
        self.pub_topic_level = f"{self.topic_prefix}/WhLevel"
        self.pub_topic_pressure = f"{self.topic_prefix}/WhPressure"
        self.pub_topic_sunrise = f"{self.topic_prefix}/WhSunrise"
        self.pub_topic_sunset = f"{self.topic_prefix}/WhSunset"
        self.pub_topic_temp_d1 = f"{self.topic_prefix}/WhtempD1"
        self.pub_topic_level_d1 = f"{self.topic_prefix}/WhLevelD1"
        self.pub_topic_temp_d2 = f"{self.topic_prefix}/WhtempD2"
        self.pub_topic_level_d2 = f"{self.topic_prefix}/WhLevelD2"
        self.pub_topic_temp_d3 = f"{self.topic_prefix}/WhtempD3"
        self.pub_topic_level_d3 = f"{self.topic_prefix}/WhLevelD3"

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    def convert_weather_level(self, level: str) -> int:
        """Convert weather level to X-Display level."""
        level_mapping = {
            ATTR_CONDITION_SUNNY: 0,
            ATTR_CONDITION_CLEAR_NIGHT: 1,
            ATTR_CONDITION_PARTLYCLOUDY: 1,
            ATTR_CONDITION_CLOUDY: 2,
            ATTR_CONDITION_WINDY: 2,
            ATTR_CONDITION_WINDY_VARIANT: 2,
            ATTR_CONDITION_FOG: 3,
            ATTR_CONDITION_RAINY: 4,
            ATTR_CONDITION_POURING: 4,
            ATTR_CONDITION_HAIL: 4,
            ATTR_CONDITION_LIGHTNING_RAINY: 5,
            ATTR_CONDITION_LIGHTNING: 5,
            ATTR_CONDITION_SNOWY: 6,
            ATTR_CONDITION_SNOWY_RAINY: 6,
        }
        return level_mapping.get(level, 0)

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None or to_state.state in [
            "unavailable",
            "unknown",
        ]:
            return
        _LOGGER.debug(
            "Watched entity %s has changed:",
            event.data["entity_id"],
        )
        _LOGGER.debug(
            "level: %s, temp %s, hum %s, wind %s, pressure %s",
            to_state.state,
            to_state.attributes["temperature"],
            to_state.attributes["humidity"],
            to_state.attributes["wind_speed"],
            to_state.attributes["pressure"],
        )
        await async_publish(
            self.hass,
            self.pub_topic_hum,
            to_state.attributes["humidity"],
        )
        await async_publish(
            self.hass,
            self.pub_topic_temp,
            to_state.attributes["temperature"],
        )
        await async_publish(
            self.hass,
            self.pub_topic_wind,
            to_state.attributes["wind_speed"],
        )
        await async_publish(
            self.hass,
            self.pub_topic_level,
            self.convert_weather_level(to_state.state),
        )
        await async_publish(
            self.hass,
            self.pub_topic_pressure,
            to_state.attributes["pressure"],
        )

    async def update_entity(self, msg: ReceiveMessage, action: str) -> None:
        """Read only."""
