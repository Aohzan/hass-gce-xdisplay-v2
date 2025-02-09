"""Constants for the GCE XDisplay v2 integration."""

from enum import Enum

from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.weather.const import DOMAIN as WEATHER_DOMAIN

DOMAIN = "gce_xdisplay_v2"

CONF_PREFIX_TOPIC = "topic_prefix"
CONF_SCREENS = "screens"
CONF_SCREEN_TYPE_NAME = "screen_type_name"
CONF_SCREEN_TYPE_ID = "screen_type_id"
CONF_SCREEN_ID = "screen_id"
CONF_SCREEN_LINKED_ENTITY = "linked_entity"

MAX_SCREEN_COUNT = 16


class XDisplayScreenTypes(Enum):
    """Screen types for the X-Display."""

    THERMOSTAT = 0
    BUTTON = 1
    HOME = 2
    COVER = 3
    NIGHT_LIGHT = 5
    TEMPERATURE = 6
    HUMIDITY = 7
    LUMINOSITY = 8
    FOUR_BUTTONS = 9
    SLIDER = 10
    PLAYER = 11
    KEYBOARD = 12
    XPOOL = 13
    WEATHER = 14
    CONSUMPTION = 15
    ENERGY = 16


XDISPLAY_SCREEN_TYPE_DOMAINS = {
    XDisplayScreenTypes.THERMOSTAT.name: [CLIMATE_DOMAIN],
    XDisplayScreenTypes.BUTTON.name: [SWITCH_DOMAIN, LIGHT_DOMAIN],
    XDisplayScreenTypes.HOME.name: [],
    XDisplayScreenTypes.COVER.name: [COVER_DOMAIN],
    XDisplayScreenTypes.NIGHT_LIGHT.name: [],
    XDisplayScreenTypes.TEMPERATURE.name: [SENSOR_DOMAIN],
    XDisplayScreenTypes.HUMIDITY.name: [SENSOR_DOMAIN],
    XDisplayScreenTypes.LUMINOSITY.name: [SENSOR_DOMAIN],
    XDisplayScreenTypes.FOUR_BUTTONS.name: [SWITCH_DOMAIN, LIGHT_DOMAIN],
    XDisplayScreenTypes.SLIDER.name: [LIGHT_DOMAIN],
    XDisplayScreenTypes.PLAYER.name: [MEDIA_PLAYER_DOMAIN],
    XDisplayScreenTypes.KEYBOARD.name: [],
    XDisplayScreenTypes.XPOOL.name: [],
    XDisplayScreenTypes.WEATHER.name: [WEATHER_DOMAIN],
    XDisplayScreenTypes.CONSUMPTION.name: [],
    XDisplayScreenTypes.ENERGY.name: [],
}

XDISPLAY_SCREEN_TYPE_DEVICE_CLASSES = {
    XDisplayScreenTypes.TEMPERATURE.name: ["temperature"],
    XDisplayScreenTypes.HUMIDITY.name: ["humidity"],
    XDisplayScreenTypes.LUMINOSITY.name: ["illuminance"],
}
