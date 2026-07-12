"""Saldox Action Executor — executes EMS plan actions.

Watches the current plan's actions and sends commands when an action's
time window is active. Supports both direct Modbus and HA service call
control backends.

Action mapping:
  ChargeBattery     → force-charge at max power (Passive Mode, grid import)
  DischargeBattery  → Passive Mode (battery covers deficit, PV surplus → grid)
  ExportToGrid      → force-discharge to grid (Passive Mode, grid export)
  SolarCharge       → charge from PV only (no grid import)
  CurtailPv         → baseline (no PV curtailment via HA)
  (no action)       → baseline: Passive Mode, grid=0, no charge, discharge OK

Key distinction:
  DischargeBattery = battery covers home deficit, PV surplus → grid (saldering)
  ExportToGrid     = actively push power to grid for arbitrage

Baseline mode (when no action is active):
  - Passive Mode with desired_grid_power=0
  - max_battery_power=0 (no charging)
  - min_battery_power=-max (battery discharges to cover load, grid import=0)
  - PV surplus goes to grid export

SoC auto-stop:
  - ChargeBattery stops when SoC >= charge target (default 95%).
  - ExportToGrid stops when SoC <= discharge floor (default 10%).
  - On stop, transitions to baseline mode (not Self Use).

Safety:
  - Only writes when the desired state differs from the current state (no spam).
  - Logs every mode transition for auditability.
  - Resets to baseline when no action is active.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

_LOG = logging.getLogger(__name__)

# SoC thresholds for auto-stop (percent of capacity).
SOC_CHARGE_STOP_PCT = 95.0    # stop grid-charging when SoC >= this
SOC_DISCHARGE_STOP_PCT = 10.0 # stop discharging when SoC <= this


class BatteryController(Protocol):
    """Abstract interface for battery control backends."""
    async def set_charge(self, power_w: int | None = None) -> str | None: ...
    async def set_discharge(self, power_w: int | None = None) -> str | None: ...
    async def set_discharge_selfuse(self) -> str | None: ...
    async def set_auto(self) -> str | None: ...
    async def set_solar_charge(self) -> str | None: ...
    async def set_grid_charge(self, power_w: int | None = None) -> str | None: ...
    async def restore_pv(self) -> None: ...


class ExecutionLog:
    """Records plan action execution results for monitoring."""

    def __init__(self, max_entries: int = 200):
        self._entries: list[dict[str, Any]] = []
        self._max = max_entries

    def record(self, action: dict[str, Any], result: str | None,
               soc_percent: float | None, status: str = "executed") -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": action.get("kind", ""),
            "startUtc": action.get("startUtc", ""),
            "endUtc": action.get("endUtc", ""),
            "kwh": action.get("kwh", 0),
            "powerW": action.get("powerW") or action.get("power_w"),
            "status": status,  # executed, skipped_soc, failed, overridden
            "result": result,
            "socPercent": soc_percent,
        }
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries = self._entries[-self._max:]
        _LOG.info("EXEC_LOG: %s %s → %s (SoC=%.1f%%)",
                  entry["kind"], entry["status"], result or "no-op",
                  soc_percent or 0)

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    @property
    def last(self) -> dict[str, Any] | None:
        return self._entries[-1] if self._entries else None


class ActionExecutor:
    """Executes EMS plan actions via a battery controller backend."""

    def __init__(self, controller: BatteryController):
        self._ctrl = controller
        self.log = ExecutionLog()
        self._last_kind: str | None = None

    # Priority order: higher = wins when multiple actions overlap.
    _KIND_PRIORITY = {
        "ExportToGrid": 100,
        "ChargeBattery": 90,
        "SolarCharge": 50,
        "DischargeBattery": 40,
        "ChargeCar": 30,
        "CurtailPv": 10,
    }

    def _find_active_action(self, plan: dict[str, Any]) -> dict[str, Any] | None:
        """Find the highest-priority action whose time window covers 'now'."""
        actions = plan.get("actions") or []
        now = datetime.now(timezone.utc)
        candidates = []
        for a in actions:
            try:
                start = datetime.fromisoformat(a["startUtc"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(a["endUtc"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if start <= now < end:
                candidates.append(a)
        if not candidates:
            return None
        # Return the highest-priority action when multiple overlap.
        return max(candidates, key=lambda a: self._KIND_PRIORITY.get(a.get("kind", ""), 0))

    async def execute(self, plan: dict[str, Any],
                      current_soc_percent: float | None = None) -> str | None:
        """Check the plan and send commands if needed.

        Args:
            plan: The current EMS plan dict (with "actions" list).
            current_soc_percent: Live battery SoC (0-100). Used for auto-stop.

        Returns a short description of what was done, or None if no change.
        """
        if not plan:
            return await self._ctrl.set_auto()

        active = self._find_active_action(plan)

        if active is None:
            return await self._ctrl.set_auto()

        kind = active.get("kind", "")
        power_w = active.get("powerW") or active.get("power_w")
        power_w = int(power_w) if power_w is not None else None

        # SoC auto-stop: abort charge/discharge when target reached.
        if current_soc_percent is not None:
            if kind == "ChargeBattery" and current_soc_percent >= SOC_CHARGE_STOP_PCT:
                _LOG.info("SOC_STOP: SoC %.1f%% >= %.0f%% — stop charging, switch to auto",
                          current_soc_percent, SOC_CHARGE_STOP_PCT)
                self.log.record(active, "SoC stop — auto", current_soc_percent, "skipped_soc")
                return await self._ctrl.set_auto()
            if kind == "ExportToGrid" and current_soc_percent <= SOC_DISCHARGE_STOP_PCT:
                _LOG.info("SOC_STOP: SoC %.1f%% <= %.0f%% — stop discharging, switch to auto",
                          current_soc_percent, SOC_DISCHARGE_STOP_PCT)
                self.log.record(active, "SoC stop — auto", current_soc_percent, "skipped_soc")
                return await self._ctrl.set_auto()

        result: str | None = None
        if kind == "ChargeBattery":
            result = await self._ctrl.set_charge(power_w=power_w)
        elif kind == "GridCharge":
            result = await self._ctrl.set_grid_charge(power_w=power_w)
        elif kind == "DischargeBattery":
            result = await self._ctrl.set_discharge_selfuse()
        elif kind == "ExportToGrid":
            result = await self._ctrl.set_discharge(power_w=power_w)
        elif kind == "SolarCharge":
            result = await self._ctrl.set_solar_charge()
        elif kind == "CurtailPv":
            result = await self._ctrl.set_grid_charge(power_w=power_w)
        else:
            result = await self._ctrl.set_auto()

        # Restore PV when transitioning away from curtail/grid-charge modes
        if kind not in ("CurtailPv", "GridCharge") and self._last_kind in ("CurtailPv", "GridCharge"):
            await self._ctrl.restore_pv()
        self._last_kind = kind

        if result is not None:
            self.log.record(active, result, current_soc_percent, "executed")
        return result
