"""Sync between entities and X-Display screens."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

import pytz
from homeassistant.components.energy.data import (
    EnergyManager,
    EnergyPreferences,
    async_get_manager,
)
from homeassistant.components.mqtt.client import async_publish
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.recorder import get_instance

from . import XDisplaySync

if TYPE_CHECKING:
    from homeassistant.components.mqtt.models import ReceiveMessage
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

_LOGGER = logging.getLogger(__name__)


class XDisplayEnergySync(XDisplaySync):
    """Sync between entity and X-Display energy distribution screen."""

    energy_manager: EnergyManager | None

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        screen_id: int,
        screen_config: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, config_entry, screen_id, screen_config)
        self.pub_topic_consumption = f"{self.topic_prefix}/Consommation"
        self.pub_topic_production = f"{self.topic_prefix}/Production"
        self.pub_topic_charge = f"{self.topic_prefix}/Charge"
        self.pub_topic_discharge = f"{self.topic_prefix}/Discharge"
        self.pub_topic_soutire = f"{self.topic_prefix}/Soutire"
        self.pub_topic_injecte = f"{self.topic_prefix}/Injecte"

        self.entities: list[str] = []
        self.entity_ids_consumption: list[str] = []
        self.entity_id_production: str | None = None
        self.entity_id_charge: str | None = None
        self.entity_id_discharge: str | None = None
        self.entity_id_soutire: str | None = None
        self.entity_id_injecte: str | None = None

    async def initialize(self) -> None:
        """Get energy manager."""
        _LOGGER.debug("Initialize energy distribution data")
        self.energy_manager = await async_get_manager(self.hass)
        self.energy_manager.async_listen_updates(self.update_xdisplay)

        if not self.energy_manager.data:
            _LOGGER.debug("No energy data available")
        else:
            self._process_energy_sources(self.energy_manager.data)
            self._extend_entities()
            await self.update_xdisplay()

    def _process_energy_sources(self, energy_preferences: EnergyPreferences) -> None:
        """Process energy sources."""
        for energy in energy_preferences["energy_sources"]:
            if energy["type"] == "grid":
                self.entity_ids_consumption = [
                    stat_id["stat_energy_from"] for stat_id in energy["flow_from"]
                ]
            elif energy["type"] == "solar":
                self.entity_id_production = energy["stat_energy_from"]
            elif energy["type"] == "battery":
                self.entity_id_charge = energy["stat_energy_to"]
                self.entity_id_discharge = energy["stat_energy_from"]
            else:
                _LOGGER.debug("Energy type %s not compatible", energy["type"])

    def _extend_entities(self) -> None:
        """Extend entities list."""
        if self.entity_ids_consumption:
            self.entities.extend(self.entity_ids_consumption)
        if self.entity_id_production:
            self.entities.append(self.entity_id_production)
        if self.entity_id_charge:
            self.entities.append(self.entity_id_charge)
        if self.entity_id_discharge:
            self.entities.append(self.entity_id_discharge)
        if self.entity_id_soutire:
            self.entities.append(self.entity_id_soutire)
        if self.entity_id_injecte:
            self.entities.append(self.entity_id_injecte)

    async def update_xdisplay(self) -> None:
        """Publish updated MQTT state from entity watched."""
        _LOGGER.debug("Update energy distribution data")
        if self.entities:
            stats = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period,
                self.hass,
                datetime.datetime.combine(
                    datetime.datetime.now(
                        tz=pytz.timezone(self.hass.config.time_zone)
                    ).date(),
                    datetime.time.min,
                ),
                None,
                self.entities,
                "day",
                None,
                {"change"},
            )
            for entity_id, stat in stats.items():
                if "change" not in stat[-1]:
                    _LOGGER.debug("No stat for %s", entity_id)
                    continue
                value = stat[-1]["change"]
                if (
                    self.entity_ids_consumption
                    and entity_id in self.entity_ids_consumption
                ):
                    _LOGGER.debug("Publishing consumption: %s", value)
                    await async_publish(
                        self.hass,
                        self.pub_topic_consumption,
                        value,
                        retain=True,
                    )
                elif entity_id == self.entity_id_production:
                    _LOGGER.debug("Publishing production: %s", value)
                    await async_publish(
                        self.hass,
                        self.pub_topic_production,
                        value,
                        retain=True,
                    )
                elif entity_id == self.entity_id_charge:
                    _LOGGER.debug("Publishing charge: %s", value)
                    await async_publish(
                        self.hass,
                        self.pub_topic_charge,
                        value,
                        retain=True,
                    )
                elif entity_id == self.entity_id_discharge:
                    _LOGGER.debug("Publishing discharge: %s", value)
                    await async_publish(
                        self.hass,
                        self.pub_topic_discharge,
                        value,
                        retain=True,
                    )
                elif entity_id == self.entity_id_soutire:
                    _LOGGER.debug("Publishing soutire: %s", value)
                    await async_publish(
                        self.hass,
                        self.pub_topic_soutire,
                        value,
                        retain=True,
                    )
                elif entity_id == self.entity_id_injecte:
                    _LOGGER.debug("Publishing injecte: %s", value)
                    await async_publish(
                        self.hass,
                        self.pub_topic_injecte,
                        value,
                        retain=True,
                    )

    async def update_entity(self, msg: ReceiveMessage) -> None:
        """Update the entity."""
