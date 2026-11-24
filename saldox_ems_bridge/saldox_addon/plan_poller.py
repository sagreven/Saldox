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
  sensor.{slug}_battery_capacity_kwh — totale accucapaciteit volgens Saldox (kWh)
  sensor.{slug}_battery_pack{N}_capacity_kwh — capaciteit per pack (kWh)

De capaciteits-sensors komen NIET uit de omvormer: de Sofar heeft geen capaciteitsregister
(het Solarman-profiel leest uit het configblok alleen DOD 0x104D, EOD 0x104E en EPS-buffer
0x1052). Ze komen terug uit /api/ha/device-config, waar Saldox ze per pack bijhoudt. Het
totaal volgt dezelfde regel als de planner, zodat HA niet iets anders toont dan het plan.

Per-uur plan-sensors (voor terugkijken/plan-vs-gemeten; HA-recorder bewaart de historie):
  sensor.{slug}_consumption          — gepland verbruik dit uur (W)      — LIVE (last-write-wins)
  sensor.{slug}_pv                   — geplande PV dit uur (W)           — LIVE
  sensor.{slug}_soc                  — geplande SoC dit uur (%)          — LIVE
  sensor.{slug}_grid                 — gepland grid dit uur (W, +import) — LIVE
  sensor.{slug}_price                — EPEX dit uur (EUR/kWh)            — LIVE
  sensor.{slug}_action               — geplande actie dit uur (tekst)   — LIVE
  sensor.{slug}_<metric>_committed   — idem, maar één keer per uur (op :00) weggeschreven als
                                       VASTE referentie (wordt binnen het uur niet herzien).

Elke per-uur-sensor draagt de attributes `for_hour_utc` (voor welk uur dit plan geldt) en
`plan_recomputed_at` (wanneer het plan laatst herberekend is), zodat een terugblik weet welke
versie hij vergelijkt — ook als de planner het uur onderweg meermaals herzien heeft.

De _savings_eur sensor draagt als attributes het volledige plan (timeline,
actions, batterySoC, evSoC) zodat het ingress-dashboard alles kan plotten.
"""
from __future__ import annotations

import asyncio
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable

import aiohttp

from .ha_api import HomeAssistantClient
from .registers import CONFIG_REGISTER_NAMES

_LOG = logging.getLogger(__name__)


def derive_grid_power_w(
    load_w: float | None, pv_w: float | None, battery_w: float | None
) -> float | None:
    """Leid het net-vermogen (PCC) af uit de energiebalans i.p.v. register 0x0488.

    De Sofar HYD PCC-register over-leest tijdens Passive-mode geforceerd laden met ~het
    laadvermogen (firmware-quirk). De drie componenten balanceren wél consistent:

        grid = load − pv − battery_power

    met de add-on-tekenconventie ``battery_power`` − = laden, + = ontladen. Resultaat is
    positief = import, negatief = export (zoals de Saldox-server verwacht).

    Geeft ``None`` als één van de drie ontbreekt, zodat de aanroeper kan terugvallen op de
    ruwe register-waarde. Puur/stateless zodat 'm direct te unit-testen is.
    """
    if load_w is None or pv_w is None or battery_w is None:
        return None
    return load_w - pv_w - battery_w


def build_telemetry_payload(readings: dict) -> dict[str, float]:
    """Bouw de telemetrie-payload uit de Modbus-readings (mapping + per-pack + afgeleide grid).

    Pure functie (geen I/O) zodat de mapping — inclusief de per-pack bat1/bat2-velden — direct
    te unit-testen is. ``readings`` is ``{register_naam: {"value": x, ...}}``.

    Per-pack (2-BDU): bat2 = het +7-offsetblok (0x060D/0x060F). bat1 = het basisblok
    (0x0606/0x0608). GEVERIFIEERD 21-11-2026: ``battery_power_w``/``battery_soc_percent`` zijn
    fysiek BAT1, niet het aggregaat — een aggregaat kan nooit kleiner zijn dan een enkel pack,
    maar battery_power_w (340W) < battery2_power_w (430W). We pushen bat1 daarom óók apart. Het
    bestaande 'aggregaat'-veld (batteryPowerW/batterySoCPercent) laten we bewust ongemoeid i.v.m.
    continuïteit van de server-historie.
    """
    payload: dict[str, float] = {}
    mapping = {
        "battery_soc_percent": "batterySoCPercent",
        "battery_power_w": "batteryPowerW",
        "ev_soc_percent": "evSoCPercent",
        "ev_power_w": "evPowerW",
        "pv_total_power_w": "pvPowerW",
        "load_power_w": "loadPowerW",
        "battery2_power_w": "bat2PowerW",
        "battery2_soc_percent": "bat2SoCPercent",
    }
    for modbus_key, api_key in mapping.items():
        entry = readings.get(modbus_key)
        if entry and entry.get("value") is not None:
            payload[api_key] = float(entry["value"])

    for src_key, bat1_key in (("battery_power_w", "bat1PowerW"), ("battery_soc_percent", "bat1SoCPercent")):
        entry = readings.get(src_key)
        if entry and entry.get("value") is not None:
            payload[bat1_key] = float(entry["value"])

    def _val(key: str) -> float | None:
        e = readings.get(key)
        return float(e["value"]) if e and e.get("value") is not None else None

    # Grid (PCC): afgeleid uit de energiebalans i.p.v. register 0x0488 (zie derive_grid_power_w).
    # LET OP: gebruikt battery_power_w = BAT1 — zodra bat2 actief is mist dit bat2's bijdrage.
    # Bekende beperking (zie 2.6.4-notitie); aggregaat-correctie volgt apart.
    grid = derive_grid_power_w(_val("load_power_w"), _val("pv_total_power_w"), _val("battery_power_w"))
    if grid is not None:
        payload["gridPowerW"] = grid
    else:
        raw = _val("ac_active_power_w")
        if raw is not None:
            payload["gridPowerW"] = raw

    return payload


def build_config_registers(readings: dict) -> list[dict[str, Any]]:
    """Bouw de payload-registers voor /api/ha/device-config uit de Modbus-readings.

    Alleen de namen uit ``CONFIG_REGISTER_NAMES``, en alleen waar een waarde aanwezig is —
    een register dat de firmware niet beantwoordt mag geen 0 worden, want serverside zou
    ``0`` als een echte instelling tellen (een DOD van 0% betekent iets heel anders dan
    "onbekend"). Puur/stateless zodat het direct te testen is.
    """
    entries: list[dict[str, Any]] = []
    for name in CONFIG_REGISTER_NAMES:
        entry = readings.get(name)
        if not entry or entry.get("value") is None:
            continue
        entries.append({
            "key": name,
            "value": float(entry["value"]),
            "unit": entry.get("unit") or None,
        })
    return entries


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
        # Uur (UTC, op het hele uur) waarvoor de committed-snapshot al geschreven is.
        self._committed_hour: datetime | None = None
        # monotonic() van de laatste configpush; None = nog nooit, dus bij start meteen.
        self._last_config_push: float | None = None

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

    # -----------------------------------------------------------------------
    #  Per-uur plan-sensors (voor terugkijken / plan-vs-gemeten)
    # -----------------------------------------------------------------------

    @staticmethod
    def _slot_for_now(timeline: list[dict[str, Any]], now_utc: datetime) -> dict[str, Any] | None:
        """De timeline-slot waarvan het start-uur gelijk is aan het lopende uur (UTC)."""
        hour_start = now_utc.replace(minute=0, second=0, microsecond=0)
        for s in timeline:
            try:
                st = datetime.fromisoformat(s["startUtc"].replace("Z", "+00:00"))
            except (KeyError, ValueError, AttributeError):
                continue
            if st.replace(minute=0, second=0, microsecond=0) == hour_start:
                return s
        return None

    def _action_label_now(self, actions: list[dict[str, Any]], now_utc: datetime) -> str:
        """Label van de actie die NU loopt, of 'idle' als er geen actie geldt."""
        for a in actions:
            try:
                st = datetime.fromisoformat(a["startUtc"].replace("Z", "+00:00"))
                en = datetime.fromisoformat(a["endUtc"].replace("Z", "+00:00"))
            except (KeyError, ValueError, AttributeError):
                continue
            if st <= now_utc < en:
                kind = a.get("kind", "")
                return self._ACTION_LABELS.get(kind, kind) or "idle"
        return "idle"

    # (suffix, waarde-key, unit, device_class) — action wordt apart afgehandeld.
    _HOUR_NUMERIC = (
        ("consumption", "consumptionWatts", "W", "power"),
        ("pv", "pvWatts", "W", "power"),
        ("soc", "socPercent", "%", "battery"),
        ("grid", "gridWatts", "W", "power"),
        ("price", "priceEurKwh", "EUR/kWh", "monetary"),
    )

    async def _publish_hour_sensors(
        self, timeline: list[dict[str, Any]], actions: list[dict[str, Any]],
        now_utc: datetime, fetched_at: str,
    ) -> None:
        """Publiceer de plan-waarden van het lopende uur als HA-sensors.

        Live sensors worden elke tick overschreven (last-write-wins). De committed-sensors
        worden één keer per uur (de eerste tick ná het hele uur) weggeschreven en daarna
        binnen dat uur NIET meer herzien — een vaste referentie voor de terugblik.
        """
        slot = self._slot_for_now(timeline, now_utc)
        if slot is None:
            return

        hour_start = now_utc.replace(minute=0, second=0, microsecond=0)
        attrs = {
            "for_hour_utc": hour_start.isoformat(),
            "plan_recomputed_at": fetched_at,
            "source": "saldox-api",
        }
        do_commit = self._committed_hour != hour_start

        async def write(suffix: str, value: Any, unit: str | None, dclass: str | None, numeric: bool) -> None:
            await self._ha.post_state(
                entity_id=f"sensor.{self._slug}_{suffix}",
                state=value if value is not None else "unknown",
                unit=unit if (unit and value is not None) else None,
                friendly_name=f"{self._friendly} {suffix.replace('_', ' ')} (plan)",
                device_class=dclass if value is not None else None,
                state_class="measurement" if numeric else None,
                extra_attrs=attrs,
            )
            if do_commit:
                await self._ha.post_state(
                    entity_id=f"sensor.{self._slug}_{suffix}_committed",
                    state=value if value is not None else "unknown",
                    unit=unit if (unit and value is not None) else None,
                    friendly_name=f"{self._friendly} {suffix.replace('_', ' ')} committed (plan)",
                    device_class=dclass if value is not None else None,
                    state_class="measurement" if numeric else None,
                    extra_attrs={**attrs, "committed": True},
                )

        for suffix, key, unit, dclass in self._HOUR_NUMERIC:
            val = slot.get(key)
            await write(suffix, round(val, 3) if isinstance(val, (int, float)) else val, unit, dclass, True)
        await write("action", self._action_label_now(actions, now_utc), "", None, False)

        if do_commit:
            self._committed_hour = hour_start
            _LOG.info("Plan committed-snapshot geschreven voor uur %s", attrs["for_hour_utc"])

    async def _push_telemetry(self) -> None:
        """Push current Modbus readings to Saldox API for pattern learning."""
        if not self._get_readings:
            return
        readings = self._get_readings()
        if not readings:
            return

        # Mapping (incl. per-pack bat1/bat2) + afgeleide grid: zie build_telemetry_payload (puur/testbaar).
        payload = build_telemetry_payload(readings)
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

    async def _push_device_config(self) -> None:
        """Push de CONFIGREGISTERS van de omvormer en publiceer Saldox' accu-beeld in HA.

        Traag pad: bij start en daarna 1x per _CONFIG_PUSH_SECONDS. Deze registers zijn
        instellingen (DOD 0x104D, EOD 0x104E, EPS-buffer 0x1052) en veranderen alleen als
        iemand ze wijzigt, dus ze horen niet in de regellus — de Modbus-bus is FC03-only en
        bevriest bij drukte.

        Het antwoord bevat de capaciteit per pack en het totaal zoals Saldox die kent. Die
        publiceren we als HA-sensors, want in HAOS was de accucapaciteit nergens te zien: de
        omvormer heeft er simpelweg geen register voor. Het totaal komt uit dezelfde regel als
        de planner gebruikt, zodat HA niet iets anders toont dan waar het plan mee rekent.
        """
        if not self._get_readings:
            return
        readings = self._get_readings()
        if not readings:
            return

        entries = build_config_registers(readings)

        session = await self._get_session()
        url = f"{self._api_url}/api/ha/device-config"
        try:
            async with session.post(
                url, json={"registers": entries}, timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                if resp.status != 200:
                    _LOG.warning("Device-config push HTTP %s", resp.status)
                    return
                data = await resp.json()
        except aiohttp.ClientError as ex:
            _LOG.warning("Device-config push failed: %s", ex)
            return

        changes = data.get("changes") or []
        if changes:
            _LOG.info("Device-config: %s", " | ".join(str(c) for c in changes))
        else:
            _LOG.debug("Device-config: %d registers gepusht, geen wijzigingen", len(entries))

        battery = data.get("battery") or {}
        packs = battery.get("packs") or []
        common = {
            "source": "saldox-api",
            "pack_count": len(packs),
            "dod_percent": next((e["value"] for e in entries if e["key"] == "battery_dod_percent"), None),
            "eps_buffer_percent": next(
                (e["value"] for e in entries if e["key"] == "battery_eps_buffer_percent"), None),
        }

        async def write(suffix: str, value: Any, extra: dict[str, Any]) -> None:
            await self._ha.post_state(
                entity_id=f"sensor.{self._slug}_{suffix}",
                state=value if value is not None else "unknown",
                unit="kWh" if value is not None else None,
                friendly_name=f"{self._friendly} {suffix.replace('_', ' ')}",
                device_class="energy_storage" if value is not None else None,
                state_class="measurement",
                extra_attrs=extra,
            )

        await write("battery_capacity_kwh", battery.get("totalKwh"), common)
        for pack in packs:
            idx = pack.get("index")
            if idx is None:
                continue
            await write(
                f"battery_pack{idx}_capacity_kwh",
                pack.get("capacityKwh"),
                {**common, "pack_name": pack.get("name")},
            )

    async def tick(self) -> None:
        # Push live readings to Saldox for pattern learning.
        await self._push_telemetry()

        # Configregisters: traag, los van de telemetrie-cadans.
        now = time.monotonic()
        if self._last_config_push is None or (now - self._last_config_push) >= self._CONFIG_PUSH_SECONDS:
            self._last_config_push = now
            await self._push_device_config()

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

        # Per-uur plan-sensors (live + committed-snapshot) voor terugkijken/plan-vs-gemeten.
        await self._publish_hour_sensors(timeline, actions, datetime.now(timezone.utc), fetched_at)

        # Fetch savings history and merge into plan data for the dashboard.
        savings_history = await self._fetch_savings()
        if savings_history:
            plan["savingsHistory"] = savings_history

        if self._on_update:
            self._on_update(plan)

    # EV charging state detection thresholds.
    _EV_CHARGING_THRESHOLD_W = 100  # power above this = charging
    _CHARGING_POLL_SECONDS = 300     # 5 min while charging
    # Configregisters zijn instellingen: 1x/24u is ruim genoeg en houdt de Modbus-bus vrij.
    _CONFIG_PUSH_SECONDS = 86400

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
