"""Sync between entities and X-Display screens."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.climate.const import HVACAction, HVACMode
from homeassistant.components.mqtt.client import async_publish
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
        # Not used, return the confirmation of the command
        self.sub_topic_target_temp_reply = f"{self.topic_prefix}/ThCmdReply"

        async_track_state_change_event(
            hass, [screen_config[CONF_SCREEN_LINKED_ENTITY]], self.update_xdisplay
        )

    async def update_xdisplay(self, event: Event[EventStateChangedData]) -> None:
        """Publish updated MQTT state from entity watched."""
        if (to_state := event.data["new_state"]) is None or to_state.state in [
            "unavailable",
            "unknown",
        ]:
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
