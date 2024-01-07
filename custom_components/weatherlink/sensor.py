"""Platform for sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SENSOR_TYPE_VUE_AND_VANTAGE_PRO, get_coordinator
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

SUBTAG_1 = "davis_current_observation"


@dataclass
class WLSensorDescription(SensorEntityDescription):
    """Class describing Weatherlink sensor entities."""

    tag: DataKey | None = None
    exclude_api_ver: set = ()
    exclude_data_structure: set = ()
    aux_sensors: set = ()


SENSOR_TYPES: Final[tuple[WLSensorDescription, ...]] = (
    WLSensorDescription(
        key="OutsideTemp",
        tag=DataKey.TEMP_OUT,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        translation_key="outside_temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="InsideTemp",
        tag=DataKey.TEMP_IN,
        device_class=SensorDeviceClass.TEMPERATURE,
        translation_key="inside_temperature",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="OutsideHumidity",
        tag=DataKey.HUM_OUT,
        device_class=SensorDeviceClass.HUMIDITY,
        suggested_display_precision=0,
        translation_key="outside_humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="InsideHumidity",
        tag=DataKey.HUM_IN,
        device_class=SensorDeviceClass.HUMIDITY,
        suggested_display_precision=0,
        translation_key="inside_humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="Pressure",
        tag=DataKey.BAR_SEA_LEVEL,
        device_class=SensorDeviceClass.PRESSURE,
        translation_key="pressure",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfPressure.INHG,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WLSensorDescription(
        key="BarTrend",
        tag=DataKey.BAR_TREND,
        icon="mdi:trending-up",
        translation_key="bar_trend",
    ),
    WLSensorDescription(
        key="Wind",
        tag=DataKey.WIND_MPH,
        device_class=SensorDeviceClass.WIND_SPEED,
        translation_key="wind",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="WindGust",
        tag=DataKey.WIND_GUST_MPH,
        device_class=SensorDeviceClass.WIND_SPEED,
        translation_key="wind_gust",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="WindDir",
        tag=DataKey.WIND_DIR,
        icon="mdi:compass-outline",
        translation_key="wind_direction",
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="WindDirDeg",
        tag=DataKey.WIND_DIR,
        icon="mdi:compass-outline",
        native_unit_of_measurement=DEGREE,
        translation_key="wind_direction_deg",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="RainToday",
        tag=DataKey.RAIN_DAY,
        translation_key="rain_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="RainRate",
        tag=DataKey.RAIN_RATE,
        translation_key="rain_rate",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.INCHES_PER_HOUR,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="RainStorm",
        tag=DataKey.RAIN_STORM,
        translation_key="rain_storm",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        suggested_display_precision=1,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="RainStormLast",
        tag=DataKey.RAIN_STORM_LAST,
        translation_key="rain_storm_last",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        suggested_display_precision=1,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(2,),
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="RainInMonth",
        tag=DataKey.RAIN_MONTH,
        translation_key="rain_this_month",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="RainInYear",
        tag=DataKey.RAIN_YEAR,
        translation_key="rain_this_year",
        device_class=SensorDeviceClass.PRECIPITATION,
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="Dewpoint",
        tag=DataKey.DEWPOINT,
        translation_key="dewpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="WindChill",
        tag=DataKey.WIND_CHILL,
        translation_key="wind_chill",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="HeatIndex",
        tag=DataKey.HEAT_INDEX,
        translation_key="heat_index",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="WetBulb",
        tag=DataKey.WET_BULB,
        translation_key="wet_bulb",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(2,),
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="ThwIndex",
        tag=DataKey.THW_INDEX,
        translation_key="thw_index",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(2,),
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="ThswIndex",
        tag=DataKey.THSW_INDEX,
        translation_key="thsw_index",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(2,),
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="SolarRadiation",
        tag=DataKey.SOLAR_RADIATION,
        # translation_key="solar_radiation",
        device_class=SensorDeviceClass.IRRADIANCE,
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        state_class=SensorStateClass.MEASUREMENT,
        exclude_api_ver=(ApiVersion.API_V1,),
        aux_sensors=(55,),
    ),
    WLSensorDescription(
        key="TransBatteryVolt",
        tag=DataKey.TRANS_BATTERY_VOLT,
        translation_key="trans_battery_volt",
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=3,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(
            2,
            10,
        ),
    ),
    WLSensorDescription(
        key="SolarPanelVolt",
        tag=DataKey.SOLAR_PANEL_VOLT,
        translation_key="solar_panel_volt",
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=3,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(
            2,
            10,
        ),
    ),
    WLSensorDescription(
        key="SupercapVolt",
        tag=DataKey.SUPERCAP_VOLT,
        translation_key="supercap_volt",
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=3,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        exclude_api_ver=(ApiVersion.API_V1,),
        exclude_data_structure=(
            2,
            10,
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = await get_coordinator(hass, config_entry)
    primary_tx_id = hass.data[DOMAIN][config_entry.entry_id]["primary_tx_id"]
    entities = [
        WLSensor(coordinator, hass, config_entry, description, primary_tx_id)
        for description in SENSOR_TYPES
        if (config_entry.data[CONF_API_VERSION] not in description.exclude_api_ver)
        and (
            coordinator.data[primary_tx_id].get(DataKey.DATA_STRUCTURE)
            not in description.exclude_data_structure
        )
    ]

    aux_entities = []
    if config_entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        for sensor in hass.data[DOMAIN][config_entry.entry_id]["sensors_metadata"]:
            if sensor["tx_id"] is not None and sensor["tx_id"] != primary_tx_id:
                for description in SENSOR_TYPES:
                    if sensor["sensor_type"] in description.aux_sensors:
                        aux_entities.append(
                            WLSensor(
                                coordinator,
                                hass,
                                config_entry,
                                description,
                                sensor["tx_id"],
                            )
                        )

    async_add_entities(entities + aux_entities)


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
        tx_id: int,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.entry: ConfigEntry = entry
        self.entity_description = description
        self.tx_id = tx_id
        self.primary_tx_id = self.hass.data[DOMAIN][entry.entry_id]["primary_tx_id"]
        self._attr_has_entity_name = True
        tx_id_part = f"-{self.tx_id}" if self.tx_id != self.primary_tx_id else ""
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
            return self.coordinator.data[1]["station_name"]
        if self.entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            if self.tx_id == self.primary_tx_id:
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
            for sensor in self.hass.data[DOMAIN][self.entry.entry_id][
                "sensors_metadata"
            ]:
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["tx_id"] is None
                    or sensor["tx_id"] == self.tx_id
                ):
                    product_name = sensor.get("product_name")
                    break
            gateway_type = "WeatherLink"
            if model == "6555":
                gateway_type = f"WLIP {model}"
            if model.startswith("6100"):
                gateway_type = f"WLL {model}"
            if model.startswith("6313"):
                gateway_type = f"WLC {model}"
            if model.endswith("6558"):
                gateway_type = f"WL {model}"

        return (
            f"{gateway_type} / {product_name}"
            if self.tx_id == self.primary_tx_id
            else product_name
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # _LOGGER.debug("Key: %s", self.entity_description.key)
        if self.entity_description.key in [
            "Dewpoint",
            "HeatIndex",
            "InsideHumidity",
            "InsideTemp",
            "OutsideHumidity",
            "OutsideTemp",
            "Pressure",
            "RainInMonth",
            "RainInYear",
            "RainRate",
            "RainStorm",
            "RainStormLast",
            "RainToday",
            "SolarPanelVolt",
            "SolarRadiation",
            "SupercapVolt",
            "ThwIndex",
            "ThswIndex",
            "TransBatteryVolt",
            "WetBulb",
            "Wind",
            "WindChill",
            "WindDirDeg",
            "WindGust",
        ]:
            return self.coordinator.data[self.tx_id].get(self.entity_description.tag)

        if self.entity_description.tag in [DataKey.WIND_DIR]:
            if self.coordinator.data[self.tx_id][self.entity_description.tag] is None:
                return None

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
                    (
                        float(
                            self.coordinator.data[self.tx_id][
                                self.entity_description.tag
                            ]
                        )
                        + 11.25
                    )
                    % 360
                )
                // 22.5
            )

            return directions[index]

        if self.entity_description.key == "BarTrend":
            bar_trend = self.coordinator.data[self.tx_id].get(
                self.entity_description.tag
            )
            if bar_trend is None:
                return None
            if self.is_float(bar_trend):
                if bar_trend >= 0.060:
                    return "rising_rapidly"
                if bar_trend >= 0.020:
                    return "rising_slowly"
                if bar_trend > -0.020:
                    return "steady"
                if bar_trend > -0.060:
                    return "falling_slowly"
                return "falling_rapidly"
            return str(bar_trend).lower().replace(" ", "_")
        return None

    def is_float(self, in_string):
        """Check if string is float."""
        try:
            float(in_string)
            return True
        except ValueError:
            return False

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes, if any."""
        if self.entity_description.key in [
            "RainStorm",
        ]:
            if self.coordinator.data[self.tx_id].get(DataKey.RAIN_STORM_START) is None:
                return None
            dt_object = datetime.fromtimestamp(
                self.coordinator.data[self.tx_id].get(DataKey.RAIN_STORM_START)
            )
            return {
                "rain_storm_start": dt_object,
            }
        if self.entity_description.key in [
            "RainStormLast",
        ]:
            if (
                self.coordinator.data[self.tx_id].get(DataKey.RAIN_STORM_LAST_START)
                is None
            ):
                return None
            dt_object = datetime.fromtimestamp(
                self.coordinator.data[self.tx_id].get(DataKey.RAIN_STORM_LAST_START)
            )
            if (
                self.coordinator.data[self.tx_id].get(DataKey.RAIN_STORM_LAST_END)
                is None
            ):
                return None
            dt_object_end = datetime.fromtimestamp(
                self.coordinator.data[self.tx_id].get(DataKey.RAIN_STORM_LAST_END)
            )
            return {
                "rain_storm_start": dt_object,
                "rain_storm_end": dt_object_end,
            }
        return
