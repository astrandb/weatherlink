"""Platform for binary sensor integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import WLConfigEntry, get_coordinator
from .const import CONF_API_VERSION, DISCONNECTED_AFTER_SECONDS, ApiVersion, DataKey
from .entity import WLEntity
from .pyweatherlink import WLData

_LOGGER = logging.getLogger(__name__)


@dataclass
class WLBinarySensorDescription(BinarySensorEntityDescription):
    """Class describing Weatherlink binarysensor entities."""

    tag: str | None = None
    exclude_api_ver: set = ()
    exclude_data_structure: set = ()
    aux_sensors: set = ()


SENSOR_TYPES: Final[tuple[WLBinarySensorDescription, ...]] = (
    WLBinarySensorDescription(
        key="TransmitterBattery",
        tag=DataKey.TRANS_BATTERY_FLAG,
        device_class=BinarySensorDeviceClass.BATTERY,
        translation_key="trans_battery",
        entity_category=EntityCategory.DIAGNOSTIC,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(2, 12, 16, 18),
        aux_sensors=(55, 56),
    ),
    WLBinarySensorDescription(
        key="Timestamp",
        tag=DataKey.TIMESTAMP,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        translation_key="timestamp",
        entity_category=EntityCategory.DIAGNOSTIC,
        # exclude_api_ver=(ApiVersion.API_V1,),
        # exclude_data_structure=(2,),
        aux_sensors=(55, 56, 323, 326),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WLConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = await get_coordinator(hass, entry)
    primary_tx_id = entry.runtime_data.primary_tx_id

    entities = [
        WLBinarySensor(coordinator, hass, entry, description, primary_tx_id)
        for description in SENSOR_TYPES
        if (entry.data[CONF_API_VERSION] not in description.exclude_api_ver)
        and (
            coordinator.data[primary_tx_id].get(DataKey.DATA_STRUCTURE)
            not in description.exclude_data_structure
        )
        and (coordinator.data[primary_tx_id].get(description.tag) is not None)
    ]

    aux_entities = []
    if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        for sensor in entry.runtime_data.sensors_metadata:
            if sensor["tx_id"] is not None and sensor["tx_id"] != primary_tx_id:
                aux_entities += [
                    WLBinarySensor(
                        coordinator,
                        hass,
                        entry,
                        description,
                        sensor["tx_id"],
                    )
                    for description in SENSOR_TYPES
                    if sensor["sensor_type"] in description.aux_sensors
                    and coordinator.data[sensor["tx_id"]].get(DataKey.DATA_STRUCTURE)
                    not in description.exclude_data_structure
                ]
            if sensor["tx_id"] is None:
                aux_entities += [
                    WLBinarySensor(
                        coordinator,
                        hass,
                        entry,
                        description,
                        sensor["lsid"],
                    )
                    for description in SENSOR_TYPES
                    if sensor["sensor_type"] in description.aux_sensors
                    and (
                        coordinator.data[sensor["lsid"]].get(description.tag)
                        is not None
                    )
                ]
    async_add_entities(entities + aux_entities)


class WLBinarySensor(WLEntity, BinarySensorEntity):
    """Representation of a Binary Sensor."""

    entity_description: WLBinarySensorDescription
    sensor_data = WLData()

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if self.entity_description.key == "TransmitterBattery":
            return self.coordinator.data[self.tx_id].get(self.entity_description.tag)
        if self.entity_description.key == "Timestamp":
            dt_update = dt_util.utc_from_timestamp(
                self.coordinator.data[self.tx_id].get(DataKey.TIMESTAMP)
            )
            dt_now = dt_util.now()
            diff = dt_now - dt_update
            return diff.total_seconds() < DISCONNECTED_AFTER_SECONDS
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes, if any."""
        if self.entity_description.key in [
            "Timestamp",
        ]:
            if self.coordinator.data[self.tx_id].get(DataKey.TIMESTAMP) is None:
                return None
            dt_object = dt_util.utc_from_timestamp(
                self.coordinator.data[self.tx_id].get(DataKey.TIMESTAMP)
            )
            return {
                "last_update": dt_object,
            }
        return None
