# Home-Assistant GCE X-Display V2 custom component

Sync X-Display's screens with Home-Assistant entities through MQTT.

Supported

- Button with switch or light entity
- Player with media_player entity
- Thermostat with climate entity

You can control the screen (on/off, lock, off delay) and get the temperature.

## Requirements

The X-Display must be connected to the same MQTT broker as Home-Assistant.

## Installation

### HACS

HACS > Integrations > Explore & Add Repositories > GCE X-Display V2 > Install this repository

### Manually

Copy `custom_components/gce_xdisplay_v2` in `config/custom_components` of your Home Assistant.

## Configuration

Add the integration `GCE X-Display V2` in the interface on `Configuration` > `Integration`. Put the MQTT prefix (example `x-display_1234AB`).

Once your X-Display added, you can add/edit/remove screens in the integration configuration.

/!\ You can only remove the last screen.
/!\ All screens must be managed by the integration, so you have to delete all those you made before.
