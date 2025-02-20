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
            self.pub_topic_cmd,
            to_state.state,
        )

    async def update_entity(self, msg: ReceiveMessage, action: str) -> None:
        """Read only."""
