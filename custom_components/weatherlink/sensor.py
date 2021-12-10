"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    DEVICE_CLASS_TEMPERATURE,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
)
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = await get_coordinator(hass, config_entry)

    async_add_entities(
        # WLSensor(coordinator, idx) for idx, ent in enumerate(coordinator.data)
        [WLSensor(coordinator, 1)]
    )


class WLSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, coordinator, idx):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._idx = idx
        self._state = None
        self._attr_name = "Outside temp"  # self.coordinator.data[self._idx]["name"]
        self._attr_device_class = DEVICE_CLASS_TEMPERATURE
        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._attr_state_class = STATE_CLASS_MEASUREMENT
        self._attr_unique_id = (
            "temp-123"  # {self.coordinator.data[self._idx]['serialNumber']}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, "123")
            },  # self.coordinator.data[self._idx]["serialNumber"])},
            # name=self.coordinator.data[self._idx]["name"],
            name="Device 1",
            manufacturer="Davis",
            model="Weatherlink",
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # return 23.4
        return round(float(self.coordinator.data["temp_c"]), 1)
