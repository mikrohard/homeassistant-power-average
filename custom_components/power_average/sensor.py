"""Sensor platform for Power Average Calculator."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Power Average Calculator sensor."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    
    sensors = []
    
    power_sensor = PowerAverageSensor(
        hass,
        config_entry.entry_id,
        data.get("name", "Power Average"),
        data.get("current_l1"),
        data.get("current_l2"),
        data.get("current_l3"),
        data.get("voltage_l1"),
        data.get("voltage_l2"),
        data.get("voltage_l3"),
    )
    
    completed_window_sensor = CompletedWindowPowerSensor(
        hass,
        config_entry.entry_id,
        data.get("name", "Power Average"),
        power_sensor,
    )
    
    power_sensor.set_completed_window_sensor(completed_window_sensor)
    
    sensors.append(power_sensor)
    sensors.append(completed_window_sensor)
    
    async_add_entities(sensors)


class PowerAverageSensor(SensorEntity):
    """Representation of a Power Average sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        current_l1: str,
        current_l2: str,
        current_l3: str,
        voltage_l1: str,
        voltage_l2: str,
        voltage_l3: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_power_average"
        
        self._current_l1 = current_l1
        self._current_l2 = current_l2
        self._current_l3 = current_l3
        self._voltage_l1 = voltage_l1
        self._voltage_l2 = voltage_l2
        self._voltage_l3 = voltage_l3
        
        self._measurements = []
        self._window_start = None
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        
        self._unsubscribe_state_change = None
        self._unsubscribe_interval = None
        self._completed_window_sensor = None
        self._completed_window_data = None

    def set_completed_window_sensor(self, sensor):
        """Set the completed window sensor reference."""
        self._completed_window_sensor = sensor

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Power Average Calculator",
            manufacturer="Custom",
            model="Power Average",
            sw_version="1.0.0",
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        entities = [
            self._current_l1,
            self._current_l2,
            self._current_l3,
            self._voltage_l1,
            self._voltage_l2,
            self._voltage_l3,
        ]
        
        self._unsubscribe_state_change = async_track_state_change_event(
            self.hass,
            entities,
            self._handle_state_change
        )
        
        self._unsubscribe_interval = async_track_time_interval(
            self.hass,
            self._update_average,
            timedelta(seconds=10)
        )
        
        self._reset_window()
        self._take_measurement()
        self._update_average(None)

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        if self._unsubscribe_state_change:
            self._unsubscribe_state_change()
        if self._unsubscribe_interval:
            self._unsubscribe_interval()

    def _get_window_start(self, now: datetime) -> datetime:
        """Calculate the start of the current 15-minute window."""
        minute = now.minute
        window_minute = (minute // 15) * 15
        return now.replace(minute=window_minute, second=0, microsecond=0)

    def _reset_window(self) -> None:
        """Reset the measurement window."""
        now = dt_util.now()
        self._window_start = self._get_window_start(now)
        self._measurements = []
        _LOGGER.debug("Window reset. New window start: %s", self._window_start)

    def _take_measurement(self) -> None:
        """Take a power measurement."""
        try:
            current_l1_state = self.hass.states.get(self._current_l1)
            current_l2_state = self.hass.states.get(self._current_l2)
            current_l3_state = self.hass.states.get(self._current_l3)
            voltage_l1_state = self.hass.states.get(self._voltage_l1)
            voltage_l2_state = self.hass.states.get(self._voltage_l2)
            voltage_l3_state = self.hass.states.get(self._voltage_l3)
            
            if not all([
                current_l1_state,
                current_l2_state,
                current_l3_state,
                voltage_l1_state,
                voltage_l2_state,
                voltage_l3_state,
            ]):
                _LOGGER.warning("Not all entities are available")
                return
            
            i1 = float(current_l1_state.state) if current_l1_state.state != "unavailable" else 0
            i2 = float(current_l2_state.state) if current_l2_state.state != "unavailable" else 0
            i3 = float(current_l3_state.state) if current_l3_state.state != "unavailable" else 0
            v1 = float(voltage_l1_state.state) if voltage_l1_state.state != "unavailable" else 230
            v2 = float(voltage_l2_state.state) if voltage_l2_state.state != "unavailable" else 230
            v3 = float(voltage_l3_state.state) if voltage_l3_state.state != "unavailable" else 230
            
            i1 = max(0, i1)
            i2 = max(0, i2)
            i3 = max(0, i3)
            
            power = (i1 * v1) + (i2 * v2) + (i3 * v3)
            
            now = dt_util.now()
            self._measurements.append({
                "timestamp": now,
                "power": power,
                "l1_power": i1 * v1,
                "l2_power": i2 * v2,
                "l3_power": i3 * v3,
            })
            
            _LOGGER.debug(
                "Measurement taken: L1=%sW, L2=%sW, L3=%sW, Total=%sW",
                i1 * v1,
                i2 * v2,
                i3 * v3,
                power
            )
            
        except (ValueError, AttributeError) as err:
            _LOGGER.error("Error taking measurement: %s", err)

    @callback
    def _handle_state_change(self, event) -> None:
        """Handle state changes of monitored entities."""
        self._take_measurement()
        self._update_average(None)

    @callback
    def _update_average(self, time) -> None:
        """Calculate and update the average power."""
        now = dt_util.now()
        current_window_start = self._get_window_start(now)
        
        if self._window_start != current_window_start:
            if self._measurements and self._completed_window_sensor:
                total_power = sum(m["power"] for m in self._measurements)
                avg_power = total_power / len(self._measurements)
                
                avg_l1 = sum(m["l1_power"] for m in self._measurements) / len(self._measurements)
                avg_l2 = sum(m["l2_power"] for m in self._measurements) / len(self._measurements)
                avg_l3 = sum(m["l3_power"] for m in self._measurements) / len(self._measurements)
                
                self._completed_window_data = {
                    "average_power": round(avg_power, 2),
                    "window_start": self._window_start.isoformat(),
                    "window_end": current_window_start.isoformat(),
                    "measurement_count": len(self._measurements),
                    "l1_average_power": round(avg_l1, 2),
                    "l2_average_power": round(avg_l2, 2),
                    "l3_average_power": round(avg_l3, 2),
                }
                
                self._completed_window_sensor.update_completed_window(self._completed_window_data)
            
            self._reset_window()
            self._take_measurement()
        
        self._measurements = [
            m for m in self._measurements
            if m["timestamp"] >= self._window_start
        ]
        
        if not self._measurements:
            self._attr_native_value = 0
            self._attr_extra_state_attributes = {
                "window_start": self._window_start.isoformat(),
                "measurement_count": 0,
                "window_duration_seconds": 0,
            }
        else:
            total_power = sum(m["power"] for m in self._measurements)
            avg_power = total_power / len(self._measurements)
            
            self._attr_native_value = round(avg_power, 2)
            
            window_duration = (now - self._window_start).total_seconds()
            
            avg_l1 = sum(m["l1_power"] for m in self._measurements) / len(self._measurements)
            avg_l2 = sum(m["l2_power"] for m in self._measurements) / len(self._measurements)
            avg_l3 = sum(m["l3_power"] for m in self._measurements) / len(self._measurements)
            
            self._attr_extra_state_attributes = {
                "window_start": self._window_start.isoformat(),
                "measurement_count": len(self._measurements),
                "window_duration_seconds": round(window_duration, 1),
                "l1_average_power": round(avg_l1, 2),
                "l2_average_power": round(avg_l2, 2),
                "l3_average_power": round(avg_l3, 2),
                "last_measurement": self._measurements[-1]["timestamp"].isoformat(),
            }
        
        self.async_write_ha_state()


class CompletedWindowPowerSensor(SensorEntity):
    """Sensor that shows the average power from the last completed 15-minute window."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        power_sensor: PowerAverageSensor,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = f"{name} Completed Window"
        self._attr_unique_id = f"{entry_id}_power_average_completed"
        self._power_sensor = power_sensor
        
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Power Average Calculator",
            manufacturer="Custom",
            model="Power Average",
            sw_version="1.0.0",
        )

    @callback
    def update_completed_window(self, window_data: dict) -> None:
        """Update with completed window data."""
        self._attr_native_value = window_data["average_power"]
        self._attr_extra_state_attributes = {
            "window_start": window_data["window_start"],
            "window_end": window_data["window_end"],
            "measurement_count": window_data["measurement_count"],
            "l1_average_power": window_data["l1_average_power"],
            "l2_average_power": window_data["l2_average_power"],
            "l3_average_power": window_data["l3_average_power"],
        }
        self.async_write_ha_state()