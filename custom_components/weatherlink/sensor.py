"""Platform for sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    LENGTH_MILLIMETERS,
    PERCENTAGE,
    PRECIPITATION_MILLIMETERS_PER_HOUR,
    PRESSURE_MBAR,
    SPEED_METERS_PER_SECOND,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator
from .const import DOMAIN

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
        tag="temp_c",
        device_class=SensorDeviceClass.TEMPERATURE,
        name="Outside temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="OutsideHumidity",
        tag="relative_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        name="Outside humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="InsideHumidity",
        tag="relative_humidity_in",
        subtag=SUBTAG_1,
        device_class=SensorDeviceClass.HUMIDITY,
        name="Inside humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="Pressure",
        tag="pressure_mb",
        device_class=SensorDeviceClass.PRESSURE,
        name="Pressure",
        native_unit_of_measurement=PRESSURE_MBAR,
        state_class=SensorStateClass.MEASUREMENT,
        decimals=0,
    ),
    WLSensorDescription(
        key="Wind",
        tag="wind_mph",
        device_class=SensorDeviceClass.SPEED,
        icon="mdi:weather-windy",
        name="Wind",
        convert=lambda x: x * 1609 / 3600,
        native_unit_of_measurement=SPEED_METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="WindDir",
        tag="wind_dir",
        icon="mdi:compass-outline",
        name="Wind direction",
        native_unit_of_measurement="",
    ),
    WLSensorDescription(
        key="InsideTemp",
        tag="temp_in_f",
        subtag=SUBTAG_1,
        device_class=SensorDeviceClass.TEMPERATURE,
        name="Inside temperature",
        native_unit_of_measurement=TEMP_FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="RainToday",
        tag="rain_day_in",
        subtag=SUBTAG_1,
        icon="mdi:weather-pouring",
        name="Rain today",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=LENGTH_MILLIMETERS,
        convert=lambda x: x * 25.4,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="RainRate",
        tag="rain_rate_in_per_hr",
        subtag=SUBTAG_1,
        icon="mdi:weather-pouring",
        name="Rain rate",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=PRECIPITATION_MILLIMETERS_PER_HOUR,
        convert=lambda x: x * 25.4,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="RainInMonth",
        tag="rain_month_in",
        subtag=SUBTAG_1,
        icon="mdi:weather-pouring",
        name="Rain this month",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=LENGTH_MILLIMETERS,
        convert=lambda x: x * 25.4,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="RainInYear",
        tag="rain_year_in",
        subtag=SUBTAG_1,
        icon="mdi:weather-pouring",
        name="Rain this year",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=LENGTH_MILLIMETERS,
        convert=lambda x: x * 25.4,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    WLSensorDescription(
        key="Dewpoint",
        tag="dewpoint_c",
        name="Dewpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
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
        WLSensor(coordinator, description) for description in SENSOR_TYPES
    )


class WLSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    entity_description: WLSensorDescription

    def __init__(self, coordinator, description: WLSensorDescription):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = (
            f"{self.coordinator.data[SUBTAG_1]['DID']}-{self.entity_description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.data[SUBTAG_1]["DID"])},
            name=self.coordinator.data[SUBTAG_1]["station_name"],
            manufacturer="Davis",
            model="Weatherlink",
            configuration_url="https://www.weatherlink.com/",
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.entity_description.subtag is not None:
            if (
                self.coordinator.data[self.entity_description.subtag].get(
                    self.entity_description.tag
                )
                is None
            ):
                return None
            value = float(
                self.coordinator.data[self.entity_description.subtag][
                    self.entity_description.tag
                ]
            )
        else:
            if self.entity_description.tag in ["wind_dir"]:
                return self.coordinator.data[self.entity_description.tag]

            if self.coordinator.data.get(self.entity_description.tag) is None:
                return None
            value = float(self.coordinator.data[self.entity_description.tag])

        if self.entity_description.convert is not None:
            value = self.entity_description.convert(value)
        return round(value, self.entity_description.decimals)
