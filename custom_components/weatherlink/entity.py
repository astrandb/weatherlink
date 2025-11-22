"""Base entity for weatherlink integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SENSOR_TYPE_AIRLINK, SENSOR_TYPE_VUE_AND_VANTAGE_PRO, WLConfigEntry
from .const import (
    CONF_API_VERSION,
    CONFIG_URL,
    DOMAIN,
    MANUFACTURER,
    UNAVAILABLE_AFTER_SECONDS,
    ApiVersion,
    DataKey,
)
from .pyweatherlink import WLData

_LOGGER = logging.getLogger(__name__)


class WLEntity(CoordinatorEntity):
    """Representation of the base entity."""

    entity_description: EntityDescription
    sensor_data = WLData()

    def __init__(
        self,
        coordinator,
        hass: HomeAssistant,
        entry: WLConfigEntry,
        description: EntityDescription,
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
