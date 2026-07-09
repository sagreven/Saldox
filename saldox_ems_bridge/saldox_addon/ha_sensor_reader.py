"""Read inverter data from existing HA sensors (Solax/SolarmanV2 integration).

When the Solax integration already holds the Modbus connection, this module
reads its HA sensor states and converts them to the same internal format
that the direct Modbus reader produces. This allows the rest of the add-on
(dashboard, plan poller, action executor) to work unchanged.

Also provides battery control via HA service calls (energy storage mode,
passive mode power limits) instead of direct Modbus writes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .ha_api import HomeAssistantClient

_LOG = logging.getLogger(__name__)


@dataclass
class Reading:
    """Matches the format from modbus_client.read_all()."""
    name: str
    value: float | int
    unit: str


# Map: our internal register name → (HA entity_id, unit, scale factor).
# Scale converts HA values (typically kW) to our internal format (W).
_SENSOR_MAP: dict[str, tuple[str, str, float]] = {
    "pv_total_power_w":       ("sensor.sofar_inverter_sofar_pv_power_total",           "W",  1000),
    "ac_active_power_w":      ("sensor.sofar_inverter_sofar_active_power_pcc_total",   "W",  1000),  # kW→W
    "battery_soc_percent":    ("sensor.sofar_inverter_sofar_battery_capacity_total",    "%",  1),
    "battery_power_w":        ("sensor.sofar_inverter_sofar_battery_power_total",       "W",  1000),  # kW→W
    "battery_voltage_v":      ("sensor.sofar_inverter_sofar_battery_voltage_1",         "V",  1),
    "battery_temperature_c":  ("sensor.sofar_inverter_sofar_battery_temperature_1",     "°C", 1),
    "inverter_temperature_c": ("sensor.sofar_inverter_sofar_heatsink_temperature_1",    "°C", 1),
    "today_production_kwh":   ("sensor.sofar_inverter_sofar_solar_generation_today",    "kWh", 1),
    "total_production_kwh":   ("sensor.sofar_inverter_sofar_solar_generation_total",    "kWh", 1),
    "today_import_kwh":       ("sensor.sofar_inverter_sofar_import_energy_today",       "kWh", 1),
    "today_export_kwh":       ("sensor.sofar_inverter_sofar_export_energy_today",       "kWh", 1),
    "today_consumption_kwh":  ("sensor.sofar_inverter_sofar_load_consumption_today",    "kWh", 1),
    "battery_input_today_kwh":("sensor.sofar_inverter_sofar_battery_input_energy_today","kWh", 1),
    "battery_output_today_kwh":("sensor.sofar_inverter_sofar_battery_output_energy_today","kWh", 1),
    "battery_soh_percent":    ("sensor.sofar_inverter_sofar_battery_state_of_health_total", "%", 1),
    "battery_cycles":         ("sensor.sofar_inverter_sofar_battery_charge_cycle_1",    "",   1),
    "grid_frequency_hz":      ("sensor.sofar_inverter_sofar_grid_frequency",            "Hz", 1),
    "inverter_status":        ("sensor.sofar_inverter_sofar_system_state",              "",   0),  # text
    "pv1_power_w":            ("sensor.sofar_inverter_sofar_pv_power_1",               "W",  1000),
    "pv2_power_w":            ("sensor.sofar_inverter_sofar_pv_power_2",               "W",  1000),
    "load_power_w":           ("sensor.sofar_inverter_sofar_active_power_load_sys",     "W",  1000),
}

# Control entities for battery mode via HA services.
_STORAGE_MODE_ENTITY = "select.sofar_inverter_energy_storage_mode"
_PASSIVE_GRID_POWER = "number.sofar_inverter_passive_desired_grid_power"
_PASSIVE_MAX_BAT_POWER = "number.sofar_inverter_passive_maximum_battery_power"
_PASSIVE_MIN_BAT_POWER = "number.sofar_inverter_passive_minimum_battery_power"
_PASSIVE_UPDATE_BUTTON = "button.sofar_inverter_passive_update_battery_charge_discharge"


class HaSensorReader:
    """Reads Sofar inverter data from HA sensors provided by the Solax integration."""

    def __init__(self, ha: HomeAssistantClient):
        self._ha = ha

    async def read_all(self) -> list[Reading]:
        """Read all mapped HA sensors and return as Reading list."""
        entity_ids = [entity for entity, _, _ in _SENSOR_MAP.values()]
        states = await self._ha.get_states(entity_ids)

        readings: list[Reading] = []
        for name, (entity_id, unit, scale) in _SENSOR_MAP.items():
            state_obj = states.get(entity_id)
            if state_obj is None:
                continue
            raw = state_obj.get("state", "")
            if raw in ("unknown", "unavailable", ""):
                continue
            if scale == 0:
                # Text value (e.g. inverter status).
                readings.append(Reading(name=name, value=raw, unit=unit))
            else:
                try:
                    value = round(float(raw) * scale, 1)
                    readings.append(Reading(name=name, value=value, unit=unit))
                except (ValueError, TypeError):
                    continue
        return readings

    async def close(self) -> None:
        """No-op — connection is managed by HA client."""
        pass


class HaBatteryController:
    """Controls the Sofar inverter battery via HA service calls.

    Uses the Solax integration's energy storage mode and passive mode
    power limits instead of direct Modbus writes.
    """

    def __init__(self, ha: HomeAssistantClient, max_power_w: int = 10000):
        self._ha = ha
        self._max_power_w = max_power_w
        self._last_mode: str | None = None

    async def set_charge(self, power_w: int | None = None) -> str | None:
        """Force-charge battery at given power (default: max)."""
        watts = power_w or self._max_power_w
        if self._last_mode == f"charge_{watts}":
            return None

        # Set to Passive Mode, then set high grid import + battery charge power.
        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": watts,
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": watts,  # import from grid to charge battery
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": 0,  # no discharge
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        self._last_mode = f"charge_{watts}"
        _LOG.info("CONTROL: force-charge @ %d W via HA Passive Mode", watts)
        return f"Laden {watts} W"

    async def set_discharge(self, power_w: int | None = None) -> str | None:
        """Force-discharge battery at given power (default: max)."""
        watts = power_w or self._max_power_w
        if self._last_mode == f"discharge_{watts}":
            return None

        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": watts,  # discharge power
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": -watts,  # export to grid
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": 0,  # no charge
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        self._last_mode = f"discharge_{watts}"
        _LOG.info("CONTROL: force-discharge @ %d W via HA Passive Mode", watts)
        return f"Ontladen {watts} W"

    async def set_auto(self) -> str | None:
        """Return to Self Use (auto) mode."""
        if self._last_mode == "auto":
            return None

        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Self Use",
        })

        self._last_mode = "auto"
        _LOG.info("CONTROL: reset to Self Use mode via HA")
        return "Auto modus"
