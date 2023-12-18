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
        WLSensor(coordinator, hass, config_entry, description)
        for description in SENSOR_TYPES
        if (config_entry.data[CONF_API_VERSION] not in description.exclude_api_ver)
        and (
            coordinator.data[DataKey.DATA_STRUCTURE]
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
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.entry: ConfigEntry = entry
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = (
            f"{self.get_unique_id_base()}-{self.entity_description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.get_unique_id_base())},
            name=self.generate_name(),
            manufacturer=MANUFACTURER,
            model=self.generate_model(),
            sw_version=self.get_firmware(),
            serial_number=self.get_serial(),
            configuration_url=CONFIG_URL,
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
            return self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0]["station_name"]

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
        return self.coordinator.data.get(self.entity_description.tag)
