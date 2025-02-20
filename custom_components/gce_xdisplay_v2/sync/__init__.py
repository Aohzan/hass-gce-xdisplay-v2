"""Sync entities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.gce_xdisplay_v2.const import (
    CONF_PREFIX_TOPIC,
)

if TYPE_CHECKING:
    from homeassistant.components.mqtt.models import ReceiveMessage
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, EventStateChangedData, HomeAssistant

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]


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
