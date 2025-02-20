"""Sync between entities and X-Display screens."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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
        if (to_state := event.data["new_state"]) is None or to_state.state in [
            "unavailable",
            "unknown",
        ]:
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
