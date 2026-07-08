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
    ):
        self._ha = ha
        self._api_url = saldox_api_url.rstrip("/")
        self._api_token = saldox_api_token
        self._slug = slug
        self._friendly = friendly
        self._poll_seconds = max(60, poll_minutes * 60)
        self._session: aiohttp.ClientSession | None = None
        self._on_update = on_update

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_token}"}
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch_plan(self) -> dict[str, Any] | None:
        """Fetch the 48h EMS plan from the Saldox API.

        Returns the full plan dict, or None on error.
        """
        session = await self._get_session()
        url = f"{self._api_url}/api/ems/plan"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    _LOG.warning("Saldox plan API %s -> HTTP %s", url, resp.status)
                    return None
                return await resp.json()
        except aiohttp.ClientError as ex:
            _LOG.warning("Saldox plan API fetch failed: %s", ex)
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
        "RunHeavyLoad": "Zwaar verbruik",
    }

    async def tick(self) -> None:
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

        if self._on_update:
            self._on_update(plan)

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as ex:  # noqa: BLE001
                _LOG.error("Plan poll failed: %s\n%s", ex, traceback.format_exc())
            await asyncio.sleep(self._poll_seconds)
