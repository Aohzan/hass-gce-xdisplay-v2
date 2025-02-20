"""Support for X-Display switch through MQTT."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.mqtt.client import async_publish
from homeassistant.components.switch import SwitchEntity

from custom_components.gce_xdisplay_v2.entity import XdisplayEntity

from .definitions import SWITCHES, XdisplaySwitchEntityDescription

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    _: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Display switches from config entry."""
    async_add_entities(
        XdisplaySwitch(description, config_entry) for description in SWITCHES
    )


class XdisplaySwitch(XdisplayEntity, SwitchEntity):
    """Representation of a X-Display switch that is updated via MQTT."""

    entity_description: XdisplaySwitchEntityDescription

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""
        return self._mqtt_value == self.entity_description.payload_on

    async def async_turn_on(self) -> None:
        """Turn the device on."""
        await async_publish(
            self.hass,
            self._mqtt_topic,
            self.entity_description.payload_on,
            self.entity_description.qos,
            self.entity_description.retain,
        )

    async def async_turn_off(self) -> None:
        """Turn the device off."""
        await async_publish(
            self.hass,
            self._mqtt_topic,
            self.entity_description.payload_off,
            self.entity_description.qos,
            self.entity_description.retain,
        )
