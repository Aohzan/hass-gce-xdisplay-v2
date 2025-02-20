"""Support for DSMR Reader through MQTT."""

import logging

from homeassistant.components.mqtt.client import (
    async_subscribe,
)
from homeassistant.components.mqtt.models import (
    ReceiveMessage,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.util import slugify

from .const import CONF_PREFIX_TOPIC, DOMAIN
from .definitions import XdisplayEntityDescription

_LOGGER = logging.getLogger(__name__)


class XdisplayEntity(Entity):
    """Representation of a X-Display V2 entity that is updated via MQTT."""

    _attr_has_entity_name = True
    entity_description: XdisplayEntityDescription

    def __init__(
        self, description: XdisplayEntityDescription, config_entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description

        self._mqtt_topic = f"{config_entry.data[CONF_PREFIX_TOPIC]}/{description.key}"
        self._mqtt_value = None

        slug = slugify(description.key.replace("/", "_"))
        self._attr_unique_id = f"{config_entry.entry_id}-{slug}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, config_entry.data[CONF_PREFIX_TOPIC]),
            },
            name=config_entry.title,
            manufacturer="GCE Electronics",
            model="X-Display V2",
            serial_number=config_entry.data[CONF_DEVICE_ID],
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT events."""

        @callback
        def message_received(message: ReceiveMessage) -> None:
            """Handle new MQTT messages."""
            if message.payload == "":
                self._mqtt_value = None
            elif type(message.payload) is bytes or type(message.payload) is bytearray:
                self._mqtt_value = message.payload.decode("utf-8")
            else:
                self._mqtt_value = message.payload

            self.async_write_ha_state()

        try:
            await async_subscribe(self.hass, self._mqtt_topic, message_received, 1)
            _LOGGER.debug("Subscribed to %s", self._mqtt_topic)
        except HomeAssistantError:
            async_create_issue(
                self.hass,
                DOMAIN,
                f"cannot_subscribe_mqtt_topic_{self._mqtt_topic}",
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="cannot_subscribe_mqtt_topic",
                translation_placeholders={
                    "topic": self._mqtt_topic,
                    "topic_title": self._mqtt_topic.split("/")[-1],
                },
            )
