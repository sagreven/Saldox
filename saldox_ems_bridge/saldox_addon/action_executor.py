"""Saldox Action Executor — executes EMS plan actions.

Watches the current plan's actions and sends commands when an action's
time window is active. Supports both direct Modbus and HA service call
control backends.

Action mapping:
  ChargeBattery     → force-charge at max power (Passive Mode, grid import)
  DischargeBattery  → Self Use mode (battery covers home deficit naturally)
  ExportToGrid      → force-discharge to grid (Passive Mode, grid export)
  CurtailPv         → Self Use (no PV curtailment via HA)
  (others)          → Self Use (informational only)

Key distinction:
  DischargeBattery = let battery cover home needs (Self Use, no grid export)
  ExportToGrid     = actively push power to grid for arbitrage

Safety:
  - Only writes when the desired state differs from the current state (no spam).
  - Logs every mode transition for auditability.
  - Resets to auto when no action is active.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

_LOG = logging.getLogger(__name__)


class BatteryController(Protocol):
    """Abstract interface for battery control backends."""
    async def set_charge(self, power_w: int | None = None) -> str | None: ...
    async def set_discharge(self, power_w: int | None = None) -> str | None: ...
    async def set_auto(self) -> str | None: ...


class ActionExecutor:
    """Executes EMS plan actions via a battery controller backend."""

    def __init__(self, controller: BatteryController):
        self._ctrl = controller

    def _find_active_action(self, plan: dict[str, Any]) -> dict[str, Any] | None:
        """Find the action whose time window covers 'now'."""
        actions = plan.get("actions") or []
        now = datetime.now(timezone.utc)
        for a in actions:
            try:
                start = datetime.fromisoformat(a["startUtc"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(a["endUtc"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if start <= now < end:
                return a
        return None

    async def execute(self, plan: dict[str, Any]) -> str | None:
        """Check the plan and send commands if needed.

        Returns a short description of what was done, or None if no change.
        """
        if not plan:
            return await self._ctrl.set_auto()

        active = self._find_active_action(plan)

        if active is None:
            return await self._ctrl.set_auto()

        kind = active.get("kind", "")

        if kind == "ChargeBattery":
            return await self._ctrl.set_charge()
        elif kind == "DischargeBattery":
            # Self Use mode: battery naturally covers home consumption deficit.
            # Sofar discharges only what the home needs — no grid export.
            return await self._ctrl.set_auto()
        elif kind == "ExportToGrid":
            # Force-discharge to grid for price arbitrage.
            return await self._ctrl.set_discharge()
        elif kind == "CurtailPv":
            return await self._ctrl.set_auto()
        else:
            return await self._ctrl.set_auto()
