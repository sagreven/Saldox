"""Saldox EMS Plan poller voor Home Assistant.

Haalt het 48-uur energieplan op via de Saldox API en publiceert het als HA
sensors. Het plan bevat een timeline (48 uurslots met PV, verbruik, prijs),
acties (laden/ontladen batterij, auto laden), SoC-curves en besparingen.

Gepubliceerde entities (slug standaard `saldox_plan`):
  sensor.{slug}_savings_eur          — verwachte besparing komende 48h
  sensor.{slug}_optimized_cost_eur   — geoptimaliseerde kosten
  sensor.{slug}_naive_cost_eur       — kosten zonder optimalisatie
  sensor.{slug}_next_action          — eerstvolgende geplande actie (tekst)
  sensor.{slug}_battery_soc_pct      — geplande batterij SoC nu (%)

De _savings_eur sensor draagt als attributes het volledige plan (timeline,
actions, batterySoC, evSoC) zodat het ingress-dashboard alles kan plotten.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Callable

import aiohttp

from .ha_api import HomeAssistantClient

_LOG = logging.getLogger(__name__)


class PlanPoller:
    """Pollt de Saldox EMS plan API en pusht samenvatting naar HA."""

    def __init__(
        self,
        ha: HomeAssistantClient,
        saldox_api_url: str,
        saldox_api_token: str,
        slug: str = "saldox_plan",
        friendly: str = "Saldox plan",
        poll_minutes: int = 5,
        on_update: Callable[[dict[str, Any]], None] | None = None,
        get_readings: Callable[[], dict[str, dict]] | None = None,
    ):
        self._ha = ha
        self._api_url = saldox_api_url.rstrip("/")
        self._api_token = saldox_api_token
        self._slug = slug
        self._friendly = friendly
        self._poll_seconds = max(60, poll_minutes * 60)
        self._session: aiohttp.ClientSession | None = None
        self._on_update = on_update
        self._get_readings = get_readings
        self._get_hourly_usage: Callable[[], list[dict]] | None = None

    def set_hourly_usage_source(self, fn: Callable[[], list[dict]]) -> None:
        """Set callback that returns completed hourly usage entries."""
        self._get_hourly_usage = fn

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_token}"}
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _current_soc_params(self) -> dict[str, str]:
        """Read current battery and EV SoC from Modbus readings to send to the API."""
        if not self._get_readings:
            return {}
        readings = self._get_readings()
        params: dict[str, str] = {}
        # Battery SoC from Modbus register "battery_soc_percent"
        bat = readings.get("battery_soc_percent")
        if bat and bat.get("value") is not None:
            params["batterySoCPercent"] = str(bat["value"])
        # EV SoC — if available from a future Modbus register or HA sensor
        ev = readings.get("ev_soc_percent")
        if ev and ev.get("value") is not None:
            params["evSoCPercent"] = str(ev["value"])
        return params

    async def _fetch_plan(self) -> dict[str, Any] | None:
        """Fetch the 48h EMS plan from the Saldox API.

        Sends current battery/EV SoC as query params so the planner
        can align the plan with the actual hardware state.

        Returns the full plan dict, or None on error.
        """
        session = await self._get_session()
        url = f"{self._api_url}/api/ems/plan"
        params = self._current_soc_params()
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    _LOG.warning("Saldox plan API %s -> HTTP %s", url, resp.status)
                    return None
                data = await resp.json()
                if params:
                    _LOG.info("Plan fetched with live SoC: %s", params)
                return data
        except aiohttp.ClientError as ex:
            _LOG.warning("Saldox plan API fetch failed: %s", ex)
            return None

    async def _fetch_savings(self) -> dict[str, Any] | None:
        """Fetch daily savings history from Saldox API."""
        session = await self._get_session()
        url = f"{self._api_url}/api/ems/savings"
        try:
            async with session.get(url, params={"days": "30"}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
        except aiohttp.ClientError:
            return None

    @staticmethod
    def _find_next_action(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find the first action that hasn't ended yet."""
        now = datetime.now(timezone.utc)
        future = []
        for a in actions:
            try:
                end = datetime.fromisoformat(a["endUtc"].replace("Z", "+00:00"))
                if end > now:
                    start = datetime.fromisoformat(a["startUtc"].replace("Z", "+00:00"))
                    future.append((start, a))
            except (KeyError, ValueError):
                continue
        if not future:
            return None
        future.sort(key=lambda x: x[0])
        return future[0][1]

    @staticmethod
    def _current_soc_pct(soc_curve: list[dict[str, Any]]) -> float | None:
        """Interpolate the planned battery SoC percentage for right now."""
        if not soc_curve:
            return None
        now = datetime.now(timezone.utc)
        prev = None
        for point in soc_curve:
            try:
                ts = datetime.fromisoformat(point["timestampUtc"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if ts >= now:
                cap = point.get("capacityKwh", 1)
                if cap <= 0:
                    cap = 1
                return round(point["soCKwh"] / cap * 100, 1)
            prev = point
        # Past the last point — return the last value.
        if prev:
            cap = prev.get("capacityKwh", 1)
            if cap <= 0:
                cap = 1
            return round(prev["soCKwh"] / cap * 100, 1)
        return None

    # Map API action kind names to Dutch display labels.
    _ACTION_LABELS = {
        "ChargeBattery": "Batterij laden",
        "DischargeBattery": "Batterij ontladen",
        "ChargeCar": "Auto laden",
        "CurtailPv": "PV beperken",
        "ExportToGrid": "Export naar net",
        "SolarCharge": "Zonne-laden",
    }

    async def _push_telemetry(self) -> None:
        """Push current Modbus readings to Saldox API for pattern learning."""
        if not self._get_readings:
            return
        readings = self._get_readings()
        if not readings:
            return

        payload: dict[str, float] = {}
        # Map Modbus register names to telemetry fields.
        mapping = {
            "battery_soc_percent": "batterySoCPercent",
            "battery_power_w": "batteryPowerW",
            "ev_soc_percent": "evSoCPercent",
            "ev_power_w": "evPowerW",
            "pv_total_power_w": "pvPowerW",
            "ac_active_power_w": "gridPowerW",
            "load_power_w": "loadPowerW",
        }
        for modbus_key, api_key in mapping.items():
            entry = readings.get(modbus_key)
            if entry and entry.get("value") is not None:
                payload[api_key] = float(entry["value"])

        if not payload:
            return

        # Include completed hourly usage data if available.
        if self._get_hourly_usage:
            hourly = self._get_hourly_usage()
            if hourly:
                payload["hourlyUsage"] = hourly
                _LOG.info("Telemetry includes %d hourly usage entries", len(hourly))

        session = await self._get_session()
        url = f"{self._api_url}/api/ha/telemetry"
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOG.debug("Telemetry pushed: %d readings stored", data.get("stored", 0))
                else:
                    _LOG.warning("Telemetry push HTTP %s", resp.status)
        except aiohttp.ClientError as ex:
            _LOG.warning("Telemetry push failed: %s", ex)

    async def tick(self) -> None:
        # Push live readings to Saldox for pattern learning.
        await self._push_telemetry()

        plan = await self._fetch_plan()
        if plan is None:
            return

        savings = plan.get("totalSavingsEur")
        optimized = plan.get("optimizedCostEur")
        naive = plan.get("naiveCostEur")
        actions = plan.get("actions") or []
        battery_soc = plan.get("batterySoC") or []
        ev_soc = plan.get("evSoC") or []
        timeline = plan.get("timeline") or []

        next_action = self._find_next_action(actions)
        soc_pct = self._current_soc_pct(battery_soc)

        fetched_at = datetime.now(timezone.utc).isoformat()

        # Full plan as attributes on the savings sensor.
        full_attrs = {
            "timeline": timeline,
            "actions": actions,
            "battery_soc": battery_soc,
            "ev_soc": ev_soc,
            "naive_cost_eur": naive,
            "optimized_cost_eur": optimized,
            "from_utc": plan.get("fromUtc"),
            "to_utc": plan.get("toUtc"),
            "source": "saldox-api",
            "fetched_at_utc": fetched_at,
        }

        common = {"source": "saldox-api", "fetched_at_utc": fetched_at}

        async def push(
            suffix: str,
            value: Any,
            unit: str = "EUR",
            device_class: str | None = "monetary",
            state_class: str | None = "measurement",
            extra: dict[str, Any] | None = None,
        ) -> None:
            entity = f"sensor.{self._slug}_{suffix}"
            await self._ha.post_state(
                entity_id=entity,
                state=value if value is not None else "unknown",
                unit=unit if value is not None else None,
                friendly_name=f"{self._friendly} {suffix.replace('_', ' ')}",
                device_class=device_class if value is not None else None,
                state_class=state_class,
                extra_attrs=extra,
            )

        await push("savings_eur", round(savings, 2) if savings is not None else None, extra=full_attrs)
        await push("optimized_cost_eur", round(optimized, 2) if optimized is not None else None, extra=common)
        await push("naive_cost_eur", round(naive, 2) if naive is not None else None, extra=common)
        await push(
            "battery_soc_pct", soc_pct,
            unit="%", device_class="battery", state_class="measurement",
            extra=common,
        )

        # Next action as a text sensor.
        if next_action:
            kind = next_action.get("kind", "")
            label = self._ACTION_LABELS.get(kind, kind)
            try:
                start_dt = datetime.fromisoformat(next_action["startUtc"].replace("Z", "+00:00"))
                start_local = start_dt.strftime("%H:%M")
            except (KeyError, ValueError):
                start_local = "?"
            action_text = f"{label} om {start_local}"
            action_attrs = {
                **common,
                "kind": kind,
                "start_utc": next_action.get("startUtc"),
                "end_utc": next_action.get("endUtc"),
                "kwh": next_action.get("kwh"),
                "savings_eur": next_action.get("eurSavings"),
                "rationale": next_action.get("rationale"),
                "risk": next_action.get("risk"),
            }
        else:
            action_text = "Geen acties gepland"
            action_attrs = common

        await push(
            "next_action", action_text,
            unit="", device_class=None, state_class=None,
            extra=action_attrs,
        )

        _LOG.info(
            "Plan update: savings=€%.2f, optimized=€%.2f, naive=€%.2f, actions=%d, next=%s",
            savings or 0, optimized or 0, naive or 0, len(actions),
            action_text,
        )

        # Fetch savings history and merge into plan data for the dashboard.
        savings_history = await self._fetch_savings()
        if savings_history:
            plan["savingsHistory"] = savings_history

        if self._on_update:
            self._on_update(plan)

    # EV charging state detection thresholds.
    _EV_CHARGING_THRESHOLD_W = 100  # power above this = charging
    _CHARGING_POLL_SECONDS = 300     # 5 min while charging

    def _is_ev_charging(self) -> bool:
        """Detect if an EV is currently charging from Modbus power readings."""
        if not self._get_readings:
            return False
        readings = self._get_readings()
        # Check for dedicated EV power reading or high grid import.
        ev = readings.get("ev_power_w")
        if ev and ev.get("value") is not None and float(ev["value"]) > self._EV_CHARGING_THRESHOLD_W:
            return True
        # Fallback: check battery_power — large negative = discharge,
        # but we can't distinguish EV from other loads without a dedicated sensor.
        return False

    async def run(self) -> None:
        was_charging = False
        while True:
            try:
                is_charging = self._is_ev_charging()

                # State change: car just connected/started → immediate recalc.
                if is_charging and not was_charging:
                    _LOG.info("EV charging detected — forcing immediate plan recalculation")

                was_charging = is_charging
                await self.tick()
            except Exception as ex:  # noqa: BLE001
                _LOG.error("Plan poll failed: %s\n%s", ex, traceback.format_exc())

            # Shorter interval while EV is charging for adaptive control.
            sleep_seconds = self._CHARGING_POLL_SECONDS if was_charging else self._poll_seconds
            await asyncio.sleep(sleep_seconds)
