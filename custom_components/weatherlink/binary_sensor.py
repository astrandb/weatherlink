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
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import (
    SENSOR_TYPE_AIRLINK,
    SENSOR_TYPE_VUE_AND_VANTAGE_PRO,
    WLConfigEntry,
    get_coordinator,
)
from .const import (
    CONF_API_VERSION,
    CONFIG_URL,
    DISCONNECTED_AFTER_SECONDS,
    DOMAIN,
    MANUFACTURER,
    UNAVAILABLE_AFTER_SECONDS,
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
        WLSensor(coordinator, hass, entry, description, primary_tx_id)
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
                    WLSensor(
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
                    WLSensor(
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


class WLSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Binary Sensor."""

    entity_description: WLBinarySensorDescription
    sensor_data = WLData()

    def __init__(
        self,
        coordinator,
        hass: HomeAssistant,
        entry: WLConfigEntry,
        description: WLBinarySensorDescription,
        tx_id: int,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self.entity_description = description
        self.tx_id = tx_id
        self.primary_tx_id = entry.runtime_data.primary_tx_id
        self._attr_has_entity_name = True
        tx_id_part = f"-{self.tx_id}" if self.tx_id != self.primary_tx_id else ""
        if self.generate_model().startswith("AirLink"):
            tx_id_part = ""
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
            unique_base = self.coordinator.data[self.tx_id]["DID"]
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            unique_base = self.coordinator.data[DataKey.UUID]
        return unique_base

    def get_firmware(self) -> str | None:
        """Get firmware version."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            return self.entry.runtime_data.station_data["stations"][0].get(
                "firmware_version"
            )
        return None

    def get_serial(self) -> str | None:
        """Get serial number."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            return self.entry.runtime_data.station_data["stations"][0].get(
                "gateway_id_hex"
            )
        return None

    def generate_name(self):
        """Generate device name."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            return self.coordinator.data[1]["station_name"]
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            if self.tx_id == self.primary_tx_id:
                return self.entry.runtime_data.station_data["stations"][0][
                    "station_name"
                ]
            for sensor in self.entry.runtime_data.sensors_metadata:
                if sensor["sensor_type"] in (55, 56) and sensor["tx_id"] == self.tx_id:
                    return f"{sensor['product_name']} ID{sensor['tx_id']}"

                if (
                    sensor["sensor_type"] in SENSOR_TYPE_AIRLINK
                    and sensor["lsid"] == self.tx_id
                ):
                    return f"{sensor['product_name']} {sensor['parent_device_name']}"

        return "Unknown devicename"

    def generate_model(self):
        """Generate model string."""
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            return "WeatherLink - API V1"
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            model: str = self.entry.runtime_data.station_data["stations"][0].get(
                "product_number"
            )
            break_out = False
            product_name = ""
            for sensor in self.entry.runtime_data.sensors_metadata:
                if break_out:
                    break
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["tx_id"] is None
                    or sensor["tx_id"] == self.tx_id
                ):
                    product_name = sensor.get("product_name")
                    break_out = True
                    continue
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_AIRLINK
                    and sensor["lsid"] == self.tx_id
                ):
                    product_name = sensor.get("product_name")
                    break_out = True
                    continue

            gateway_type = "WeatherLink"
            try:
                if model == "6555":
                    gateway_type = f"WLIP {model}"
                if model.startswith("6100"):
                    gateway_type = f"WLL {model}"
                if model.startswith("6313"):
                    gateway_type = f"WLC {model}"
                if model.startswith("6805"):
                    gateway_type = f"EnviroMonitor {model}"
                if model.startswith("7210"):
                    gateway_type = f"AirLink {model}"
                if model.endswith("6558"):
                    gateway_type = f"WL {model}"
            except AttributeError:
                pass

        return (
            f"{gateway_type} / {product_name}"
            if self.tx_id == self.primary_tx_id
            else product_name
        )

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

    @property
    def available(self):
        """Return the availability of the entity."""

        if not self.coordinator.last_update_success:
            return False

        if self.entity_description.key != "Timestamp":
            dt_update = dt_util.utc_from_timestamp(
                self.coordinator.data[self.tx_id].get(DataKey.TIMESTAMP)
            )
            dt_now = dt_util.now()
            diff = dt_now - dt_update
            return diff.total_seconds() < UNAVAILABLE_AFTER_SECONDS

        return True
