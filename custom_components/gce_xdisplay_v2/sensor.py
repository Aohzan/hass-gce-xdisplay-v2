"""Support for DSMR Reader through MQTT."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME, EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_PREFIX_TOPIC,
    CONF_SCREEN_LINKED_ENTITY,
    CONF_SCREEN_TYPE_NAME,
    CONF_SCREENS,
    DOMAIN,
)
from .definitions import SENSORS, XdisplaySensorEntityDescription
from .entity import XdisplayEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType


async def async_setup_entry(
    _: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Display sensors from config entry."""
    async_add_entities(
        XdisplaySensor(description, config_entry) for description in SENSORS
    )
    async_add_entities(
        XDisplaySyncDiagSensorEntity(config_entry, screen_id, screen_config)
        for screen_id, screen_config in enumerate(config_entry.data[CONF_SCREENS])
    )


class XdisplaySensor(XdisplayEntity, SensorEntity):
    """Representation of a X-Display sensor that is updated via MQTT."""

    entity_description: XdisplaySensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        if self._mqtt_value is None:
            return None
        return float(self._mqtt_value)


class XDisplaySyncDiagSensorEntity(SensorEntity):
    """Representation of a X-Display sensor that is updated via MQTT."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    _attr_icon = "mdi:monitor-dashboard"

    def __init__(
        self,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict,
    ) -> None:
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._screen_id = screen_id
        self._screen_config = screen_config
        screen_display_name = screen_config.get(
            CONF_NAME, str(screen_config[CONF_SCREEN_TYPE_NAME]).capitalize()
        )
        self._attr_name = f"Screen #{screen_id} {screen_display_name}"
        self._attr_native_value = self._screen_config[CONF_SCREEN_LINKED_ENTITY]
        self._attr_extra_state_attributes = {
            "name": screen_config.get(CONF_NAME, ""),
            "type": screen_config[CONF_SCREEN_TYPE_NAME],
        }
        self._attr_unique_id = f"{config_entry.entry_id}-screen-{screen_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, config_entry.data[CONF_PREFIX_TOPIC]),
            },
            name=config_entry.title,
            manufacturer="GCE Electronics",
            model="X-Display V2",
            serial_number=config_entry.data[CONF_DEVICE_ID],
        )
