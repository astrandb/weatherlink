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
from .const import (
    CONF_API_VERSION,
    CONFIG_URL,
    DOMAIN,
    MANUFACTURER,
    ApiVersion,
    DataKey,
)
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
        exclude_data_structure=(2,),
        aux_sensors=(55,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = await get_coordinator(hass, config_entry)

    entities = [
        WLSensor(coordinator, hass, config_entry, description, 1)
        for description in SENSOR_TYPES
        if (config_entry.data[CONF_API_VERSION] not in description.exclude_api_ver)
        and (
            coordinator.data.get(DataKey.DATA_STRUCTURE)
            not in description.exclude_data_structure
        )
    ]

    aux_entities = []
    if config_entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        for sensor in hass.data[DOMAIN][config_entry.entry_id]["sensors_metadata"]:
            if sensor["tx_id"] is not None and sensor["tx_id"] > 1:
                aux_entities = [
                    WLSensor(
                        coordinator, hass, config_entry, description, sensor["tx_id"]
                    )
                    for description in SENSOR_TYPES
                    if (sensor["sensor_type"] in description.aux_sensors)
                ]

    async_add_entities(entities + aux_entities)


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
        tx_id_part = f"-{self.tx_id}" if self.tx_id > 1 else ""
        self._attr_unique_id = (
            f"{self.get_unique_id_base()}{tx_id_part}-{self.entity_description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.get_unique_id_base()}{tx_id_part}")},
            name=self.generate_name(),
            manufacturer=MANUFACTURER,
            model=self.generate_model(),
            sw_version=self.get_firmware(),
            serial_number=self.get_serial(),
            configuration_url=CONFIG_URL,
            via_device=(DOMAIN, self.get_unique_id_base())
            if tx_id_part != ""
            else None,
        )

    def get_unique_id_base(self):
        """Generate base for unique_id."""
        unique_base = None
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            unique_base = self.coordinator.data["DID"]
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            unique_base = self.coordinator.data[DataKey.UUID]
        return unique_base

    def get_firmware(self) -> str | None:
        """Get firmware version."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            return self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0].get("firmware_version")
        return None

    def get_serial(self) -> str | None:
        """Get serial number."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            return self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0].get("gateway_id_hex")
        return None

    def generate_name(self):
        """Generate device name."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            return self.coordinator.data["station_name"]
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            if self.tx_id == 1:
                return self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                    "stations"
                ][0]["station_name"]
            for sensor in self.hass.data[DOMAIN][self.entry.entry_id][
                "sensors_metadata"
            ]:
                if sensor["sensor_type"] in (55, 56) and sensor["tx_id"] == self.tx_id:
                    return f"{sensor['product_name']} ID{sensor['tx_id']}"

        return "Unknown devicename"

    def generate_model(self):
        """Generate model string."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            return "WeatherLink - API V1"
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            model: str = self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0].get("product_number")
        if model == "6555":
            return f"WeatherLinkIP {model}"
        if model.startswith("6100"):
            return f"WeatherLink Live {model}"
        if model.startswith("6313"):
            return f"WeatherLink Console {model}"
        return "WeatherLink"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        # _LOGGER.debug("Key: %s", self.entity_description.key)
        return self.coordinator.data[self.tx_id].get(self.entity_description.tag)
