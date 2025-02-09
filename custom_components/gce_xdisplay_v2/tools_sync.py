"""Sync between entities and X-Display screens."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from homeassistant.components.climate.const import HVACAction, HVACMode
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
    CONF_PREFIX_TOPIC,
    CONF_SCREEN_LINKED_ENTITY,
)

if TYPE_CHECKING:
    from homeassistant.components.mqtt.models import ReceiveMessage
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, EventStateChangedData, HomeAssistant

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

_LOGGER = logging.getLogger(__name__)


class XDisplaySync(ABC):
    """Sync between entity and X-Display Screen."""

    hass: HomeAssistant
    config_entry: ConfigEntry
    screen_id: int
    screen_config: dict[str, Any]

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        self.hass = hass
        self.config_entry = config_entry
        self.screen_id = screen_id
        self.screen_config = screen_config

        self.topic_prefix = (
            self.config_entry.data[CONF_PREFIX_TOPIC] + "/" + str(screen_id)
        )

    @abstractmethod
    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Update X-Display screen from entity watched."""

    @abstractmethod
    async def update_entity(self, msg: ReceiveMessage) -> None:
        """Update linked entity from X-Display action."""


class XDisplayButtonSync(XDisplaySync):
    """Sync between entity and X-Display button screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)

        self.topic_sub = f"{self.topic_prefix}/IoState"
        self.topic_pub = f"{self.topic_prefix}/IoCmd"
        self.linked_entity_domain = screen_config[CONF_SCREEN_LINKED_ENTITY].split(".")[
            0
        ]

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity %s has changed: %s",
            event.data["entity_id"],
            to_state.state,
        )
        await async_publish(
            self.hass,
            self.topic_pub,
            1 if to_state.state == "on" else 0,
        )

    async def update_entity(self, msg: ReceiveMessage) -> None:
        """Update the entity."""
        _LOGGER.debug("Action on XDisplay screen #%s: %s", self.screen_id, msg.payload)
        await self.hass.services.async_call(
            self.linked_entity_domain,
            "turn_on" if msg.payload == "1" else "turn_off",
            {"entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY]},
        )


class XDisplayThermostatSync(XDisplaySync):
    """Sync between entity and X-Display thermostat screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)

        self.sub_topic_target_temp = f"{self.topic_prefix}/ThState"
        self.pub_topic_target_temp = f"{self.topic_prefix}/ThCmd"
        self.sub_topic_measure_temp = f"{self.topic_prefix}/ThMeasureState"
        self.pub_topic_measure_temp = f"{self.topic_prefix}/ThMeasureCmd"
        self.pub_topic_turned_on = f"{self.topic_prefix}/ThermoOnOff"
        self.pub_topic_heating = f"{self.topic_prefix}/ThermoOutput"
        self.sub_topic_turned_on = f"{self.topic_prefix}/IoState"
        self.sub_topic_target_temp_reply = f"{self.topic_prefix}/ThCmdReply"  # Not used, return the confirmation of the command

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity %s has changed to %s (attributes: %s)",
            event.data["entity_id"],
            to_state.state,
            to_state.attributes,
        )
        await async_publish(
            self.hass,
            self.pub_topic_turned_on,
            1 if to_state.state == "heat" else 0,
        )
        await async_publish(
            self.hass,
            self.pub_topic_heating,
            1 if to_state.attributes["hvac_action"] == HVACAction.HEATING else 0,
        )
        await async_publish(
            self.hass,
            self.pub_topic_target_temp,
            to_state.attributes["temperature"],
        )
        await async_publish(
            self.hass,
            self.pub_topic_measure_temp,
            to_state.attributes["current_temperature"],
        )

    async def update_entity(self, msg: ReceiveMessage, action: str) -> None:
        """Update the entity."""
        _LOGGER.debug(
            "XDisplay published for screen #%s:\ntopic: %s\npayload: %s",
            self.screen_id,
            msg.topic,
            msg.payload,
        )
        if action == "set_temperature":
            _LOGGER.debug("Setting temperature to %s", msg.payload)
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY],
                    "temperature": float(msg.payload),
                },
            )
        elif action == "set_hvac_mode":
            if msg.payload not in ("0", "1"):
                _LOGGER.error("Invalid payload for HVAC mode: %s", msg.payload)
                return
            _LOGGER.debug("Setting HVAC mode to %s", msg.payload)
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY],
                    "hvac_mode": HVACMode.HEAT if msg.payload == "1" else HVACMode.OFF,
                },
            )


class XDisplayCoverSync(XDisplaySync):
    """Sync between entity and X-Display cover screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)

        self.sub_topic_position = f"{self.topic_prefix}/ShutterPos"
        self.pub_topic_cmd = f"{self.topic_prefix}/ShutterCmd"

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity %s has changed: %s",
            event.data["entity_id"],
            to_state.state,
        )
        await async_publish(
            self.hass,
            self.pub_topic_cmd,
            2 if to_state.state == "open" else 1,
        )

    async def update_entity(self, msg: ReceiveMessage) -> None:
        """Update the entity."""
        _LOGGER.debug(
            "XDisplay published for screen #%s:\ntopic: %s\npayload: %s",
            self.screen_id,
            msg.topic,
            msg.payload,
        )
        await self.hass.services.async_call(
            "cover",
            "open_cover" if msg.payload == "1" else "close_cover",
            {"entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY]},
        )


class XDisplaySensorSync(XDisplaySync):
    """Sync between entity and X-Display sensor screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict[str, Any],
        sensor_type: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)

        if sensor_type not in ["temp", "hum", "lum"]:
            raise ValueError("Invalid sensor type")  # noqa: EM101, TRY003

        self.pub_topic_cmd = f"{self.topic_prefix}/{sensor_type}Cmd"

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity %s has changed: %s",
            event.data["entity_id"],
            to_state.state,
        )
        await async_publish(
            self.hass,
            self.pub_topic_cmd,
            to_state.state,
        )

    async def update_entity(self, msg: ReceiveMessage, action: str) -> None:
        """Read only."""


class XDisplayMediaPlayerSync(XDisplaySync):
    """Sync between entity and X-Display media player screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)

        # Subscribe topics
        self.sub_topic_vol_up = f"{self.topic_prefix}/PlayerUpVolState"
        self.sub_topic_vol_down = f"{self.topic_prefix}/PlayerDownVolState"
        self.sub_topic_mute = f"{self.topic_prefix}/PlayerMuteState"
        self.sub_topic_pause = f"{self.topic_prefix}/PlayerPauseState"
        self.sub_topic_next = f"{self.topic_prefix}/PlayerNextState"
        self.sub_topic_prev = f"{self.topic_prefix}/PlayerPrevState"
        self.sub_topic_random = f"{self.topic_prefix}/PlayerRandomState"
        self.sub_topic_loop = f"{self.topic_prefix}/PlayerLoopState"
        # Publish topics
        self.pub_topic_vol_up = f"{self.topic_prefix}/PlayerUpVolCmd"
        self.pub_topic_vol_down = f"{self.topic_prefix}/PlayerDownVolCmd"
        self.pub_topic_mute = f"{self.topic_prefix}/PlayerMuteCmd"
        self.pub_topic_pause = f"{self.topic_prefix}/PlayerPauseCmd"
        self.pub_topic_next = f"{self.topic_prefix}/PlayerNextCmd"
        self.pub_topic_random = f"{self.topic_prefix}/PlayerRandomCmd"
        self.pub_topic_loop = f"{self.topic_prefix}/PlayerLoopCmd"

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity %s has changed: %s (attributes %s)",
            event.data["entity_id"],
            to_state.state,
            to_state.attributes,
        )
        await async_publish(
            self.hass,
            self.pub_topic_pause,
            0 if to_state.state == "playing" else 1,
        )
        await async_publish(
            self.hass,
            self.pub_topic_mute,
            1 if to_state.attributes.get("is_volume_muted") else 0,
        )
        await async_publish(
            self.hass,
            self.pub_topic_loop,
            1
            if to_state.attributes.get("repeat") == "one"
            else 2
            if to_state.attributes.get("repeat") == "all"
            else 0,
        )
        await async_publish(
            self.hass,
            self.pub_topic_random,
            1 if to_state.attributes.get("shuffle") else 0,
        )

    async def update_entity(self, msg: ReceiveMessage, action: str) -> None:
        """Update the entity."""
        _LOGGER.debug(
            "XDisplay published for screen #%s:\ntopic: %s\npayload: %s",
            self.screen_id,
            msg.topic,
            msg.payload,
        )
        if (
            action
            in [
                "volume_up",
                "volume_down",
                "volume_mute",
                "media_next_track",
                "media_previous_track",
            ]
            and msg.payload == "1"
        ):
            await self.hass.services.async_call(
                "media_player",
                action,
                {"entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY]},
            )
        elif action == "media_play_pause":
            await self.hass.services.async_call(
                "media_player",
                "media_pause" if msg.payload == "1" else "media_play",
                {"entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY]},
            )
        elif action == "repeat_set":
            await self.hass.services.async_call(
                "media_player",
                "repeat_set",
                {
                    "entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY],
                    "repeat": "one" if msg.payload == "1" else "off",
                },
            )
        elif action == "shuffle_set":
            await self.hass.services.async_call(
                "media_player",
                "shuffle_set",
                {
                    "entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY],
                    "shuffle": msg.payload == "1",
                },
            )


class XDisplayWeatherSync(XDisplaySync):
    """Sync between entity and X-Display weather screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry[Any],
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        super().__init__(hass, config_entry, screen_id, screen_config)

        self.pub_topic_hum = f"{self.topic_prefix}/Wthum"
        self.pub_topic_temp = f"{self.topic_prefix}/Whtemp"
        self.pub_topic_wind = f"{self.topic_prefix}/Whwind"
        self.pub_topic_level = f"{self.topic_prefix}/WhLevel"  # Data : 0 (soleil), 1(éclaircie), 2(nuage), 3(brouillard), 4(pluie), 5(orage), 6(neige)
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
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity %s has changed: %s (attributes %s)",
            event.data["entity_id"],
            to_state.state,
            to_state.attributes,
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
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_sunrise,
        #     to_state.attributes["sunrise"],
        # )
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_sunset,
        #     to_state.attributes["sunset"],
        # )
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_temp_d1,
        #     to_state.attributes["forecast_temp_day_1"],
        # )
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_level_d1,
        #     0,
        # )
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_temp_d2,
        #     to_state.attributes["forecast_temp_day_2"],
        # )
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_level_d2,
        #     0,
        # )
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_temp_d3,
        #     to_state.attributes["forecast_temp_day_3"],
        # )
        # await async_publish(
        #     self.hass,
        #     self.pub_topic_level_d3,
        #     0,
        # )

    async def update_entity(self, msg: ReceiveMessage, action: str) -> None:
        """Read only."""
