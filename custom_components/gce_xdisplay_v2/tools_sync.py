"""Sync between entities and X-Display screens."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from homeassistant.components.mqtt.client import async_publish
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
        suffix_pub: str,
        suffix_sub: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)

        self.topic_sub = f"{self.topic_prefix}/{suffix_sub}"
        self.topic_pub = f"{self.topic_prefix}/{suffix_pub}"

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity (%s) has changed: %s",
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
            "switch",
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
        self.sub_topic_turned_on = f"{self.topic_prefix}/ThCmdReply"

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None:
            return
        _LOGGER.debug(
            "Watched entity (%s) has changed: %s %s",
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
            1 if to_state.attributes["hvac_action"] == "heating" else 0,
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
        _LOGGER.debug("Action on XDisplay screen #%s: %s", self.screen_id, msg.payload)
        if action == "set_temperature":
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY],
                    "temperature": float(msg.payload),
                },
            )
        elif action == "set_hvac_mode":
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": self.screen_config[CONF_SCREEN_LINKED_ENTITY],
                    "hvac_mode": "heat" if msg.payload == "1" else "off",
                },
            )
