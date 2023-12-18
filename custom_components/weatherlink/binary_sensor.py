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
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator
from .const import CONF_API_VERSION, DOMAIN, ApiVersion, DataKey
from .pyweatherlink import WLData

_LOGGER = logging.getLogger(__name__)


@dataclass
class WLBinarySensorDescription(BinarySensorEntityDescription):
    """Class describing Weatherlink binarysensor entities."""

    tag: str | None = None
    exclude_api_ver: set = ()
    exclude_data_structure: set = ()


SENSOR_TYPES: Final[tuple[WLBinarySensorDescription, ...]] = (
    WLBinarySensorDescription(
        key="TransmitterBattery",
        tag=DataKey.TRANS_BATTERY_FLAG,
        device_class=BinarySensorDeviceClass.BATTERY,
        translation_key="trans_battery",
        entity_category=EntityCategory.DIAGNOSTIC,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(2,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = await get_coordinator(hass, config_entry)

    async_add_entities(
        WLSensor(coordinator, hass, config_entry, description, 1)
        for description in SENSOR_TYPES
        if (config_entry.data[CONF_API_VERSION] not in description.exclude_api_ver)
        and (
            coordinator.data[1].get(DataKey.DATA_STRUCTURE)
            not in description.exclude_data_structure
        )
    )


class WLSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Binary Sensor."""

    entity_description: WLBinarySensorDescription
    sensor_data = WLData()

    def __init__(
        self,
        coordinator,
        hass: HomeAssistant,
        entry: ConfigEntry,
        description: WLBinarySensorDescription,
        tx_id: int,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.entry: ConfigEntry = entry
        self.entity_description = description
        self.tx_id = tx_id
        self._attr_has_entity_name = True
        self._attr_unique_id = (
            f"{self.get_unique_id_base()}-{self.entity_description.key}"
        )
        via = (
            None
            if self.tx_id == 1
            else (
                DOMAIN,
                f"{self.get_unique_id_base()}-{1}",
            )
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.get_unique_id_base()}-{self.tx_id}")},
            name=self.generate_name(),
            manufacturer="Davis",
            model=self.generate_model(),
            configuration_url="https://www.weatherlink.com/",
            via_device=via,
        )

    def get_unique_id_base(self):
        """Generate base for unique_id."""
        unique_base = None
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            unique_base = self.coordinator.data[self.tx_id]["DID"]
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            unique_base = self.coordinator.data[DataKey.UUID]
        return unique_base

    def generate_name(self):
        """Generate device name."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            return self.coordinator.data["station_name"]
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            return self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0]["station_name"]

        return "Unknown devicename"

    def generate_model(self):
        """Generate model string."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            return "Weatherlink - API V1"
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            model = self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0].get("product_number")
            return f"Weatherlink {model}"
        return "Weatherlink"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        # _LOGGER.debug("Key: %s", self.entity_description.key)
        return self.coordinator.data[self.tx_id].get(self.entity_description.tag)
