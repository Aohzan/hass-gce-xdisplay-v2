"""Support for X-Display number through MQTT."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.mqtt.client import async_publish
from homeassistant.components.number import NumberEntity

from custom_components.gce_xdisplay_v2.entity import XdisplayEntity

from .definitions import NUMBERS, XdisplayNumberEntityDescription

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    _: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Display numberes from config entry."""
    async_add_entities(
        XdisplayNumber(description, config_entry) for description in NUMBERS
    )


class XdisplayNumber(XdisplayEntity, NumberEntity):
    """Representation of a X-Display number that is updated via MQTT."""

    entity_description: XdisplayNumberEntityDescription

    @property
    def value(self) -> int | None:
        """Return the entity value to represent the entity state."""
        return self._mqtt_value

    async def async_set_value(self, value: int) -> None:
        """Set new value."""
        await async_publish(
            self.hass,
            self._mqtt_topic,
            value,
            self.entity_description.qos,
            retain=True,
        )
