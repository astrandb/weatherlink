"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator
from .config_flow import API_V1, API_V2
from .const import CONF_API_VERSION, DOMAIN
from .pyweatherlink import WLData

_LOGGER = logging.getLogger(__name__)

SUBTAG_1 = "davis_current_observation"


@dataclass
class WLSensorDescription(SensorEntityDescription):
    """Class describing Weatherlink sensor entities."""

    tag: str | None = None
    subtag: str | None = None
    convert: Callable[[Any], Any] | None = None
    decimals: int = 1


SENSOR_TYPES: Final[tuple[WLSensorDescription, ...]] = (
    WLSensorDescription(
        key="OutsideTemp",
        tag="temp_out",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        translation_key="outside_temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="InsideTemp",
        tag="temp_in",
        device_class=SensorDeviceClass.TEMPERATURE,
        translation_key="inside_temperature",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="OutsideHumidity",
        tag="hum_out",
        device_class=SensorDeviceClass.HUMIDITY,
        suggested_display_precision=0,
        translation_key="outside_humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="InsideHumidity",
        tag="hum_in",
        device_class=SensorDeviceClass.HUMIDITY,
        suggested_display_precision=0,
        translation_key="inside_humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="Pressure",
        tag="bar_sea_level",
        device_class=SensorDeviceClass.PRESSURE,
        translation_key="pressure",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfPressure.INHG,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="Wind",
        tag="wind_mph",
        device_class=SensorDeviceClass.WIND_SPEED,
        translation_key="wind",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="WindDir",
        tag="wind_dir",
        icon="mdi:compass-outline",
        translation_key="wind_direction",
    ),
    WLSensorDescription(
        key="RainToday",
        tag="rain_day",
        translation_key="rain_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    WLSensorDescription(
        key="RainRate",
        tag="rain_rate",
        subtag=SUBTAG_1,
        translation_key="rain_rate",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.INCHES_PER_HOUR,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="RainInMonth",
        tag="rain_month",
        translation_key="rain_this_month",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    WLSensorDescription(
        key="RainInYear",
        tag="rain_year",
        translation_key="rain_this_year",
        device_class=SensorDeviceClass.PRECIPITATION,
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    WLSensorDescription(
        key="Dewpoint",
        tag="dewpoint",
        translation_key="dewpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = await get_coordinator(hass, config_entry)

    async_add_entities(
        WLSensor(coordinator, hass, config_entry, description)
        for description in SENSOR_TYPES
    )


class WLSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    entity_description: WLSensorDescription
    sensor_data = WLData()

    def __init__(
        self,
        coordinator,
        hass: HomeAssistant,
        entry: ConfigEntry,
        description: WLSensorDescription,
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
            manufacturer="Davis Instruments",
            model=self.generate_model(),
            sw_version=self.get_firmware(),
            configuration_url="https://www.weatherlink.com/",
        )

    def get_unique_id_base(self):
        """Generate base for unique_id."""
        unique_base = None
        if self.entry.data[CONF_API_VERSION] == API_V1:
            unique_base = self.coordinator.data["DID"]
        if self.entry.data[CONF_API_VERSION] == API_V2:
            unique_base = self.coordinator.data["station_id_uuid"]
        return unique_base

    def get_firmware(self) -> str | None:
        """Get firmware version."""
        if self.entry.data[CONF_API_VERSION] == API_V2:
            return self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0].get("firmware_version")
        return None

    def generate_name(self):
        """Generate device name."""
        if self.entry.data[CONF_API_VERSION] == API_V1:
            return self.coordinator.data["station_name"]
        if self.entry.data[CONF_API_VERSION] == API_V2:
            return self.hass.data[DOMAIN][self.entry.entry_id]["station_data"][
                "stations"
            ][0]["station_name"]

        return "Unknown devicename"

    def generate_model(self):
        """Generate model string."""
        if self.entry.data[CONF_API_VERSION] == API_V1:
            return "Weatherlink - API V1"
        if self.entry.data[CONF_API_VERSION] == API_V2:
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
    def native_value(self):
        """Return the state of the sensor."""
        # _LOGGER.debug("Key: %s", self.entity_description.key)
        if self.entity_description.key in [
            "OutsideTemp",
            "InsideTemp",
            "OutsideHumidity",
            "InsideHumidity",
            "Pressure",
            "Wind",
            "Dewpoint",
            "RainToday",
            "RainRate",
            "RainInYear",
            "RainInMonth",
        ]:
            return self.coordinator.data.get(self.entity_description.tag)

        if self.entity_description.tag in ["wind_dir"]:
            directions = [
                "n",
                "nne",
                "ne",
                "ene",
                "e",
                "ese",
                "se",
                "sse",
                "s",
                "ssw",
                "sw",
                "wsw",
                "w",
                "wnw",
                "nw",
                "nnw",
            ]

            index = int(
                (
                    (float(self.coordinator.data[self.entity_description.tag]) + 11.25)
                    % 360
                )
                // 22.5
            )

            return directions[index]

        return None
