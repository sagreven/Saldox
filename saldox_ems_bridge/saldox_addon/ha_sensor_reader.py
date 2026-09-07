"""Read inverter data from existing HA sensors (Solax/SolarmanV2 integration).

When the Solax integration already holds the Modbus connection, this module
reads its HA sensor states and converts them to the same internal format
that the direct Modbus reader produces. This allows the rest of the add-on
(dashboard, plan poller, action executor) to work unchanged.

Also provides battery control via:
  - ModbusBatteryController: direct Modbus writes (preferred, <1s latency)
  - HaBatteryController: HA/Solax service calls (deprecated fallback)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .ha_api import HomeAssistantClient
from .registers import by_name

if TYPE_CHECKING:
    from .modbus_client import SofarModbusClient

_LOG = logging.getLogger(__name__)


@dataclass
class Reading:
    """Matches the format from modbus_client.read_all()."""
    name: str
    value: float | int
    unit: str


# Map: our internal register name → (HA entity_id, unit, scale factor).
# Scale converts HA values (typically kW) to our internal format (W).
# SolarmanV2 entity mapping (davidrapan/ha-solarman, profiel sofar_g3hyd.yaml)
# WiFi logger LSW3 op 192.168.178.159:8899, SN 3154393423
# NB: SolarmanV2 entities rapporteren in W (niet kW), dus scale=1.
_SENSOR_MAP: dict[str, tuple[str, str, float]] = {
    "pv_total_power_w":       ("sensor.sofar_hyd_pv_power",                "W",  1),
    "ac_active_power_w":      ("sensor.sofar_hyd_activepower_pcc_total",   "W",  1),
    "battery_soc_percent":    ("sensor.sofar_hyd_battery",                  "%",  1),
    "battery_power_w":        ("sensor.sofar_hyd_battery_power",            "W",  1),
    "battery_voltage_v":      ("sensor.sofar_hyd_battery_voltage",          "V",  1),
    "battery_temperature_c":  ("sensor.sofar_hyd_battery_temperature",      "°C", 1),
    "inverter_temperature_c": ("sensor.sofar_hyd_ambient_temperature_1",    "°C", 1),
    "today_production_kwh":   ("sensor.sofar_hyd_today_production",         "kWh", 1),
    "total_production_kwh":   ("sensor.sofar_hyd_total_production",         "kWh", 1),
    "today_import_kwh":       ("sensor.sofar_hyd_today_energy_import",      "kWh", 1),
    "today_export_kwh":       ("sensor.sofar_hyd_today_energy_export",      "kWh", 1),
    "today_consumption_kwh":  ("sensor.sofar_hyd_today_load_consumption",   "kWh", 1),
    "battery_input_today_kwh":("sensor.sofar_hyd_today_battery_charge",     "kWh", 1),
    "battery_output_today_kwh":("sensor.sofar_hyd_today_battery_discharge", "kWh", 1),
    "battery_soh_percent":    ("sensor.sofar_hyd_battery_soh",              "%",  1),
    "battery_cycles":         ("sensor.sofar_hyd_battery_number_of_cycles", "",   1),
    "grid_frequency_hz":      ("sensor.sofar_hyd_grid_frequency",           "Hz", 1),
    "inverter_status":        ("sensor.sofar_hyd_inverter_status",          "",   0),  # text
    "pv1_power_w":            ("sensor.sofar_hyd_pv1_power",               "W",  1),
    "pv2_power_w":            ("sensor.sofar_hyd_pv2_power",               "W",  1),
    "load_power_w":           ("sensor.sofar_hyd_activepower_load_sys",     "W",  1),
}

# Control entities for battery mode via SolarmanV2 HA services.
_STORAGE_MODE_ENTITY = "select.sofar_hyd_storage_control_mode"
_PASSIVE_GRID_POWER = "number.sofar_hyd_passive_grid_power"
_PASSIVE_MAX_BAT_POWER = "number.sofar_hyd_passive_maximum_battery_power"
_PASSIVE_MIN_BAT_POWER = "number.sofar_hyd_passive_minimum_battery_power"
_PASSIVE_UPDATE_BUTTON = ""  # SolarmanV2 heeft geen update button nodig — writes zijn direct


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


class ModbusBatteryController:
    """Controls Sofar HYD battery via direct Modbus writes over RS485.

    Bewezen werkend op 2026-07-14: 9600 baud, FC16 (write multiple), Passive Mode
    block write (0x1187-0x118C, 6 registers in één FC16 call).

    Sofar Passive Mode conventie:
      - grid_power: + = import van grid, - = export naar grid
      - min_battery: - = max discharge power (negatief!)
      - max_battery: + = max charge power

    FC06 (write single) werkt NIET op deze firmware — alleen FC16.
    """

    def __init__(self, modbus: SofarModbusClient, max_power_w: int = 15000,
                 ramp_start_w: int = 500, ramp_rate_w_per_s: int = 50,
                 ramp_idle_threshold_w: int = 100):
        self._modbus = modbus
        self._max_power_w = max_power_w
        self._last_mode: str | None = None
        # Track last written values for periodic verification.
        self._last_written: dict[str, int] | None = None
        # Soft-start voor laden — zie _charge_ceiling().
        self._ramp_start_w = ramp_start_w
        self._ramp_rate_w_per_s = ramp_rate_w_per_s
        self._ramp_idle_threshold_w = ramp_idle_threshold_w
        self._ramp_started_at: float | None = None

    # ------------------------------------------------------------------
    #  Soft-start / ramp-up
    # ------------------------------------------------------------------

    def note_battery_power(self, watts: float | None) -> None:
        """Feed the measured battery power in so the ramp tracks reality.

        Zolang er feitelijk niet geladen wordt houden we de ramp scherpgesteld,
        zodat het plafond pas gaat oplopen vanaf het moment dat er echt stroom
        de batterij in gaat. Zonder deze koppeling zou de ramp al 's nachts in
        baseline-modus aflopen en bij zonsopgang geen bescherming meer bieden.

        LET OP — tekenconventie. De comment bij het battery_power_w-register
        (registers.py) claimt "wij + = laden", maar dat klopt niet met de
        praktijk. Gemeten op 2026-09-07 om 18:20 UTC, met de executor in
        geforceerde ontlading (max_bat_w=0, laden dus onmogelijk):

            add-on battery_power_w         = +420 W
            sensor.sofar_hyd_battery_power = -410 W
            sensor.sofar_hyd_battery_current = -1,08 A
            SoC liep in dat venster van 39% naar 38%

        In readings["battery_power_w"] is positief dus ONTLADEN. We rekenen
        hier daarom om naar laadvermogen.
        """
        if watts is None:
            return
        charge_w = -watts  # zie docstring: add-on levert + bij ontladen
        if charge_w < self._ramp_idle_threshold_w:
            self._ramp_started_at = None

    def _charge_ceiling(self, requested_w: int) -> int:
        """Return how much charge power we currently allow.

        De DC-zekering klapt eruit wanneer er in één keer een hoog laadvermogen
        op een (bijna) lege batterij wordt gezet. We springen daarom nooit
        direct naar het gevraagde vermogen: vanaf het moment dat het laden
        aangaat starten we op _ramp_start_w en lopen lineair op met
        _ramp_rate_w_per_s tot het gevraagde plafond bereikt is.

        Bewust op wall-time gebaseerd en niet per poll-cyclus, zodat
        POLL_INTERVAL de rampsnelheid niet beïnvloedt.
        """
        if requested_w <= 0:
            self._ramp_started_at = None  # laden uit — ramp weer scherpstellen
            return 0
        now = time.monotonic()
        if self._ramp_started_at is None:
            self._ramp_started_at = now
        elapsed = now - self._ramp_started_at
        allowed = self._ramp_start_w + self._ramp_rate_w_per_s * elapsed
        return max(1, min(int(allowed), requested_w))

    async def _set_storage_mode(self, mode: int) -> None:
        """Set energy storage mode via FC16. 0=SelfUse, 3=Passive, etc."""
        await self._modbus.write_holding(by_name("energy_storage_mode"), mode)

    async def _write_passive(self, grid_w: int, min_bat_w: int, max_bat_w: int) -> None:
        """Write passive block and track values for later verification."""
        await self._modbus.write_passive_block(grid_w, min_bat_w, max_bat_w)
        self._last_written = {"grid_w": grid_w, "min_bat_w": min_bat_w, "max_bat_w": max_bat_w}

    @property
    def last_written_registers(self) -> dict[str, int] | None:
        """Last written passive register values (for external monitoring)."""
        return self._last_written

    async def set_charge(self, power_w: int | None = None) -> str | None:
        """Force-charge battery via Passive Mode."""
        watts = power_w or self._max_power_w
        ceiling = self._charge_ceiling(watts)
        if self._last_mode == f"charge_{watts}_{ceiling}":
            return None
        try:
            await self._set_storage_mode(3)  # Passive
            await self._write_passive(
                grid_w=ceiling,     # import from grid for charging
                min_bat_w=ceiling,  # force charge (positive min = force charge)
                max_bat_w=ceiling,  # max charge rate (soft-started)
            )
        except Exception as ex:
            _LOG.error("Modbus write failed (set_charge %d W): %s", ceiling, ex)
            return f"FOUT: charge {ceiling} W — {ex}"
        self._last_mode = f"charge_{watts}_{ceiling}"
        if ceiling < watts:
            _LOG.info("MODBUS CONTROL: force-charge ramp %d/%d W", ceiling, watts)
            return f"Laden {ceiling} W (ramp → {watts} W, direct Modbus)"
        _LOG.info("MODBUS CONTROL: force-charge @ %d W", ceiling)
        return f"Laden {ceiling} W (direct Modbus)"

    async def set_discharge(self, power_w: int | None = None) -> str | None:
        """Force-discharge battery via Passive Mode."""
        watts = power_w or self._max_power_w
        self._charge_ceiling(0)  # laden uit — soft-start weer scherpstellen
        if self._last_mode == f"discharge_{watts}":
            return None
        try:
            await self._set_storage_mode(3)  # Passive
            await self._write_passive(
                grid_w=-watts,      # export to grid
                min_bat_w=-watts,   # force discharge (negative = discharge)
                max_bat_w=0,        # no charging
            )
        except Exception as ex:
            _LOG.error("Modbus write failed (set_discharge %d W): %s", watts, ex)
            return f"FOUT: discharge {watts} W — {ex}"
        self._last_mode = f"discharge_{watts}"
        _LOG.info("MODBUS CONTROL: force-discharge @ %d W", watts)
        return f"Ontladen {watts} W (direct Modbus)"

    async def set_auto(self) -> str | None:
        """Baseline mode: Passive, PV charges battery, no grid charge.

        grid_w=0 prevents grid import for charging. max_bat allows PV surplus
        to flow into the battery. min_bat allows discharge to cover load.
        """
        ceiling = self._charge_ceiling(self._max_power_w)
        if self._last_mode == f"auto_{ceiling}":
            return None
        try:
            await self._set_storage_mode(3)  # Passive
            await self._write_passive(
                grid_w=0,                    # no grid import target
                min_bat_w=-self._max_power_w, # allow full discharge
                max_bat_w=ceiling,           # PV surplus charging, soft-started
            )
        except Exception as ex:
            _LOG.error("Modbus write failed (set_auto): %s", ex)
            return f"FOUT: auto — {ex}"
        self._last_mode = f"auto_{ceiling}"
        _LOG.info("MODBUS CONTROL: auto/baseline (Passive, grid=0, PV charge ≤ %d W)", ceiling)
        return "Baseline (direct Modbus)"

    async def set_standby(self) -> str | None:
        """Standby: battery does nothing."""
        self._charge_ceiling(0)  # laden uit — soft-start weer scherpstellen
        if self._last_mode == "standby":
            return None
        try:
            await self._set_storage_mode(3)  # Passive
            await self._write_passive(
                grid_w=0,
                min_bat_w=0,    # no discharge
                max_bat_w=0,    # no charge
            )
        except Exception as ex:
            _LOG.error("Modbus write failed (set_standby): %s", ex)
            return f"FOUT: standby — {ex}"
        self._last_mode = "standby"
        _LOG.info("MODBUS CONTROL: standby")
        return "Standby (direct Modbus)"

    async def set_discharge_selfuse(self) -> str | None:
        """Battery covers home deficit, PV surplus to grid."""
        return await self.set_auto()

    async def set_solar_charge(self) -> str | None:
        """Charge from PV only, no grid import."""
        ceiling = self._charge_ceiling(self._max_power_w)
        if self._last_mode == f"solar_charge_{ceiling}":
            return None
        try:
            await self._set_storage_mode(3)  # Passive
            await self._write_passive(
                grid_w=0,            # no grid import
                min_bat_w=0,         # no discharge
                max_bat_w=ceiling,   # charge from PV surplus, soft-started
            )
        except Exception as ex:
            _LOG.error("Modbus write failed (set_solar_charge): %s", ex)
            return f"FOUT: solar_charge — {ex}"
        self._last_mode = f"solar_charge_{ceiling}"
        _LOG.info("MODBUS CONTROL: solar charge (PV only, ≤ %d W)", ceiling)
        return "Zonne-laden (direct Modbus)"

    async def set_grid_charge(self, power_w: int | None = None) -> str | None:
        """Grid charge: force charge from grid."""
        return await self.set_charge(power_w)

    async def restore_pv(self) -> None:
        """Restore PV export — no-op in Passive Mode (PV always active)."""
        _LOG.info("MODBUS CONTROL: restore_pv (no-op in Passive Mode)")

    async def get_current_mode(self) -> dict:
        """Read the current battery mode from last known state."""
        return {
            "storageMode": "direct-modbus",
            "saldoxLastMode": self._last_mode,
        }


class HaBatteryController:
    """Controls the Sofar inverter battery via HA service calls.

    DEPRECATED: Use ModbusBatteryController instead. This class is kept
    as a fallback for environments where direct Modbus is not available.

    Uses the Solax integration's energy storage mode and passive mode
    power limits instead of direct Modbus writes.
    """

    def __init__(self, ha: HomeAssistantClient, max_power_w: int = 15000):
        self._ha = ha
        self._max_power_w = max_power_w
        self._last_mode: str | None = None

    async def set_charge(self, power_w: int | None = None) -> str | None:
        """Force-charge battery from grid at given power (default: max).

        Sofar sign convention: positive battery power = charge.
        """
        watts = power_w or self._max_power_w
        if self._last_mode == f"charge_{watts}":
            return None

        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": watts,  # positive = charge up to watts
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": watts,  # positive = force charge at watts
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": watts,  # positive = allow grid import for charging
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        self._last_mode = f"charge_{watts}"
        _LOG.info("CONTROL: force-charge @ %d W via HA Passive Mode (bat=+%d, grid=+%d)", watts, watts, watts)
        return f"Laden {watts} W"

    async def set_discharge(self, power_w: int | None = None) -> str | None:
        """Force-discharge battery to grid at given power (default: max).

        Sofar Passive Mode sign convention (confirmed by testing):
          - Battery power: positive = charge, negative = discharge
          - Grid power: 0 = let inverter decide (surplus → grid)
        All three registers must be negative for discharge to work:
        max_bat = -watts, min_bat = -watts, grid = -watts.
        """
        watts = power_w or self._max_power_w
        if self._last_mode == f"discharge_{watts}":
            return None

        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": 0,  # no charging allowed during discharge
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": -watts,  # negative = force discharge at this power
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": -watts,  # negative = export to grid
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        self._last_mode = f"discharge_{watts}"
        _LOG.info("CONTROL: force-discharge @ %d W via HA Passive Mode (bat=-%d, grid=0)", watts, watts)
        return f"Ontladen {watts} W"

    async def set_discharge_selfuse(self) -> str | None:
        """Battery covers home load deficit, PV surplus → grid. Grid import = 0.

        Baseline mode: no active charging, but battery discharges to prevent
        grid import. PV surplus goes to grid (saldering / export).
        """
        if self._last_mode == "discharge_selfuse":
            return None

        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": 0,  # no charging
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": -self._max_power_w,  # allow discharge to cover load
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": 0,  # target zero grid import
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        self._last_mode = "discharge_selfuse"
        _LOG.info("CONTROL: baseline — no charge, discharge covers deficit, grid=0")
        return "Baseline (grid=0, batterij springt bij)"

    async def set_auto(self) -> str | None:
        """Baseline mode: Passive Mode with grid import = 0.

        Battery doesn't charge, but discharges to cover load deficit.
        PV surplus goes to grid export. This replaces the old Self Use
        mode which ignored passive power registers.
        """
        if self._last_mode == "auto":
            return None

        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": 0,  # no charging
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": -self._max_power_w,  # discharge to cover load
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": 0,  # target zero grid import
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        self._last_mode = "auto"
        _LOG.info("CONTROL: baseline (Passive) — no charge, discharge OK, grid=0")
        return "Baseline (grid=0)"

    async def get_current_mode(self) -> dict:
        """Read the current energy storage mode and power settings from HA."""
        states = await self._ha.get_states([
            _STORAGE_MODE_ENTITY,
            _PASSIVE_MAX_BAT_POWER,
            _PASSIVE_MIN_BAT_POWER,
            _PASSIVE_GRID_POWER,
        ])
        mode_state = states.get(_STORAGE_MODE_ENTITY, {}).get("state", "unknown")
        max_bat = states.get(_PASSIVE_MAX_BAT_POWER, {}).get("state", "0")
        min_bat = states.get(_PASSIVE_MIN_BAT_POWER, {}).get("state", "0")
        grid = states.get(_PASSIVE_GRID_POWER, {}).get("state", "0")
        return {
            "storageMode": mode_state,
            "maxBatPowerW": float(max_bat) if max_bat not in ("unknown", "unavailable") else None,
            "minBatPowerW": float(min_bat) if min_bat not in ("unknown", "unavailable") else None,
            "gridPowerW": float(grid) if grid not in ("unknown", "unavailable") else None,
            "saldoxLastMode": self._last_mode,
        }

    async def set_solar_charge(self) -> str | None:
        """Charge battery from solar only — no grid import.

        Sofar sign convention: max_bat positive = allow charging up to watts.
        min_bat=0 → no forced discharge. Grid=0 → no grid import/export.
        PV surplus goes to battery, remainder to grid.
        """
        if self._last_mode == "solar_charge":
            return None

        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": self._max_power_w,  # positive = allow charge from PV
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": 0,  # no forced discharge
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": 0,  # no grid import
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        self._last_mode = "solar_charge"
        _LOG.info("CONTROL: solar charge via Passive Mode (bat=+%d/0, grid=0)", self._max_power_w)
        return "Zonne-laden (grid=0)"

    async def set_grid_charge(self, power_w: int | None = None) -> str | None:
        """Grid charge: max import from grid, charge battery, PV curtailed.

        Used during negative EPEX prices when exporting PV costs money.
        - Battery charges from grid at max power
        - PV curtailed to 0% to prevent export (active_power_limit)
        - Grid desired = max import (positive = import direction)
        """
        watts = power_w or self._max_power_w
        if self._last_mode == f"grid_charge_{watts}":
            return None

        # Switch to Passive Mode
        await self._ha.call_service("select", "select_option", {
            "entity_id": _STORAGE_MODE_ENTITY,
            "option": "Passive Mode",
        })
        # Battery: force charge at max power
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MAX_BAT_POWER,
            "value": watts,
        })
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_MIN_BAT_POWER,
            "value": watts,  # force charge
        })
        # Grid: max import (positive = import)
        await self._ha.call_service("number", "set_value", {
            "entity_id": _PASSIVE_GRID_POWER,
            "value": watts,  # actively pull from grid
        })
        await self._ha.call_service("button", "press", {
            "entity_id": _PASSIVE_UPDATE_BUTTON,
        })

        # Curtail PV to 0% — prevent export during negative prices
        try:
            await self._ha.call_service("number", "set_value", {
                "entity_id": "number.sofar_inverter_active_power_export_limit",
                "value": 0,
            })
        except Exception:
            _LOG.warning("PV curtail entity not available — skipping")

        self._last_mode = f"grid_charge_{watts}"
        _LOG.info("CONTROL: grid charge @ %dW + PV curtailed (negative price mode)", watts)
        return f"Grid laden {watts}W + PV uit"

    async def restore_pv(self) -> None:
        """Restore PV export limit to 100% after negative price period."""
        try:
            await self._ha.call_service("number", "set_value", {
                "entity_id": "number.sofar_inverter_active_power_export_limit",
                "value": 100,
            })
            _LOG.info("CONTROL: PV export limit restored to 100%%")
        except Exception:
            _LOG.warning("PV restore entity not available — skipping")
