"""Saldox Action Executor — executes EMS plan actions via Modbus.

Watches the current plan's actions and sends Modbus commands when an action's
time window is active. Resets to auto mode when no action is active.

Action mapping:
  ChargeBattery     → battery_mode=force-charge + battery_charge_power=max
  DischargeBattery  → battery_mode=force-discharge + battery_discharge_power=max
  CurtailPv         → active_power_limit=0%
  (others)          → no hardware action (informational only)

Safety:
  - Only writes when the desired state differs from the current state (no spam).
  - Logs every mode transition for auditability.
  - Resets to auto + 100% power limit when no action is active.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .modbus_client import SofarModbusClient
from .registers import by_name

_LOG = logging.getLogger(__name__)

# Modbus register values for battery modes.
_MODE_AUTO = 0
_MODE_FORCE_CHARGE = 1
_MODE_FORCE_DISCHARGE = 2

# Default max charge/discharge power for Sofar HYD (5 kW).
_DEFAULT_MAX_POWER_W = 5000


class ActionExecutor:
    """Executes EMS plan actions by writing Modbus registers."""

    def __init__(self, client: SofarModbusClient, max_power_w: int = _DEFAULT_MAX_POWER_W):
        self._client = client
        self._max_power_w = max_power_w
        # Track last-written state to avoid redundant writes.
        self._last_mode: int | None = None
        self._last_power_limit: int | None = None

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
        """Check the plan and send Modbus commands if needed.

        Returns a short description of what was done, or None if no change.
        """
        if not plan:
            return await self._ensure_auto()

        active = self._find_active_action(plan)

        if active is None:
            return await self._ensure_auto()

        kind = active.get("kind", "")

        if kind == "ChargeBattery":
            return await self._set_charge()
        elif kind == "DischargeBattery":
            return await self._set_discharge()
        elif kind == "CurtailPv":
            return await self._set_curtail()
        else:
            # Informational actions (ChargeCar, RunHeavyLoad) — no Modbus command.
            return await self._ensure_auto()

    async def _set_charge(self) -> str | None:
        """Force-charge battery at max power."""
        changed = False

        if self._last_mode != _MODE_FORCE_CHARGE:
            raw_power = self._max_power_w // 100
            await self._client.write_holding(by_name("battery_charge_power_w"), raw_power)
            await self._client.write_holding(by_name("battery_mode"), _MODE_FORCE_CHARGE)
            self._last_mode = _MODE_FORCE_CHARGE
            changed = True
            _LOG.info("ACTION: force-charge @ %d W", self._max_power_w)

        if self._last_power_limit != 100:
            await self._client.write_holding(by_name("active_power_limit_pct"), 100)
            self._last_power_limit = 100
            changed = True

        return f"Laden {self._max_power_w} W" if changed else None

    async def _set_discharge(self) -> str | None:
        """Force-discharge battery at max power."""
        changed = False

        if self._last_mode != _MODE_FORCE_DISCHARGE:
            raw_power = self._max_power_w // 100
            await self._client.write_holding(by_name("battery_discharge_power_w"), raw_power)
            await self._client.write_holding(by_name("battery_mode"), _MODE_FORCE_DISCHARGE)
            self._last_mode = _MODE_FORCE_DISCHARGE
            changed = True
            _LOG.info("ACTION: force-discharge @ %d W", self._max_power_w)

        if self._last_power_limit != 100:
            await self._client.write_holding(by_name("active_power_limit_pct"), 100)
            self._last_power_limit = 100
            changed = True

        return f"Ontladen {self._max_power_w} W" if changed else None

    async def _set_curtail(self) -> str | None:
        """Curtail PV output to 0%."""
        changed = False

        if self._last_power_limit != 0:
            await self._client.write_holding(by_name("active_power_limit_pct"), 0)
            self._last_power_limit = 0
            changed = True
            _LOG.info("ACTION: curtail PV to 0%%")

        if self._last_mode != _MODE_AUTO:
            await self._client.write_holding(by_name("battery_mode"), _MODE_AUTO)
            self._last_mode = _MODE_AUTO
            changed = True

        return "PV beperkt 0%" if changed else None

    async def _ensure_auto(self) -> str | None:
        """Reset to auto mode + 100% power limit if not already there."""
        changed = False

        if self._last_mode is not None and self._last_mode != _MODE_AUTO:
            await self._client.write_holding(by_name("battery_mode"), _MODE_AUTO)
            self._last_mode = _MODE_AUTO
            changed = True
            _LOG.info("ACTION: reset to auto mode")

        if self._last_power_limit is not None and self._last_power_limit != 100:
            await self._client.write_holding(by_name("active_power_limit_pct"), 100)
            self._last_power_limit = 100
            changed = True
            _LOG.info("ACTION: reset power limit to 100%%")

        return "Auto modus" if changed else None
