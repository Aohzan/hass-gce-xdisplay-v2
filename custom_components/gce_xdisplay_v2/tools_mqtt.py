"""Tools for GCE XDisplay V2 integration."""

from homeassistant.components.mqtt.client import async_publish
from homeassistant.core import HomeAssistant

from custom_components.gce_xdisplay_v2.const import XDisplayScreenTypes


async def xdisplay_mqtt_add_screen(
    hass: HomeAssistant,
    prefix_topic: str,
    screen_type: XDisplayScreenTypes,
) -> None:
    """Create a new screen."""
    await async_publish(hass, f"{prefix_topic}/new", screen_type.value, retain=False)


async def xdisplay_mqtt_delete_screen(
    hass: HomeAssistant, prefix_topic: str, screen_id: int
) -> None:
    """Delete a screen."""
    await async_publish(
        hass,
        f"{prefix_topic}/{screen_id}/delete",
        "",
    )


async def xdisplay_mqtt_update_screen_name(
    hass: HomeAssistant,
    prefix_topic: str,
    screen_id: int,
    screen_name: str,
) -> None:
    """Update a screen."""
    await async_publish(
        hass,
        f"{prefix_topic}/{screen_id}/updateName",
        screen_name,
    )
