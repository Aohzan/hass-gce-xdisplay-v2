"""Sync entities."""

from __future__ import annotations

import datetime
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import pytz
from homeassistant.components.climate.const import HVACAction, HVACMode
from homeassistant.components.energy.data import (
    EnergyManager,
    EnergyPreferences,
    async_get_manager,
)
from homeassistant.components.mqtt.client import async_publish
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)
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
from homeassistant.helpers.recorder import get_instance

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
