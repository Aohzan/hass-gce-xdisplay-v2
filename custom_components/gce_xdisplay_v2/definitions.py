"""Entities for GCE X-Display V2 integration."""

from dataclasses import dataclass

from homeassistant.components.number import NumberEntityDescription, NumberMode
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.helpers.entity import EntityDescription


@dataclass(frozen=True)
# pylint: disable-next=hass-enforce-class-module
class XdisplayEntityDescription(EntityDescription):
    """Entity description for X-Display V2."""

    qos: int = 0
    retain: bool = True


@dataclass(frozen=True)
# pylint: disable-next=hass-enforce-class-module
class XdisplaySensorEntityDescription(
    XdisplayEntityDescription, SensorEntityDescription
):
    """Entity description for X-Display V2 sensors."""


@dataclass(frozen=True)
# pylint: disable-next=hass-enforce-class-module
class XdisplaySwitchEntityDescription(
    XdisplayEntityDescription, SwitchEntityDescription
):
    """Entity description for X-Display V2 switch."""

    payload_on: str = "1"
    payload_off: str = "0"


@dataclass(frozen=True)
# pylint: disable-next=hass-enforce-class-module
class XdisplayNumberEntityDescription(
    XdisplayEntityDescription, NumberEntityDescription
):
    """Entity description for X-Display V2 number."""


SENSORS: tuple[XdisplaySensorEntityDescription, ...] = (
    XdisplaySensorEntityDescription(
        key="temp",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

SWITCHES: tuple[XdisplaySwitchEntityDescription, ...] = (
    XdisplaySwitchEntityDescription(
        key="screenoff",
        name="Screen",
        payload_on="0",
        payload_off="1",
        icon="mdi:monitor",
    ),
    XdisplaySwitchEntityDescription(
        key="verr",
        name="Lock Screen",
        payload_on="1",
        payload_off="0",
        icon="mdi:lock",
    ),
)

NUMBERS: tuple[XdisplayNumberEntityDescription, ...] = (
    XdisplayNumberEntityDescription(
        key="AutoOff",
        name="Auto Off",
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        icon="mdi:power-sleep",
        native_unit_of_measurement="min",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
    ),
)
