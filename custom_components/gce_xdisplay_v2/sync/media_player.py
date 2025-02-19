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
        if (to_state := event.data["new_state"]) is None or to_state.state in [
            "unavailable",
            "unknown",
        ]:
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
