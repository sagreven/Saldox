"""Saldox EMS Bridge — main entry point.

Doet drie dingen tegelijk:
  1. Modbus-poll loop — leest elke N seconden de Sofar HYD register-map en pusht
     de waardes naar Home Assistant als `sensor.{slug}_*`.
  2. Webhook server — luistert op port 8765 voor Saldox commands (start/stop
     batterij-mode, max-power limit, force-charge/discharge).
  3. Heartbeat-callback (optioneel) — pingt Saldox bij significante events.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from contextlib import suppress
from typing import Any

import aiohttp
from aiohttp import web

from .action_executor import ActionExecutor
from .arbitrage_optimizer import ArbitrageConfig, ArbitrageOptimizer
from .arbitrage_simulator import (
    HourSlot, PlannedLoad, enrich_slots_with_profiles, generate_synthetic_dataset,
    run_full_simulation, parameter_sweep,
    schedule_multiple_loads, format_schedule_table,
    format_comparison_table, format_daily_breakdown, format_sweep_table,
    fetch_prices_from_api, parse_api_prices,
    APPLIANCE_PROFILES,
)
from .ha_api import HomeAssistantClient
from .ha_sensor_reader import HaBatteryController, HaSensorReader, ModbusBatteryController
from .modbus_client import SofarModbusClient
from .plan_poller import PlanPoller
from .prices_poller import PricesPoller
from .registers import by_name

_LOG = logging.getLogger("saldox_addon")

# Mapping: Modbus-register name → HA sensor-suffix + device_class + state_class.
# State-class "measurement" voor momentane waardes, "total_increasing" voor
# lifetime energy counters. Sensor-suffix wordt gecombineerd met device_slug
# tot sensor.{slug}_{suffix} zodat Saldox z'n bestaande driver (die zoekt naar
# sensor.{slug}_power, _today_kwh, _total_kwh) er meteen mee werkt.
SENSOR_MAP = {
    # name in registers.py     suffix             device_class       state_class
    "pv_total_power_w":       ("power",          "power",           "measurement"),
    "ac_active_power_w":      ("grid_power",     "power",           "measurement"),
    "battery_soc_percent":    ("battery_soc",    "battery",         "measurement"),
    "battery_power_w":        ("battery_power",  "power",           "measurement"),
    "today_production_kwh":   ("today_kwh",      "energy",          "total_increasing"),
    "total_production_kwh":   ("total_kwh",      "energy",          "total_increasing"),
    "today_import_kwh":       ("today_import_kwh","energy",         "total_increasing"),
    "today_export_kwh":       ("today_export_kwh","energy",         "total_increasing"),
    "today_consumption_kwh":  ("today_consumption_kwh","energy",    "total_increasing"),
    "battery_input_today_kwh":("battery_in_today_kwh","energy",    "total_increasing"),
    "battery_output_today_kwh":("battery_out_today_kwh","energy",  "total_increasing"),
    "inverter_temperature_c": ("temperature",    "temperature",     "measurement"),
    "inverter_status":        ("status",         None,              None),
    "battery_voltage_v":      ("battery_voltage","voltage",         "measurement"),
    # New sensors — full inverter coverage without Solax integration
    "battery_temperature_c":  ("battery_temperature", "temperature","measurement"),
    "battery_soh_percent":    ("battery_soh",    None,              "measurement"),
    "battery_cycles":         ("battery_cycles", None,              "total_increasing"),
    "load_power_w":           ("load_power",     "power",           "measurement"),
    "pv1_power_w":            ("pv1_power",      "power",           "measurement"),
    "pv2_power_w":            ("pv2_power",      "power",           "measurement"),
    "ac_frequency_hz":        ("grid_frequency", "frequency",       "measurement"),
    "grid_frequency_hz":      ("grid_frequency_raw", "frequency",   "measurement"),
    "inverter_fault_code":    ("fault_code",     None,              None),
    "pv1_voltage_v":          ("pv1_voltage",    "voltage",         "measurement"),
    "pv1_current_a":          ("pv1_current",    "current",         "measurement"),
    "pv2_voltage_v":          ("pv2_voltage",    "voltage",         "measurement"),
    "pv2_current_a":          ("pv2_current",    "current",         "measurement"),
}


# Shared state: latest poll results, updated by poll_loop, read by /status endpoint.
_latest: dict[str, dict] = {}
_latest_ts: float = 0.0

# Shared state: latest price data, updated by PricesPoller via set_prices().
_latest_prices: dict[str, dict] = {}

# Shared state: latest EMS plan, updated by PlanPoller via set_plan().
_latest_plan: dict[str, Any] = {}

# Action executor: set by main() once Modbus client is ready.
_executor: ActionExecutor | None = None
# Last executor action description (for /status).
_executor_status: str = "Wachten op plan"

# Manual override: when set, executor ignores plan and follows this instead.
# Format: {"mode": "auto"|"charge"|"discharge"|"standby", "power_pct": 0-100}
_manual_override: dict[str, Any] = {"mode": "auto", "power_pct": 100}
_ha_controller: Any = None  # set by main()
_plan_poller: Any = None    # set by main() — for forced refreshes
_arbitrage_optimizer: ArbitrageOptimizer | None = None  # set by main()

# ---------------------------------------------------------------------------
# Hourly PV accumulator — tracks average power per hour per string (today).
# Resets at midnight. Each entry: {hour: {samples: N, total: W, pv1: W, pv2: W}}
# ---------------------------------------------------------------------------
_pv_hourly: dict[int, dict[str, float]] = {}
_pv_hourly_date: str = ""  # ISO date string for reset detection


def _accumulate_pv(readings: dict[str, dict]) -> None:
    """Record a PV snapshot into the hourly accumulator."""
    global _pv_hourly_date
    from datetime import datetime
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if today != _pv_hourly_date:
        _pv_hourly.clear()
        _pv_hourly_date = today
    hour = now.hour
    total = readings.get("pv_total_power_w", {}).get("value", 0) or 0
    pv1 = readings.get("pv1_power_w", {}).get("value", 0) or 0
    pv2 = readings.get("pv2_power_w", {}).get("value", 0) or 0
    total = float(total)
    pv1 = float(pv1)
    pv2 = float(pv2)
    if hour not in _pv_hourly:
        _pv_hourly[hour] = {"samples": 0, "total": 0.0, "pv1": 0.0, "pv2": 0.0}
    bucket = _pv_hourly[hour]
    bucket["samples"] += 1
    bucket["total"] += total
    bucket["pv1"] += pv1
    bucket["pv2"] += pv2


# ---------------------------------------------------------------------------
# Hourly consumption accumulator — tracks average load power per hour (today).
# ---------------------------------------------------------------------------
_load_hourly: dict[int, dict[str, float]] = {}
_load_hourly_date: str = ""


def _accumulate_load(readings: dict[str, dict]) -> None:
    """Record a load/consumption snapshot into the hourly accumulator."""
    global _load_hourly_date
    from datetime import datetime
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if today != _load_hourly_date:
        _load_hourly.clear()
        _load_hourly_date = today
    hour = now.hour
    load = readings.get("load_power_w", {}).get("value", 0) or 0
    load = float(load)
    if hour not in _load_hourly:
        _load_hourly[hour] = {"samples": 0, "total": 0.0, "temp_sum": 0.0, "temp_n": 0}
    bucket = _load_hourly[hour]
    bucket["samples"] += 1
    bucket["total"] += load


# Outdoor temperature from HA weather entity, updated by poll loop.
_outdoor_temp: float | None = None


def _update_outdoor_temp(temp: float | None) -> None:
    """Update the current outdoor temperature (from weather entity)."""
    global _outdoor_temp
    _outdoor_temp = temp


def _record_temp_in_load() -> None:
    """Record current outdoor temp in the load accumulator for this hour."""
    from datetime import datetime
    hour = datetime.now().hour
    if hour in _load_hourly and _outdoor_temp is not None:
        _load_hourly[hour]["temp_sum"] += _outdoor_temp
        _load_hourly[hour]["temp_n"] += 1


def get_completed_hourly_usage() -> list[dict]:
    """Return completed hours' consumption + temperature for telemetry.
    Only returns hours before the current hour (completed data)."""
    from datetime import datetime, timezone
    now = datetime.now()
    result = []
    for hour, bucket in _load_hourly.items():
        if hour >= now.hour:
            continue  # skip current/future hours
        n = bucket["samples"]
        if n == 0:
            continue
        avg_load = bucket["total"] / n
        # Build UTC timestamp for this hour today
        local_dt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        utc_dt = local_dt.astimezone(timezone.utc)
        entry: dict = {
            "timestampUtc": utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "consumptionW": round(avg_load, 1),
        }
        temp_n = bucket.get("temp_n", 0)
        if temp_n > 0:
            entry["temperatureC"] = round(bucket["temp_sum"] / temp_n, 1)
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Hourly energy trade accumulator — tracks import/export kWh + costs per hour.
# Published as HA sensors for financial tracking.
# ---------------------------------------------------------------------------
_trade_hourly: dict[int, dict[str, float]] = {}
_trade_hourly_date: str = ""
_trade_daily_totals: dict[str, float] = {}


def _accumulate_trade(readings: dict[str, dict]) -> None:
    """Record grid import/export and self-consumption into hourly trade buckets."""
    global _trade_hourly_date, _trade_daily_totals
    from datetime import datetime
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if today != _trade_hourly_date:
        _trade_hourly.clear()
        _trade_daily_totals = {
            "import_kwh": 0, "export_kwh": 0, "self_kwh": 0,
            "import_cost": 0, "export_rev": 0, "self_value": 0,
        }
        _trade_hourly_date = today
    hour = now.hour

    # Grid power: + = export, − = import (in Watts)
    grid_w = readings.get("ac_active_power_w", {}).get("value", 0) or 0
    grid_w = float(grid_w)
    pv_w = readings.get("pv_total_power_w", {}).get("value", 0) or 0
    pv_w = float(pv_w)
    load_w = readings.get("load_power_w", {}).get("value", 0) or 0
    load_w = float(load_w)

    # Self-consumption = PV directly used by home (not exported, not to battery)
    # Simplified: min(PV, load) — what PV covers of home consumption
    self_w = min(pv_w, load_w) if pv_w > 0 else 0

    if hour not in _trade_hourly:
        _trade_hourly[hour] = {
            "samples": 0,
            "import_w": 0, "export_w": 0, "self_w": 0,
        }
    bucket = _trade_hourly[hour]
    bucket["samples"] += 1
    if grid_w < 0:
        bucket["import_w"] += abs(grid_w)
    else:
        bucket["export_w"] += grid_w
    bucket["self_w"] += self_w


def _get_trade_sensors() -> dict[str, dict]:
    """Calculate trade sensors from accumulated data + current prices."""
    result: dict[str, dict] = {}

    # Get current price from prices data
    from datetime import datetime
    now = datetime.now()
    current_price = None
    today_prices = _latest_prices.get("prices_today", {}).get("value", [])
    if isinstance(today_prices, list):
        for h in today_prices:
            if isinstance(h, dict) and h.get("hour") == now.hour:
                current_price = h.get("price")
                break

    avg_price = _latest_prices.get("today_avg", {}).get("value")
    if avg_price is None:
        avg_price = current_price or 0.15  # fallback

    # Calculate per-hour kWh and costs
    total_import_kwh = 0.0
    total_export_kwh = 0.0
    total_self_kwh = 0.0
    total_import_cost = 0.0
    total_export_rev = 0.0
    total_self_value = 0.0

    for hour, bucket in _trade_hourly.items():
        n = bucket["samples"]
        if n == 0:
            continue
        # Average power over samples, convert to kWh (1 hour)
        import_kwh = (bucket["import_w"] / n) / 1000.0
        export_kwh = (bucket["export_w"] / n) / 1000.0
        self_kwh = (bucket["self_w"] / n) / 1000.0

        # Find price for this hour
        hour_price = avg_price
        if isinstance(today_prices, list):
            for h in today_prices:
                if isinstance(h, dict) and h.get("hour") == hour:
                    hour_price = h.get("price", avg_price)
                    break

        total_import_kwh += import_kwh
        total_export_kwh += export_kwh
        total_self_kwh += self_kwh
        total_import_cost += import_kwh * hour_price
        total_export_rev += export_kwh * hour_price
        total_self_value += self_kwh * hour_price

    trade_profit = total_export_rev - total_import_cost
    net_result = trade_profit + total_self_value

    _trade_daily_totals.update({
        "import_kwh": round(total_import_kwh, 2),
        "export_kwh": round(total_export_kwh, 2),
        "self_kwh": round(total_self_kwh, 2),
        "import_cost": round(total_import_cost, 2),
        "export_rev": round(total_export_rev, 2),
        "self_value": round(total_self_value, 2),
    })

    return {
        "grid_import_kwh":      {"value": round(total_import_kwh, 2),  "unit": "kWh"},
        "grid_export_kwh":      {"value": round(total_export_kwh, 2),  "unit": "kWh"},
        "self_consumption_kwh": {"value": round(total_self_kwh, 2),    "unit": "kWh"},
        "grid_import_cost":     {"value": round(total_import_cost, 2), "unit": "EUR"},
        "grid_export_revenue":  {"value": round(total_export_rev, 2),  "unit": "EUR"},
        "self_consumption_value":{"value": round(total_self_value, 2), "unit": "EUR"},
        "trade_profit":         {"value": round(trade_profit, 2),      "unit": "EUR"},
        "net_result":           {"value": round(net_result, 2),        "unit": "EUR"},
        "avg_price":            {"value": round(avg_price, 4),         "unit": "EUR/kWh"},
    }


def set_prices(snapshot: dict[str, dict]) -> None:
    """Called by PricesPoller.tick() to share latest prices with /status."""
    _latest_prices.clear()
    _latest_prices.update(snapshot)


def _get_current_soc_kwh() -> float:
    """Read current battery SoC from latest readings, convert to kWh."""
    bat_soc = _latest.get("battery_soc_percent", {}).get("value")
    if bat_soc is not None:
        return float(bat_soc) / 100.0 * 30.0  # 30 kWh capacity
    return 15.0  # default 50%


def set_plan(plan: dict[str, Any]) -> None:
    """Called by PlanPoller.tick() to share latest EMS plan with /status.
    Runs the arbitrage optimizer in auto mode for dashboard stats, but
    PRESERVES the server plan actions for the executor (server is authoritative).
    """
    global _executor_status
    # Run local arbitrage optimizer when in auto mode — for dashboard stats only.
    mode = _manual_override.get("mode", "auto")
    if mode == "auto" and _arbitrage_optimizer is not None:
        try:
            result = _arbitrage_optimizer.optimize(
                timeline=plan.get("timeline", []),
                current_soc_kwh=_get_current_soc_kwh(),
            )
            if result:
                # Store local optimizer results separately — do NOT overwrite server actions.
                plan["arbitrage"] = {
                    "profitEur": result.projected_profit_eur,
                    "chargeCostEur": result.charge_cost_eur,
                    "dischargeRevenueEur": result.discharge_revenue_eur,
                    "pvSavingsEur": result.pv_savings_eur,
                    "cycles": result.cycles,
                    "summary": result.summary,
                }
        except Exception as ex:
            _LOG.error("Arbitrage optimizer failed: %s", ex, exc_info=True)

    _latest_plan.clear()
    _latest_plan.update(plan)
    if _executor is not None:
        import asyncio
        asyncio.ensure_future(_run_executor(plan))


_executor_lock = asyncio.Lock()

async def _run_executor(plan: dict[str, Any]) -> None:
    """Run the action executor and update the shared status string.
    Manual override takes priority over the plan.
    """
    global _executor_status
    if _ha_controller is None:
        return
    if _executor_lock.locked():
        return  # skip if another executor call is in progress
    async with _executor_lock:
        try:
            mode = _manual_override.get("mode", "auto")
            pct = _manual_override.get("power_pct", 100)
            max_w = 15000  # Sofar HYD 15KTL rated max — BMS will limit actual rate
            power_w = int(max_w * pct / 100)

            if mode == "charge":
                result = await _ha_controller.set_charge(power_w)
                if result:
                    _executor_status = f"⚡ Handmatig: {result}"
                return
            elif mode == "charge_solar":
                result = await _ha_controller.set_solar_charge()
                if result:
                    _executor_status = f"☀ Handmatig: {result}"
                return
            elif mode == "discharge":
                # Battery covers home load — Passive Mode with grid_power = 0
                # (battery + PV cover home, no grid import, PV surplus → grid)
                result = await _ha_controller.set_discharge_selfuse()
                if result:
                    _executor_status = "🔋 Ontladen (eigen verbruik)"
                return
            elif mode == "grid_charge":
                # Grid charge: max import + PV curtailed (negative price mode)
                result = await _ha_controller.set_grid_charge(power_w)
                if result:
                    _executor_status = f"🔌 Grid laden + PV uit: {result}"
                return
            elif mode == "export":
                # Force-discharge to grid at selected power
                result = await _ha_controller.set_discharge(power_w)
                if result:
                    _executor_status = f"⚡ Handmatig: {result}"
                return
            elif mode == "baseline" or mode == "standby":
                # Baseline: no charge, battery covers deficit, grid=0
                result = await _ha_controller.set_discharge_selfuse()
                if result:
                    _executor_status = "⚖ Baseline (grid=0, batterij springt bij)"
                return
            elif mode == "auto_sofar":
                # Return to Sofar Self Use — inverter decides everything
                if isinstance(_ha_controller, ModbusBatteryController):
                    try:
                        await _ha_controller._modbus.write_holding(by_name("energy_storage_mode"), 0)
                    except Exception as ex:
                        _LOG.warning("Modbus write energy_storage_mode failed: %s", ex)
                else:
                    await _ha_controller._ha.call_service("select", "select_option", {
                        "entity_id": "select.sofar_inverter_energy_storage_mode",
                        "option": "Self Use",
                    })
                _ha_controller._last_mode = "sofar_auto"
                _executor_status = "🔄 Sofar Auto (Self Use)"
                return

            # mode == "auto" → follow the Saldox plan
            if _executor is not None:
                soc_pct = _latest.get("battery_soc_percent", {}).get("value")
                soc_pct = float(soc_pct) if soc_pct is not None else None
                result = await _executor.execute(plan, current_soc_percent=soc_pct)
                if result:
                    _executor_status = result
        except Exception as ex:  # noqa: BLE001
            _LOG.error("Action executor failed: %s", ex, exc_info=True)
            _executor_status = f"Fout: {ex}"


async def poll_loop(
    client: SofarModbusClient,
    ha: HomeAssistantClient,
    ha_reader: HaSensorReader,
    slug: str,
    friendly: str,
    interval: int,
) -> None:
    global _latest_ts
    _modbus_ok = True  # track Modbus availability
    while True:
        try:
            # Always try direct Modbus first; retry on every cycle.
            readings = None
            source = "modbus"
            try:
                readings = await client.read_all()
                if not _modbus_ok:
                    _LOG.info("Modbus hersteld — direct Modbus actief")
                _modbus_ok = True
            except Exception as ex:
                _modbus_ok = False
                _LOG.warning("Modbus read mislukt: %s — probeer HA sensors", ex)

            if readings is None:
                readings = await ha_reader.read_all()
                source = "ha-sensors"
                if not readings:
                    _LOG.warning("Geen readings van HA sensors")
                    await asyncio.sleep(interval)
                    continue

            snapshot: dict[str, dict] = {}
            for r in readings:
                snapshot[r.name] = {"value": r.value, "unit": r.unit}
            _latest.clear()
            _latest.update(snapshot)
            _latest_ts = time.time()

            # Accumulate hourly PV, consumption, and trade averages for charts.
            _accumulate_pv(snapshot)
            _accumulate_load(snapshot)
            _accumulate_trade(snapshot)

            # Read outdoor temperature from HA weather entity.
            try:
                weather = await ha.get_state("weather.forecast_thuis")
                if weather:
                    attrs = weather.get("attributes", {})
                    temp = attrs.get("temperature")
                    if temp is not None:
                        _update_outdoor_temp(float(temp))
                        _record_temp_in_load()
            except Exception:
                pass  # non-critical

            # Always push to HA as separate sensors (Solax integration removed).
            if readings:
                for r in readings:
                    if r.name not in SENSOR_MAP:
                        continue
                    suffix, dev_class, state_class = SENSOR_MAP[r.name]
                    entity = f"sensor.{slug}_{suffix}"
                    await ha.post_state(
                        entity_id=entity,
                        state=r.value,
                        unit=r.unit or None,
                        friendly_name=f"{friendly} {suffix.replace('_', ' ')}",
                        device_class=dev_class,
                        state_class=state_class,
                        extra_attrs={"source": "saldox-ems-bridge", "modbus_register": r.name},
                    )

            _LOG.info("Poll OK — %d readings via %s", len(readings), source)

            # Publish trade/financial sensors to HA (every poll cycle).
            try:
                trade = _get_trade_sensors()
                for key, val in trade.items():
                    entity = f"sensor.saldox_{key}"
                    dev_class = "monetary" if val["unit"] == "EUR" else "energy" if val["unit"] == "kWh" else None
                    await ha.post_state(
                        entity_id=entity,
                        state=val["value"],
                        unit=val["unit"],
                        friendly_name=f"Saldox {key.replace('_', ' ')}",
                        device_class=dev_class,
                        state_class="total_increasing" if "kwh" in key else "measurement",
                        extra_attrs={"source": "saldox-ems-bridge", "updated": time.time()},
                    )
            except Exception:
                pass  # non-critical

            # Execute plan actions on every poll cycle for timely transitions.
            if _latest_plan:
                await _run_executor(_latest_plan)
        except Exception as ex:  # noqa: BLE001
            _LOG.error("Poll-iteratie faalde: %s", ex)
        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# Saldox command webhook
# ---------------------------------------------------------------------------
def make_webhook_app(client: SofarModbusClient, ha: HomeAssistantClient) -> web.Application:
    """Endpoints:
      POST /commands/active-power-limit    body: { "percent": 0..100 }
      POST /commands/battery-mode          body: { "mode": "auto|force-charge|force-discharge|standby" }
      POST /commands/battery-charge-power  body: { "watts": int }
      POST /commands/battery-discharge-power body: { "watts": int }
      GET  /healthz
    """
    BATTERY_MODE_MAP = {"auto": 0, "force-charge": 1, "force-discharge": 2, "standby": 3}

    async def health(_req: web.Request) -> web.Response:
        return web.json_response({"ok": True, "addon": "saldox-ems-bridge"})

    async def status(_req: web.Request) -> web.Response:
        # Build hourly PV averages for the solar chart.
        pv_hourly = {}
        for h, b in _pv_hourly.items():
            n = b["samples"]
            if n > 0:
                pv_hourly[str(h)] = {
                    "total": round(b["total"] / n, 1),
                    "pv1": round(b["pv1"] / n, 1),
                    "pv2": round(b["pv2"] / n, 1),
                }
        # Build hourly load averages for the consumption chart.
        load_hourly = {}
        for h, b in _load_hourly.items():
            n = b["samples"]
            if n > 0:
                load_hourly[str(h)] = {"total": round(b["total"] / n, 1)}
        return web.json_response({
            "ok": True,
            "timestamp": _latest_ts,
            "readings": _latest,
            "prices": _latest_prices,
            "plan": _latest_plan,
            "executor": _executor_status,
            "executionLog": _executor.log.entries[-20:] if _executor else [],
            "override": _manual_override,
            "pvHourly": pv_hourly,
            "loadHourly": load_hourly,
            "arbitrage": _latest_plan.get("arbitrage", {}),
            "trade": _trade_daily_totals,
        })

    async def set_override(req: web.Request) -> web.Response:
        """POST /commands/override  body: { "mode": "auto|charge|discharge|standby", "power_pct": 0..100 }"""
        body = await req.json()
        mode = str(body.get("mode", "auto"))
        if mode not in ("auto", "auto_sofar", "baseline", "charge", "charge_solar", "grid_charge", "discharge", "export", "standby"):
            return web.json_response({"ok": False, "error": "mode must be auto|auto_sofar|charge|charge_solar|discharge|export|standby"}, status=400)
        pct = int(body.get("power_pct", 100))
        if not 0 <= pct <= 100:
            return web.json_response({"ok": False, "error": "power_pct must be 0..100"}, status=400)
        _manual_override["mode"] = mode
        _manual_override["power_pct"] = pct
        _LOG.info("Manual override: mode=%s power=%d%%", mode, pct)
        # Immediately execute the override
        if _latest_plan:
            await _run_executor(_latest_plan)
        else:
            await _run_executor({})
        # Force immediate plan refresh so the plan aligns with the new reality
        if _plan_poller is not None:
            asyncio.ensure_future(_plan_poller.tick())
            _LOG.info("Forced plan refresh after override change")
        return web.json_response({"ok": True, "override": _manual_override, "executor": _executor_status})

    async def set_power_limit(req: web.Request) -> web.Response:
        body = await req.json()
        pct = int(body.get("percent", -1))
        if not 0 <= pct <= 100:
            return web.json_response({"ok": False, "error": "percent moet 0..100 zijn"}, status=400)
        try:
            await client.write_holding(by_name("active_power_limit_pct"), pct)
            return web.json_response({"ok": True, "percent": pct})
        except Exception as ex:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(ex)}, status=500)

    async def set_battery_mode(req: web.Request) -> web.Response:
        """Set battery mode via ModbusBatteryController."""
        body = await req.json()
        mode = str(body.get("mode", ""))
        controller = _ha_controller
        try:
            if mode == "auto":
                result = await controller.set_auto()
            elif mode == "standby":
                result = await controller.set_standby()
            elif mode == "force-charge":
                watts = int(body.get("watts", 0)) or None
                result = await controller.set_charge(watts)
            elif mode == "force-discharge":
                watts = int(body.get("watts", 0)) or None
                result = await controller.set_discharge(watts)
            elif mode == "solar-charge":
                result = await controller.set_solar_charge()
            else:
                return web.json_response({"ok": False, "error": f"mode must be one of: auto, standby, force-charge, force-discharge, solar-charge"}, status=400)
            return web.json_response({"ok": True, "mode": mode, "result": result})
        except Exception as ex:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(ex)}, status=500)

    async def set_battery_charge_power(req: web.Request) -> web.Response:
        body = await req.json()
        watts = int(body.get("watts", -1))
        if watts < 0:
            return web.json_response({"ok": False, "error": "watts moet >= 0 zijn"}, status=400)
        try:
            result = await _ha_controller.set_charge(watts)
            return web.json_response({"ok": True, "watts": watts, "result": result})
        except Exception as ex:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(ex)}, status=500)

    async def set_battery_discharge_power(req: web.Request) -> web.Response:
        body = await req.json()
        watts = int(body.get("watts", -1))
        if watts < 0:
            return web.json_response({"ok": False, "error": "watts moet >= 0 zijn"}, status=400)
        try:
            result = await _ha_controller.set_discharge(watts)
            return web.json_response({"ok": True, "watts": watts, "result": result})
        except Exception as ex:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(ex)}, status=500)

    @web.middleware
    async def cors_middleware(request: web.Request, handler):
        if request.method == "OPTIONS":
            resp = web.Response(status=204)
        else:
            resp = await handler(request)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    async def ingress_page(_req: web.Request) -> web.Response:
        html = """<!DOCTYPE html>
<html lang="nl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Saldox EMS Bridge</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#f4f5f7;color:#333;padding:24px}
h1{font-size:1.5rem;margin-bottom:4px;color:#1a7a2e}
.subtitle{color:#666;margin-bottom:24px;font-size:.9rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.card .label{font-size:.8rem;color:#888;text-transform:uppercase;letter-spacing:.5px}
.card .value{font-size:1.8rem;font-weight:700;margin:8px 0 4px}
.card .unit{font-size:.85rem;color:#666}
.card.ok .value{color:#1a7a2e}
.card.warn .value{color:#d97706}
.card.off .value{color:#999}
.card.savings .value{color:#1a7a2e}
.status-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.status-dot.green{background:#22c55e}
.status-dot.red{background:#ef4444}
.status-dot.gray{background:#9ca3af}
#error{color:#ef4444;margin-bottom:16px;display:none}
.section-title{font-size:1.1rem;font-weight:600;color:#555;margin:28px 0 12px;padding-top:16px;border-top:1px solid #e5e7eb}
.action-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600;color:#fff;margin-right:4px}
.action-ChargeBattery{background:#22c55e}
.action-DischargeBattery{background:#f97316}
.action-ExportToGrid{background:#dc2626}
.action-SolarCharge{background:#eab308}
.action-ChargeCar{background:#3b82f6}
.action-CurtailPv{background:#a855f7}
.action-RunHeavyLoad{background:#6b7280}
.plan-chart{position:relative;height:280px;margin-top:12px}
.plan-chart canvas{width:100%;height:100%}

/* Power flow diagram */
.pf-wrap{max-width:480px;margin:0 auto 24px}
.pf-svg{width:100%;height:auto}
.pf-node{font-size:11px;font-weight:700;text-anchor:middle}
.pf-val{font-size:13px;font-weight:700;text-anchor:middle;fill:#333}
.pf-sub{font-size:9px;fill:#888;text-anchor:middle}
.pf-icon{font-size:28px;text-anchor:middle;dominant-baseline:central}
@keyframes flowDash{to{stroke-dashoffset:-20}}
@keyframes flowDashRev{to{stroke-dashoffset:20}}
.pf-line{stroke-width:3;fill:none;stroke-linecap:round;stroke-dasharray:8 6}
.pf-line.active{animation:flowDash .8s linear infinite}
.pf-line.reverse{animation:flowDashRev .8s linear infinite}
.pf-line.idle{stroke:#e5e7eb;stroke-dasharray:none;stroke-width:2;animation:none}
.ctrl-btn{flex:1;padding:8px 4px;border:2px solid #e5e7eb;border-radius:8px;background:#fff;font-size:.8rem;font-weight:600;color:#666;cursor:pointer;transition:all .2s}
.ctrl-btn:hover{border-color:#1a7a2e;color:#1a7a2e}
.ctrl-btn.active{border-color:#1a7a2e;background:#1a7a2e;color:#fff}
.ctrl-btn[data-mode=charge].active{background:#22c55e;border-color:#22c55e}
.ctrl-btn[data-mode=discharge].active{background:#f97316;border-color:#f97316}
.ctrl-btn[data-mode=standby].active{background:#6b7280;border-color:#6b7280}
</style>
</head><body>
<h1>Saldox EMS Bridge</h1>
<p class="subtitle"><span class="status-dot" id="dot"></span><span id="conn">Verbinden...</span></p>
<div id="error"></div>
<div class="section-title" style="margin-top:8px">Arbitrage Simulator</div>
<div class="card" style="margin-bottom:16px">
  <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
    <label style="font-size:.85rem">Dagen: <input id="sim-days" type="number" value="1" min="1" max="365" style="width:60px;padding:4px;border:1px solid #ccc;border-radius:4px"></label>
    <label style="font-size:.85rem"><input id="sim-sweep" type="checkbox"> Parameter sweep</label>
    <button id="sim-btn" onclick="runSim()" class="ctrl-btn" style="flex:none;padding:8px 16px;max-width:200px">Simulatie starten</button>
  </div>
  <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
    <label style="font-size:.85rem">Apparaten: <input id="sim-loads" type="text" value="wasmachine,vaatwasser" placeholder="wasmachine,vaatwasser,droger" style="width:280px;padding:4px;border:1px solid #ccc;border-radius:4px;font-size:.8rem"></label>
    <span style="font-size:.7rem;color:#888">Keuze: wasmachine, vaatwasser, droger, oven, ev_laden, warmtepomp, airco, boiler — of naam:watts:uren</span>
  </div>
  <pre id="sim-out" style="font-size:.75rem;line-height:1.4;overflow-x:auto;max-height:500px;white-space:pre;background:#f8f9fa;padding:12px;border-radius:8px;color:#333"></pre>
</div>
<div class="pf-wrap" id="powerflow"></div>
<div class="card" id="control-panel" style="max-width:480px;margin:0 auto 24px;padding:16px">
  <div class="label" style="margin-bottom:12px">BATTERIJ BESTURING</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px" id="mode-btns">
    <button class="ctrl-btn active" data-mode="auto">Auto (Saldox)</button>
    <button class="ctrl-btn" data-mode="auto_sofar">Auto (Sofar)</button>
    <button class="ctrl-btn" data-mode="charge">Laden (grid)</button>
    <button class="ctrl-btn" data-mode="charge_solar">Laden (zon)</button>
    <button class="ctrl-btn" data-mode="discharge">Ontladen (eigen)</button>
    <button class="ctrl-btn" data-mode="export">Ontladen (grid)</button>
    <button class="ctrl-btn" data-mode="standby">Stand-by</button>
  </div>
  <div id="power-slider-wrap" style="display:none">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
      <span style="font-size:.8rem;color:#666">Vermogen</span>
      <span id="power-label" style="font-size:1rem;font-weight:700">100% (15.0 kW)</span>
    </div>
    <input type="range" id="power-slider" min="10" max="100" value="100" step="10"
      style="width:100%;accent-color:#1a7a2e">
  </div>
  <div id="ctrl-status" style="font-size:.8rem;color:#888;margin-top:8px"></div>
</div>
<div class="grid" id="grid"></div>
<div id="plan-section"></div>
<p style="color:#aaa;font-size:.75rem;margin-top:16px">Auto-refresh elke 10 seconden</p>
<script>
const grid=document.getElementById('grid'),dot=document.getElementById('dot'),
      conn=document.getElementById('conn'),errEl=document.getElementById('error'),
      planSection=document.getElementById('plan-section'),
      pfEl=document.getElementById('powerflow');

// --- Battery control panel ---
const modeBtns=document.querySelectorAll('.ctrl-btn');
const powerSlider=document.getElementById('power-slider');
const powerLabel=document.getElementById('power-label');
const powerWrap=document.getElementById('power-slider-wrap');
const ctrlStatus=document.getElementById('ctrl-status');
let currentMode='auto';

function updatePowerLabel(){
  const pct=powerSlider.value;
  const kw=(15.0*pct/100).toFixed(1);
  powerLabel.textContent=pct+'% ('+kw+' kW)';
}
powerSlider.addEventListener('input',updatePowerLabel);
powerSlider.addEventListener('change',()=>sendOverride(currentMode,parseInt(powerSlider.value)));

async function sendOverride(mode,pct){
  ctrlStatus.textContent='Versturen...';
  try{
    const r=await fetch('./commands/override',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:mode,power_pct:pct||100})});
    const d=await r.json();
    if(d.ok){ctrlStatus.textContent=d.executor||'OK';}
    else{ctrlStatus.textContent='Fout: '+(d.error||'onbekend');}
  }catch(e){ctrlStatus.textContent='Fout: '+e.message;}
}

modeBtns.forEach(btn=>{
  btn.addEventListener('click',()=>{
    const mode=btn.dataset.mode;
    currentMode=mode;
    modeBtns.forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    powerWrap.style.display=(mode==='charge'||mode==='export')?'block':'none';
    sendOverride(mode,mode==='charge'||mode==='export'?parseInt(powerSlider.value):100);
  });
});

function syncControlPanel(override){
  if(!override)return;
  const mode=override.mode||'auto';
  const pct=override.power_pct||100;
  currentMode=mode;
  modeBtns.forEach(b=>{b.classList.toggle('active',b.dataset.mode===mode);});
  powerWrap.style.display=(mode==='charge'||mode==='export')?'block':'none';
  powerSlider.value=pct;
  updatePowerLabel();
}


function renderPowerFlow(readings, executorStatus, prices, plan){
  // Extract values (default 0 if missing)
  const val=(k)=>{const r=readings[k];return r?Number(r.value)||0:0;};
  const pvW=val('pv_total_power_w');
  const gridW=val('ac_active_power_w');   // + export, − import
  const batW=val('battery_power_w');      // + charge, − discharge
  const batSoC=val('battery_soc_percent');
  const batV=val('battery_voltage_v');
  const batTemp=val('battery_temperature_c');
  // Derive home consumption: PV + grid_import + bat_discharge - grid_export - bat_charge
  const homeW=Math.max(0, pvW - gridW - batW);

  // Flow magnitudes for lines
  const pvToHome=Math.max(0, pvW - Math.max(0,gridW) - Math.max(0,batW));
  const pvToGrid=Math.max(0, gridW);
  const pvToBat=Math.max(0, batW);
  const gridToHome=Math.max(0, -gridW);
  const batToHome=Math.max(0, -batW);

  const lc=(w,rev)=>w>10?(rev?'pf-line active reverse':'pf-line active'):'pf-line idle';
  const ls=(w,col)=>w>10?col:'#e5e7eb';
  const fw=(w)=>{const a=Math.abs(w);return a>=1000?(a/1000).toFixed(1)+' kW':Math.round(a)+' W';};

  // Battery stats calculations
  const batCapKwh=plan&&plan.batterySoC&&plan.batterySoC.length?plan.batterySoC[0].capacityKwh:30;
  const batKwh=batCapKwh*(batSoC/100);
  const batRemKwh=batCapKwh-batKwh;
  const chargeRateKw=Math.abs(batW)/1000;
  let timeEst='';
  if(batW>100){
    const hrsToFull=batRemKwh/chargeRateKw;
    timeEst=hrsToFull<1?Math.round(hrsToFull*60)+'m vol':hrsToFull.toFixed(1)+'u vol';
  }else if(batW<-100){
    const hrsToEmpty=batKwh/chargeRateKw;
    timeEst=hrsToEmpty<1?Math.round(hrsToEmpty*60)+'m leeg':hrsToEmpty.toFixed(1)+'u leeg';
  }

  // Price comparison for battery insight
  const pNow=prices.now&&prices.now.value;
  const pAvg=prices.today_avg&&prices.today_avg.value;
  const pMax=prices.today_max&&prices.today_max.value;
  let priceInsight='';
  if(typeof pNow==='number'&&typeof pAvg==='number'){
    if(pNow<pAvg*0.7)priceInsight='Goedkoop — ideaal om te laden!';
    else if(pNow>pAvg*1.3)priceInsight='Duur — beter ontladen';
    else priceInsight='Gemiddelde prijs';
  }
  // Potential savings: charge now at pNow, sell/avoid at pMax
  let potentialSavings='';
  if(typeof pNow==='number'&&typeof pMax==='number'&&batRemKwh>0.5){
    const saving=(pMax-pNow)*batRemKwh;
    if(saving>0.01)potentialSavings=`Laden nu bespaart € ${saving.toFixed(2)} vs. piekprijs`;
  }

  // Executor status badge
  const exBadge=executorStatus?`<div style="text-align:center;margin:8px 0">
    <span style="display:inline-block;padding:4px 12px;border-radius:12px;font-size:.8rem;font-weight:600;background:${executorStatus.includes('Laden')?'#22c55e':executorStatus.includes('Ontladen')?'#f97316':executorStatus.includes('beperkt')?'#a855f7':'#e5e7eb'};color:${executorStatus.includes('Wachten')||executorStatus.includes('Auto')?'#666':'#fff'}">${executorStatus}</span>
  </div>`:'';

  // Battery stats panel
  const batStats=`<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-top:8px">
    <div class="card" style="padding:12px"><div class="label">Capaciteit</div><div style="font-size:1.1rem;font-weight:700;color:#f59e0b">${batKwh.toFixed(1)} / ${batCapKwh.toFixed(1)} kWh</div></div>
    <div class="card" style="padding:12px"><div class="label">Laadsnelheid</div><div style="font-size:1.1rem;font-weight:700">${chargeRateKw.toFixed(1)} kW</div>${timeEst?`<div class="unit">${timeEst}</div>`:''}</div>
    ${batV?`<div class="card" style="padding:12px"><div class="label">Spanning / Temp</div><div style="font-size:1.1rem;font-weight:700">${batV} V</div>${batTemp?`<div class="unit">${batTemp} °C</div>`:''}</div>`:''}
    ${priceInsight?`<div class="card" style="padding:12px"><div class="label">Prijsinzicht</div><div style="font-size:.9rem;font-weight:600;color:${priceInsight.includes('Goedkoop')?'#22c55e':priceInsight.includes('Duur')?'#ef4444':'#888'}">${priceInsight}</div>${potentialSavings?`<div class="unit">${potentialSavings}</div>`:''}</div>`:''}
  </div>`;

  pfEl.innerHTML=`${exBadge}<svg class="pf-svg" viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">
    <line x1="160" y1="62" x2="160" y2="218" class="${lc(pvToHome,false)}" stroke="${ls(pvToHome,'#22c55e')}"/>
    <line x1="132" y1="55" x2="68" y2="118" class="${lc(pvToGrid,false)}" stroke="${ls(pvToGrid,'#22c55e')}"/>
    <line x1="188" y1="55" x2="252" y2="118" class="${lc(pvToBat,false)}" stroke="${ls(pvToBat,'#f59e0b')}"/>
    <line x1="68" y1="165" x2="132" y2="225" class="${lc(gridToHome,false)}" stroke="${ls(gridToHome,'#3b82f6')}"/>
    <line x1="252" y1="165" x2="188" y2="225" class="${lc(batToHome,false)}" stroke="${ls(batToHome,'#f59e0b')}"/>
    ${pvToHome>10?`<text x="175" y="145" class="pf-sub">${fw(pvToHome)}</text>`:''}
    ${pvToGrid>10?`<text x="85" y="78" class="pf-sub">${fw(pvToGrid)}</text>`:''}
    ${pvToBat>10?`<text x="232" y="78" class="pf-sub">${fw(pvToBat)}</text>`:''}
    ${gridToHome>10?`<text x="85" y="205" class="pf-sub">${fw(gridToHome)}</text>`:''}
    ${batToHome>10?`<text x="232" y="205" class="pf-sub">${fw(batToHome)}</text>`:''}
    <text x="160" y="24" class="pf-icon">\u2600\ufe0f</text>
    <text x="160" y="50" class="pf-val" fill="#22c55e">${fw(pvW)}</text>
    <text x="160" y="62" class="pf-sub">Zonnepanelen</text>
    <text x="40" y="132" class="pf-icon">\u26a1</text>
    <text x="40" y="158" class="pf-val" fill="${gridW>=0?'#22c55e':'#3b82f6'}">${fw(Math.abs(gridW))}</text>
    <text x="40" y="170" class="pf-sub">${gridW>=0?'Export':'Import'}</text>
    <text x="280" y="132" class="pf-icon">&#x1F50B;</text>
    <text x="280" y="158" class="pf-val" fill="#f59e0b">${batSoC}%</text>
    <text x="280" y="170" class="pf-sub">${batW>10?'Laden '+fw(batW):batW<-10?'Ontladen '+fw(-batW):'Stand-by'}</text>
    <text x="160" y="238" class="pf-icon">&#x1F3E0;</text>
    <text x="160" y="262" class="pf-val" fill="#f97316">${fw(homeW)}</text>
    <text x="160" y="274" class="pf-sub">Verbruik</text>
  </svg>${batStats}`;
}

const labels={power:'PV vermogen',grid_power:'Net vermogen',battery_soc:'Batterij SoC',
  battery_power:'Batterij vermogen',today_kwh:'Vandaag opgewekt',total_kwh:'Totaal opgewekt',
  today_import_kwh:'Import vandaag',today_export_kwh:'Export vandaag',
  temperature:'Temperatuur',status:'Inverter status',battery_voltage:'Batterij spanning'};
const actionLabels={ChargeBattery:'Batterij laden',DischargeBattery:'Eigen verbruik',
  ExportToGrid:'Export naar grid',SolarCharge:'Zonne-laden',ChargeCar:'Auto laden',CurtailPv:'PV beperken',RunHeavyLoad:'Zwaar verbruik'};
const actionColors={ChargeBattery:'#22c55e',DischargeBattery:'#f97316',ExportToGrid:'#dc2626',
  SolarCharge:'#eab308',ChargeCar:'#3b82f6',CurtailPv:'#a855f7',RunHeavyLoad:'#6b7280'};

function toLocal(utcStr){
  if(!utcStr)return null;
  return new Date(utcStr.endsWith('Z')?utcStr:utcStr+'Z');
}
function fmtHour(d){return d?d.getHours()+':00':'?';}
function fmtTime(d){return d?d.toLocaleTimeString('nl-NL',{hour:'2-digit',minute:'2-digit'}):'?';}

function renderPlan(plan, pvHourly, loadHourly){
  if(!plan||!plan.timeline||!plan.timeline.length){planSection.innerHTML='';return;}
  const tl=plan.timeline;
  const actions=plan.actions||[];
  const batSoC=plan.batterySoC||[];
  const evSoC=plan.evSoC||[];
  const savings=plan.totalSavingsEur;
  const naive=plan.naiveCostEur;
  const optimized=plan.optimizedCostEur;
  const now=new Date();

  let h='<div class="section-title">48-uur Energieplan</div>';
  h+='<div class="grid">';
  if(savings!=null)h+=`<div class="card savings"><div class="label">Besparing</div><div class="value">€ ${savings.toFixed(2)}</div><div class="unit">komende 48 uur</div></div>`;
  if(optimized!=null&&naive!=null)h+=`<div class="card ok"><div class="label">Kosten</div><div class="value">€ ${optimized.toFixed(2)}</div><div class="unit">i.p.v. € ${naive.toFixed(2)} zonder plan</div></div>`;
  const arb=plan.arbitrage;
  if(arb&&arb.profitEur>0)h+=`<div class="card savings"><div class="label">Arbitrage winst</div><div class="value">\u20ac ${arb.profitEur.toFixed(2)}</div><div class="unit">${arb.cycles} cyclus(sen) \u00b7 ${arb.summary||''}</div></div>`;

  // Replan indicator — shows when the feedback loop triggered a replan
  if(plan.lastReplan){
    const rp=plan.lastReplan;
    const rpTime=toLocal(rp.timestampUtc);
    const rpLabels={SoCDrift:'SoC-drift',PvDrift:'PV-drift',EvPluggedIn:'EV aangesloten',PriceUpdate:'Prijsupdate',LoadSpike:'Verbruikspiek',UserOverride:'Handmatig'};
    const rpLabel=rpLabels[rp.trigger]||rp.trigger;
    h+=`<div class="card warn"><div class="label">Herplanning</div><div class="value">${rpLabel}</div><div class="unit">${rpTime?fmtTime(rpTime):''} \u00b7 ${rp.reason||''}</div></div>`;
  }

  // Next action card
  const futureActions=actions.filter(a=>{const e=toLocal(a.endUtc);return e&&e>now;}).sort((a,b)=>toLocal(a.startUtc)-toLocal(b.startUtc));
  if(futureActions.length){
    const na=futureActions[0];
    const lbl=actionLabels[na.kind]||na.kind;
    const st=toLocal(na.startUtc);
    const active=st&&st<=now;
    h+=`<div class="card ${active?'warn':'ok'}"><div class="label">${active?'Actie nu':'Volgende actie'}</div><div class="value"><span class="action-badge action-${na.kind}">${lbl}</span></div><div class="unit">${fmtTime(st)} · ${na.kwh!=null?na.kwh.toFixed(1)+' kWh · ':''}\u20ac ${(na.eurSavings||0).toFixed(2)} besparing</div></div>`;
  }
  h+='</div>';

  // Solar forecast vs actual chart — today only, with string breakdown
  h+='<div class="card" style="margin-bottom:16px"><div class="label">&#x2600; Zonneproductie vandaag &#x2014; forecast vs. werkelijk per string</div>';
  h+='<div class="plan-chart" style="height:220px"><canvas id="solarCanvas"></canvas></div></div>';

  // Consumption chart — expected vs actual
  h+='<div class="card" style="margin-bottom:16px"><div class="label">&#x1F3E0; Verbruik &#x2014; verwacht vs. werkelijk</div>';
  h+='<div class="plan-chart" style="height:220px"><canvas id="consumptionCanvas"></canvas></div></div>';

  // Power balance chart — consumption vs PV vs battery contribution
  h+='<div class="card" style="margin-bottom:16px"><div class="label">&#x26A1; Energiebalans &#x2014; verbruik, zon &#x26; batterij</div>';
  h+='<div class="plan-chart" style="height:220px"><canvas id="balanceCanvas"></canvas></div></div>';

  // Trade chart — bought/sold energy with price impact
  h+='<div class="card" style="margin-bottom:16px"><div class="label">&#x1F4B0; Handel &#x2014; inkoop, verkoop &#x26; opbrengst</div>';
  h+='<div class="plan-chart" style="height:240px"><canvas id="tradeCanvas"></canvas></div></div>';

  // 48h timeline chart — price bars with action overlays + SoC lines
  h+='<div class="card" style="grid-column:1/-1;margin-bottom:16px"><div class="label">48-uur tijdlijn — prijs + acties + SoC</div>';
  h+='<div class="plan-chart"><canvas id="planCanvas"></canvas></div></div>';

  // Action list
  if(actions.length){
    h+='<div class="card" style="margin-bottom:16px"><div class="label">Geplande acties</div><div style="margin-top:12px">';
    for(const a of actions){
      const lbl=actionLabels[a.kind]||a.kind;
      const st=toLocal(a.startUtc);
      const en=toLocal(a.endUtc);
      const risk=a.risk||'';
      h+=`<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f0f0">`;
      h+=`<span class="action-badge action-${a.kind}">${lbl}</span>`;
      h+=`<span style="font-size:.85rem">${fmtTime(st)} – ${fmtTime(en)}</span>`;
      h+=`<span style="font-size:.8rem;color:#888">${a.kwh!=null?a.kwh.toFixed(1)+' kWh':''}${a.eurSavings!=null?' · € '+a.eurSavings.toFixed(2):''}${risk?' · '+risk:''}</span>`;
      if(a.rationale)h+=`<span style="font-size:.75rem;color:#aaa;margin-left:auto" title="${a.rationale}">ℹ</span>`;
      h+=`</div>`;
    }
    h+='</div></div>';
  }

  // Savings history chart
  const sh=plan.savingsHistory;
  if(sh&&sh.days&&sh.days.length>1){
    h+='<div class="section-title">Besparingen per dag</div>';
    h+='<div class="grid"><div class="card savings"><div class="label">Totaal berekend</div><div class="value">\u20ac '+sh.totalCalculated.toFixed(2)+'</div><div class="unit">'+sh.days.length+' dagen</div></div>';
    if(sh.totalRealized)h+='<div class="card ok"><div class="label">Totaal gerealiseerd</div><div class="value">\u20ac '+sh.totalRealized.toFixed(2)+'</div><div class="unit">werkelijk bespaard</div></div>';
    h+='</div>';
    h+='<div class="card" style="margin-bottom:16px"><div class="label">Dagelijkse besparing — berekend vs. gerealiseerd</div><div class="plan-chart"><canvas id="savingsCanvas"></canvas></div></div>';
  }

  planSection.innerHTML=h;

  // Draw the canvas charts
  requestAnimationFrame(()=>{
    drawSolarChart(tl, pvHourly||{});
    drawConsumptionChart(tl, loadHourly||{});
    drawBalanceChart(tl);
    drawTradeChart(tl,actions);
    drawPlanChart(tl,actions,batSoC,evSoC);
    if(sh&&sh.days&&sh.days.length>1)drawSavingsChart(sh.days);
  });
}

function drawSavingsChart(days){
  const canvas=document.getElementById('savingsCanvas');
  if(!canvas)return;
  const dpr=window.devicePixelRatio||1;
  const rect=canvas.parentElement.getBoundingClientRect();
  canvas.width=rect.width*dpr;
  canvas.height=rect.height*dpr;
  canvas.style.width=rect.width+'px';
  canvas.style.height=rect.height+'px';
  const ctx=canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  const W=rect.width,H=rect.height;
  const pad={top:24,right:20,bottom:40,left:50};
  const cW=W-pad.left-pad.right,cH=H-pad.top-pad.bottom;
  const N=days.length;
  if(N===0)return;
  const barW=Math.min(cW/N,40);
  const groupW=barW;

  // Find max value for scale
  const allVals=days.flatMap(d=>[d.calculatedSavings||0,d.realizedSavings||0]);
  const maxV=Math.max(...allVals,0.01);
  const minV=Math.min(...allVals,0);
  const range=maxV-minV||0.01;

  // Draw bars
  for(let i=0;i<N;i++){
    const d=days[i];
    const x=pad.left+i*groupW;

    // Calculated savings bar (light green)
    const calcH=((d.calculatedSavings-minV)/range)*cH*0.85;
    const calcY=pad.top+cH-calcH;
    ctx.fillStyle='rgba(34,197,94,0.4)';
    ctx.fillRect(x+2,calcY,groupW/2-3,calcH);

    // Realized savings bar (solid green, overlaid)
    if(d.realizedSavings!=null){
      const realH=((d.realizedSavings-minV)/range)*cH*0.85;
      const realY=pad.top+cH-realH;
      ctx.fillStyle='#22c55e';
      ctx.fillRect(x+groupW/2+1,realY,groupW/2-3,realH);
    }

    // Day label
    const label=d.date.substring(5); // MM-DD
    ctx.fillStyle='#999';ctx.font='8px system-ui';ctx.textAlign='center';
    ctx.fillText(label,x+groupW/2,pad.top+cH+14);

    // Value label on top of calculated bar
    if(d.calculatedSavings>0.01){
      ctx.fillStyle='#888';ctx.font='8px system-ui';ctx.textAlign='center';
      ctx.fillText('\u20ac'+d.calculatedSavings.toFixed(2),x+groupW/2,calcY-3);
    }
  }

  // Y-axis labels
  ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='right';
  const steps=[minV,(minV+maxV)/2,maxV];
  for(const v of steps){
    const y=pad.top+cH-((v-minV)/range)*cH*0.85;
    ctx.fillText('\u20ac'+v.toFixed(2),pad.left-4,y+3);
    ctx.strokeStyle='#f0f0f0';ctx.lineWidth=0.5;
    ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(pad.left+cW,y);ctx.stroke();
  }

  // Legend
  ctx.font='9px system-ui';ctx.textAlign='left';
  ctx.fillStyle='rgba(34,197,94,0.4)';ctx.fillRect(pad.left,pad.top-14,10,8);
  ctx.fillStyle='#888';ctx.fillText('Berekend',pad.left+14,pad.top-7);
  ctx.fillStyle='#22c55e';ctx.fillRect(pad.left+80,pad.top-14,10,8);
  ctx.fillStyle='#888';ctx.fillText('Gerealiseerd',pad.left+94,pad.top-7);
}

function drawSolarChart(timeline, pvHourly){
  const canvas=document.getElementById('solarCanvas');
  if(!canvas)return;
  const now=new Date();
  const todayStr=now.toISOString().slice(0,10);
  // Filter to today's slots
  const slots=timeline.filter(s=>{const d=toLocal(s.startUtc);return d&&d.toISOString().slice(0,10)===todayStr;});
  if(slots.length===0)return;

  const dpr=window.devicePixelRatio||1;
  const rect=canvas.parentElement.getBoundingClientRect();
  canvas.width=rect.width*dpr;
  canvas.height=rect.height*dpr;
  canvas.style.width=rect.width+'px';
  canvas.style.height=rect.height+'px';
  const ctx=canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  const W=rect.width,H=rect.height;
  const pad={top:24,right:16,bottom:30,left:50};
  const cW=W-pad.left-pad.right,cH=H-pad.top-pad.bottom;
  const N=slots.length;
  const groupW=cW/N;
  const barW=groupW*0.38; // each bar takes ~38% of group width, 2 bars + gap

  // Build per-hour data: forecast (from plan) + actual (from pvHourly accumulator)
  const hours=[];
  for(let i=0;i<N;i++){
    const st=toLocal(slots[i].startUtc);
    const h=st.getHours();
    const forecast=slots[i].pvForecastWatts!=null?slots[i].pvForecastWatts:slots[i].pvWatts;
    const actual=pvHourly[String(h)];
    hours.push({
      hour:h, forecast:forecast,
      actualTotal:actual?actual.total:0,
      pv1:actual?actual.pv1:0,
      pv2:actual?actual.pv2:0,
      hasActual:!!actual,
      shadowFactor:slots[i].shadowFactor
    });
  }

  // Y scale
  let maxW=0;
  for(const h of hours){
    if(h.forecast>maxW)maxW=h.forecast;
    if(h.actualTotal>maxW)maxW=h.actualTotal;
  }
  if(maxW<100)maxW=100;
  maxW=Math.ceil(maxW/500)*500;

  function yPos(w){return pad.top+cH-(w/maxW)*cH;}
  function barH(w){return Math.max(0,(w/maxW)*cH);}

  // Y-axis gridlines + labels
  const steps=Math.min(6,Math.max(2,Math.floor(maxW/1000)));
  ctx.strokeStyle='#eee';ctx.lineWidth=1;ctx.setLineDash([]);
  ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='right';
  for(let i=0;i<=steps;i++){
    const w=maxW*(i/steps);
    const y=yPos(w);
    ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(pad.left+cW,y);ctx.stroke();
    const label=w>=1000?(w/1000).toFixed(1)+' kW':Math.round(w)+' W';
    ctx.fillText(label,pad.left-6,y+3);
  }

  const baseline=yPos(0);
  for(let i=0;i<N;i++){
    const h=hours[i];
    const gx=pad.left+i*groupW;
    const gap=groupW*0.06;

    // Left bar: Forecast (orange outline, semi-transparent fill)
    const fH=barH(h.forecast);
    const fx=gx+gap;
    ctx.fillStyle='rgba(249,115,22,0.2)';
    ctx.fillRect(fx,baseline-fH,barW,fH);
    ctx.strokeStyle='#f97316';ctx.lineWidth=1;ctx.setLineDash([]);
    ctx.strokeRect(fx,baseline-fH,barW,fH);

    // Right bar: Actual — stacked PV strings
    if(h.hasActual&&h.actualTotal>0){
      const ax=fx+barW+gap;
      // PV1 (bottom, darker yellow)
      const pv1H=barH(h.pv1);
      ctx.fillStyle='#eab308';
      ctx.fillRect(ax,baseline-pv1H,barW,pv1H);
      // PV2 (stacked on top, lighter yellow-green)
      const pv2H=barH(h.pv2);
      ctx.fillStyle='#84cc16';
      ctx.fillRect(ax,baseline-pv1H-pv2H,barW,pv2H);
      // If there's more than pv1+pv2 (other strings), fill the remainder
      const rest=h.actualTotal-h.pv1-h.pv2;
      if(rest>1){
        const restH=barH(rest);
        ctx.fillStyle='#22d3ee';
        ctx.fillRect(ax,baseline-pv1H-pv2H-restH,barW,restH);
      }
      // Outline the total actual bar
      const totalH=barH(h.actualTotal);
      ctx.strokeStyle='#a3a3a3';ctx.lineWidth=0.5;
      ctx.strokeRect(ax,baseline-totalH,barW,totalH);
    }

    // Shadow factor label (above forecast bar, where it deviates from 1.0)
    if(h.shadowFactor!=null&&Math.abs(h.shadowFactor-1.0)>0.02){
      ctx.fillStyle='#888';ctx.font='7px system-ui';ctx.textAlign='center';
      ctx.fillText((h.shadowFactor*100).toFixed(0)+'%',gx+groupW/2,baseline-barH(Math.max(h.forecast,h.actualTotal))-3);
    }

    // Hour label
    if(h.hour%2===0){
      ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='center';
      ctx.fillText(h.hour+':00',gx+groupW/2,pad.top+cH+14);
    }
  }

  // "Now" vertical line
  const nowH=now.getHours()+now.getMinutes()/60;
  for(let i=0;i<N;i++){
    if(hours[i].hour<=nowH&&(i===N-1||hours[i+1].hour>nowH)){
      const frac=nowH-hours[i].hour;
      const x=pad.left+i*groupW+frac*groupW;
      ctx.strokeStyle='#ef4444';ctx.lineWidth=1.5;ctx.setLineDash([3,2]);
      ctx.beginPath();ctx.moveTo(x,pad.top);ctx.lineTo(x,pad.top+cH);ctx.stroke();
      ctx.setLineDash([]);
      break;
    }
  }

  // Legend
  ctx.font='9px system-ui';ctx.textAlign='left';
  let lx=pad.left+8;const ly=pad.top+12;
  // Forecast
  ctx.fillStyle='rgba(249,115,22,0.2)';ctx.fillRect(lx,ly-7,10,10);
  ctx.strokeStyle='#f97316';ctx.lineWidth=1;ctx.strokeRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Forecast',lx+14,ly+1);
  lx+=ctx.measureText('Forecast').width+24;
  // PV1
  ctx.fillStyle='#eab308';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('String 1',lx+14,ly+1);
  lx+=ctx.measureText('String 1').width+24;
  // PV2
  ctx.fillStyle='#84cc16';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('String 2',lx+14,ly+1);
}

function drawConsumptionChart(timeline, loadHourly){
  const canvas=document.getElementById('consumptionCanvas');
  if(!canvas)return;
  const now=new Date();
  const todayStr=now.toISOString().slice(0,10);
  const slots=timeline.filter(s=>{const d=toLocal(s.startUtc);return d&&d.toISOString().slice(0,10)===todayStr;});
  if(slots.length===0)return;

  const dpr=window.devicePixelRatio||1;
  const rect=canvas.parentElement.getBoundingClientRect();
  canvas.width=rect.width*dpr;
  canvas.height=rect.height*dpr;
  canvas.style.width=rect.width+'px';
  canvas.style.height=rect.height+'px';
  const ctx=canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  const W=rect.width,H=rect.height;
  const pad={top:24,right:16,bottom:30,left:50};
  const cW=W-pad.left-pad.right,cH=H-pad.top-pad.bottom;
  const N=slots.length;
  const groupW=cW/N;
  const barW=groupW*0.38;

  // Build per-hour data
  const hours=[];
  for(let i=0;i<N;i++){
    const st=toLocal(slots[i].startUtc);
    const h=st.getHours();
    const expected=slots[i].consumptionWatts||0;
    const actual=loadHourly[String(h)];
    hours.push({
      hour:h,
      expected:expected,
      actual:actual?actual.total:0,
      hasActual:!!actual
    });
  }

  // Y scale
  let maxW=0;
  for(const h of hours){
    if(h.expected>maxW)maxW=h.expected;
    if(h.actual>maxW)maxW=h.actual;
  }
  if(maxW<500)maxW=500;
  maxW=Math.ceil(maxW/500)*500;

  function yPos(w){return pad.top+cH-(w/maxW)*cH;}
  function barH(w){return Math.max(0,(w/maxW)*cH);}
  const baseline=yPos(0);

  // Y-axis gridlines
  const steps=Math.min(6,Math.max(2,Math.floor(maxW/1000)));
  ctx.strokeStyle='#eee';ctx.lineWidth=1;ctx.setLineDash([]);
  ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='right';
  for(let i=0;i<=steps;i++){
    const w=maxW*(i/steps);
    const y=yPos(w);
    ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(pad.left+cW,y);ctx.stroke();
    const label=w>=1000?(w/1000).toFixed(1)+' kW':Math.round(w)+' W';
    ctx.fillText(label,pad.left-6,y+3);
  }

  for(let i=0;i<N;i++){
    const h=hours[i];
    const gx=pad.left+i*groupW;
    const gap=groupW*0.06;

    // Left bar: Expected (blue outline, semi-transparent)
    const eH=barH(h.expected);
    const ex=gx+gap;
    ctx.fillStyle='rgba(59,130,246,0.15)';
    ctx.fillRect(ex,baseline-eH,barW,eH);
    ctx.strokeStyle='#3b82f6';ctx.lineWidth=1;ctx.setLineDash([]);
    ctx.strokeRect(ex,baseline-eH,barW,eH);

    // Right bar: Actual (solid red/orange)
    if(h.hasActual&&h.actual>0){
      const ax=ex+barW+gap;
      const aH=barH(h.actual);
      // Color: green if below expected, orange if above
      ctx.fillStyle=h.actual<=h.expected*1.1?'rgba(34,197,94,0.6)':'rgba(249,115,22,0.6)';
      ctx.fillRect(ax,baseline-aH,barW,aH);
      ctx.strokeStyle='#a3a3a3';ctx.lineWidth=0.5;
      ctx.strokeRect(ax,baseline-aH,barW,aH);
    }

    // Hour label
    if(h.hour%2===0){
      ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='center';
      ctx.fillText(h.hour+':00',gx+groupW/2,pad.top+cH+14);
    }
  }

  // "Now" line
  const nowH=now.getHours()+now.getMinutes()/60;
  for(let i=0;i<N;i++){
    if(hours[i].hour<=nowH&&(i===N-1||hours[i+1].hour>nowH)){
      const frac=nowH-hours[i].hour;
      const x=pad.left+i*groupW+frac*groupW;
      ctx.strokeStyle='#ef4444';ctx.lineWidth=1.5;ctx.setLineDash([3,2]);
      ctx.beginPath();ctx.moveTo(x,pad.top);ctx.lineTo(x,pad.top+cH);ctx.stroke();
      ctx.setLineDash([]);
      break;
    }
  }

  // Legend
  ctx.font='9px system-ui';ctx.textAlign='left';
  let lx=pad.left+8;const ly=pad.top+12;
  ctx.fillStyle='rgba(59,130,246,0.15)';ctx.fillRect(lx,ly-7,10,10);
  ctx.strokeStyle='#3b82f6';ctx.lineWidth=1;ctx.strokeRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Verwacht',lx+14,ly+1);
  lx+=ctx.measureText('Verwacht').width+24;
  ctx.fillStyle='rgba(34,197,94,0.6)';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Werkelijk',lx+14,ly+1);
  lx+=ctx.measureText('Werkelijk').width+24;
  ctx.fillStyle='rgba(249,115,22,0.6)';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Boven verwacht',lx+14,ly+1);
}

function drawBalanceChart(timeline){
  const canvas=document.getElementById('balanceCanvas');
  if(!canvas)return;
  const now=new Date();
  const todayStr=now.toISOString().slice(0,10);
  const slots=timeline.filter(s=>{const d=toLocal(s.startUtc);return d&&d.toISOString().slice(0,10)===todayStr;});
  if(slots.length===0)return;

  const dpr=window.devicePixelRatio||1;
  const rect=canvas.parentElement.getBoundingClientRect();
  canvas.width=rect.width*dpr;
  canvas.height=rect.height*dpr;
  canvas.style.width=rect.width+'px';
  canvas.style.height=rect.height+'px';
  const ctx=canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  const W=rect.width,H=rect.height;
  const pad={top:24,right:16,bottom:30,left:50};
  const cW=W-pad.left-pad.right,cH=H-pad.top-pad.bottom;
  const N=slots.length;
  const barW=cW/N;

  // Y scale: max of consumption or PV
  let maxW=0;
  for(const s of slots){
    if(s.consumptionWatts>maxW)maxW=s.consumptionWatts;
    if(s.pvWatts>maxW)maxW=s.pvWatts;
  }
  if(maxW<500)maxW=500;
  maxW=Math.ceil(maxW/500)*500;

  function yPos(w){return pad.top+cH-(w/maxW)*cH;}
  function bH(w){return Math.max(0,(w/maxW)*cH);}
  const baseline=yPos(0);

  // Y-axis gridlines
  const steps=Math.min(6,Math.max(2,Math.floor(maxW/1000)));
  ctx.strokeStyle='#eee';ctx.lineWidth=1;ctx.setLineDash([]);
  ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='right';
  for(let i=0;i<=steps;i++){
    const w=maxW*(i/steps);
    const y=yPos(w);
    ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(pad.left+cW,y);ctx.stroke();
    const label=w>=1000?(w/1000).toFixed(1)+' kW':Math.round(w)+' W';
    ctx.fillText(label,pad.left-6,y+3);
  }

  for(let i=0;i<N;i++){
    const s=slots[i];
    const x=pad.left+i*barW;
    const gap=2;
    const consumption=s.consumptionWatts||0;
    const pv=s.pvWatts||0;
    const net=consumption-pv; // positive = deficit (need grid/battery), negative = surplus

    // Consumption bar (red/orange outline)
    const cH2=bH(consumption);
    ctx.fillStyle='rgba(239,68,68,0.15)';
    ctx.fillRect(x+gap,baseline-cH2,barW-2*gap,cH2);
    ctx.strokeStyle='#ef4444';ctx.lineWidth=0.8;
    ctx.strokeRect(x+gap,baseline-cH2,barW-2*gap,cH2);

    // PV contribution (yellow fill, stacked from bottom)
    const pvCover=Math.min(pv,consumption); // PV covering consumption
    const pvH=bH(pvCover);
    ctx.fillStyle='rgba(234,179,8,0.5)';
    ctx.fillRect(x+gap,baseline-pvH,barW-2*gap,pvH);

    // Battery contribution (green, on top of PV if deficit)
    if(net>0){
      // Deficit: battery could cover some
      const batH=bH(Math.min(net,5000)); // cap visual at 5kW
      ctx.fillStyle='rgba(34,197,94,0.4)';
      ctx.fillRect(x+gap,baseline-pvH-batH,barW-2*gap,batH);
    }

    // Surplus indicator (small blue bar above)
    if(net<0){
      const surplusH=bH(Math.min(-net,maxW*0.3));
      ctx.fillStyle='rgba(96,165,250,0.3)';
      ctx.fillRect(x+gap,baseline-cH2-surplusH,barW-2*gap,surplusH);
    }

    // Hour label
    const st=toLocal(s.startUtc);
    if(st.getHours()%2===0){
      ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='center';
      ctx.fillText(st.getHours()+':00',x+barW/2,pad.top+cH+14);
    }
  }

  // "Now" line
  const nowH=now.getHours()+now.getMinutes()/60;
  for(let i=0;i<N;i++){
    const st=toLocal(slots[i].startUtc);
    if(st.getHours()<=nowH&&(i===N-1||toLocal(slots[i+1].startUtc).getHours()>nowH)){
      const frac=nowH-st.getHours();
      const x=pad.left+i*barW+frac*barW;
      ctx.strokeStyle='#ef4444';ctx.lineWidth=1.5;ctx.setLineDash([3,2]);
      ctx.beginPath();ctx.moveTo(x,pad.top);ctx.lineTo(x,pad.top+cH);ctx.stroke();
      ctx.setLineDash([]);
      break;
    }
  }

  // Legend
  ctx.font='9px system-ui';ctx.textAlign='left';
  let lx=pad.left+8;const ly=pad.top+12;
  ctx.fillStyle='rgba(239,68,68,0.15)';ctx.fillRect(lx,ly-7,10,10);
  ctx.strokeStyle='#ef4444';ctx.lineWidth=0.8;ctx.strokeRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Verbruik',lx+14,ly+1);
  lx+=ctx.measureText('Verbruik').width+24;
  ctx.fillStyle='rgba(234,179,8,0.5)';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Zon',lx+14,ly+1);
  lx+=ctx.measureText('Zon').width+24;
  ctx.fillStyle='rgba(34,197,94,0.4)';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Batterij',lx+14,ly+1);
  lx+=ctx.measureText('Batterij').width+24;
  ctx.fillStyle='rgba(96,165,250,0.3)';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Overschot',lx+14,ly+1);
}

function drawTradeChart(timeline, actions){
  const canvas=document.getElementById('tradeCanvas');
  if(!canvas||!actions||!actions.length)return;

  const dpr=window.devicePixelRatio||1;
  const rect=canvas.parentElement.getBoundingClientRect();
  canvas.width=rect.width*dpr;
  canvas.height=rect.height*dpr;
  canvas.style.width=rect.width+'px';
  canvas.style.height=rect.height+'px';
  const ctx=canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  const W=rect.width,H=rect.height;
  const pad={top:28,right:55,bottom:30,left:50};
  const cW=W-pad.left-pad.right,cH=H-pad.top-pad.bottom;
  const midY=pad.top+cH*0.45; // center line (slightly above center for more sell room)

  // Build per-slot trade data from actions
  const slotStarts=timeline.map(s=>toLocal(s.startUtc));
  const N=timeline.length;
  if(N===0)return;
  const barW=cW/N;

  // Map actions to slots
  const slotTrade=timeline.map((_,i)=>{
    const st=slotStarts[i];
    if(!st)return {buy:0,sell:0,solar:0,buyCost:0,sellRev:0,solarVal:0,price:0};
    const slotEnd=new Date(st.getTime()+3600000);
    let buy=0,sell=0,solar=0,buyCost=0,sellRev=0,solarVal=0;
    for(const a of actions){
      const as=toLocal(a.startUtc),ae=toLocal(a.endUtc);
      if(!as||!ae||as>=slotEnd||ae<=st)continue;
      if(a.kind==='ChargeBattery'){buy+=a.kwh||0;buyCost+=Math.abs(a.eurSavings||0);}
      else if(a.kind==='ExportToGrid'){sell+=a.kwh||0;sellRev+=a.eurSavings||0;}
      else if(a.kind==='SolarCharge'){solar+=a.kwh||0;solarVal+=a.eurSavings||0;}
    }
    return {buy,sell,solar,buyCost,sellRev,solarVal,price:timeline[i].priceEurKwh||0};
  });

  // Y scale: max of buy or sell kWh
  let maxKwh=1;
  for(const t of slotTrade){
    if(t.buy+t.solar>maxKwh)maxKwh=t.buy+t.solar;
    if(t.sell>maxKwh)maxKwh=t.sell;
  }
  maxKwh=Math.ceil(maxKwh/5)*5;
  if(maxKwh<5)maxKwh=5;

  const topH=midY-pad.top;    // sell goes up
  const botH=pad.top+cH-midY; // buy goes down

  function sellY(kwh){return midY-kwh/maxKwh*topH;}
  function buyY(kwh){return midY+kwh/maxKwh*botH;}

  // Center line
  ctx.strokeStyle='#d1d5db';ctx.lineWidth=1;ctx.setLineDash([]);
  ctx.beginPath();ctx.moveTo(pad.left,midY);ctx.lineTo(pad.left+cW,midY);ctx.stroke();

  // Y-axis gridlines
  ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='right';
  ctx.strokeStyle='#f0f0f0';ctx.lineWidth=0.5;
  for(let v=0;v<=maxKwh;v+=Math.max(1,Math.ceil(maxKwh/4))){
    if(v===0)continue;
    // Sell side (up)
    const ys=sellY(v);
    ctx.beginPath();ctx.moveTo(pad.left,ys);ctx.lineTo(pad.left+cW,ys);ctx.stroke();
    ctx.fillText(v+' kWh',pad.left-4,ys+3);
    // Buy side (down)
    const yb=buyY(v);
    ctx.beginPath();ctx.moveTo(pad.left,yb);ctx.lineTo(pad.left+cW,yb);ctx.stroke();
    ctx.fillText(v+' kWh',pad.left-4,yb+3);
  }

  // Labels
  ctx.fillStyle='#dc2626';ctx.font='bold 9px system-ui';ctx.textAlign='left';
  ctx.fillText('VERKOOP ↑',pad.left+2,pad.top+10);
  ctx.fillStyle='#22c55e';
  ctx.fillText('INKOOP ↓',pad.left+2,pad.top+cH-4);

  // Price scale (right axis)
  const prices=slotTrade.map(t=>t.price);
  const pMax=Math.max(0.01,...prices);
  const pMin=Math.min(0,...prices);
  const pRange=pMax-pMin||0.01;

  // Draw bars + price line
  const now=new Date();
  ctx.setLineDash([]);

  // Price line points
  const pricePts=[];

  for(let i=0;i<N;i++){
    const t=slotTrade[i];
    const x=pad.left+i*barW;
    const bw=barW-2;

    // Sell bar (above center, red)
    if(t.sell>0.1){
      const h=t.sell/maxKwh*topH;
      ctx.fillStyle='rgba(220,38,38,0.7)';
      ctx.fillRect(x+1,midY-h,bw,h);
      // Euro label
      if(t.sellRev>0.1){
        ctx.fillStyle='#dc2626';ctx.font='bold 8px system-ui';ctx.textAlign='center';
        ctx.fillText('+€'+t.sellRev.toFixed(2),x+barW/2,midY-h-3);
      }
    }

    // Solar bar (above center, yellow, stacked below sell)
    if(t.solar>0.1){
      const h=t.solar/maxKwh*topH;
      const sellH=t.sell>0?t.sell/maxKwh*topH:0;
      // Solar doesn't stack with sell (different slots), show as separate yellow bar
      if(t.sell<0.1){
        ctx.fillStyle='rgba(234,179,8,0.5)';
        ctx.fillRect(x+1,midY-h,bw,h);
      }
    }

    // Buy bar (below center, green)
    if(t.buy>0.1){
      const h=t.buy/maxKwh*botH;
      ctx.fillStyle='rgba(34,197,94,0.6)';
      ctx.fillRect(x+1,midY,bw,h);
      // Euro label
      ctx.fillStyle='#16a34a';ctx.font='bold 8px system-ui';ctx.textAlign='center';
      ctx.fillText('-€'+t.buyCost.toFixed(2),x+barW/2,midY+h+10);
    }

    // Price line point
    const py=midY-((t.price-pMin)/pRange-0.5)*cH*0.6;
    pricePts.push({x:x+barW/2,y:py});

    // Hour label
    if(slotStarts[i]&&slotStarts[i].getHours()%3===0){
      ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='center';
      ctx.fillText(slotStarts[i].getHours()+':00',x+barW/2,pad.top+cH+14);
    }

    // Day separator
    if(i>0&&slotStarts[i]&&slotStarts[i].getHours()===0){
      ctx.strokeStyle='#ccc';ctx.lineWidth=1;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(x,pad.top);ctx.lineTo(x,pad.top+cH);ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle='#888';ctx.font='bold 9px system-ui';ctx.textAlign='left';
      ctx.fillText(slotStarts[i].toLocaleDateString('nl-NL',{weekday:'short',day:'numeric'}),x+3,pad.top+cH+26);
    }
  }

  // Draw price line
  if(pricePts.length>1){
    ctx.beginPath();
    ctx.strokeStyle='rgba(99,102,241,0.6)';ctx.lineWidth=1.5;ctx.setLineDash([4,3]);
    pricePts.forEach((p,i)=>{if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);});
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Price axis labels (right side)
  ctx.fillStyle='#6366f1';ctx.font='9px system-ui';ctx.textAlign='left';
  const priceSteps=[pMin,pMin+(pMax-pMin)*0.5,pMax];
  priceSteps.forEach(p=>{
    const py=midY-((p-pMin)/pRange-0.5)*cH*0.6;
    ctx.fillText('€'+p.toFixed(3),pad.left+cW+4,py+3);
  });

  // "Now" line
  for(let i=0;i<N;i++){
    const st=slotStarts[i];
    if(st&&st<=now&&new Date(st.getTime()+3600000)>now){
      const frac=(now-st)/3600000;
      const x=pad.left+i*barW+frac*barW;
      ctx.strokeStyle='#ef4444';ctx.lineWidth=1.5;ctx.setLineDash([3,2]);
      ctx.beginPath();ctx.moveTo(x,pad.top);ctx.lineTo(x,pad.top+cH);ctx.stroke();
      ctx.setLineDash([]);
      break;
    }
  }

  // Legend
  ctx.font='9px system-ui';ctx.textAlign='left';
  let lx=pad.left+80;const ly=pad.top+10;
  ctx.fillStyle='rgba(220,38,38,0.7)';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Verkoop',lx+14,ly+1);
  lx+=ctx.measureText('Verkoop').width+24;
  ctx.fillStyle='rgba(34,197,94,0.6)';ctx.fillRect(lx,ly-7,10,10);
  ctx.fillStyle='#666';ctx.fillText('Inkoop',lx+14,ly+1);
  lx+=ctx.measureText('Inkoop').width+24;
  ctx.strokeStyle='rgba(99,102,241,0.6)';ctx.lineWidth=1.5;ctx.setLineDash([4,3]);
  ctx.beginPath();ctx.moveTo(lx,ly-2);ctx.lineTo(lx+12,ly-2);ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle='#666';ctx.fillText('Prijs',lx+16,ly+1);

  // Totals summary at bottom-right
  const totBuy=slotTrade.reduce((s,t)=>s+t.buyCost,0);
  const totSell=slotTrade.reduce((s,t)=>s+t.sellRev,0);
  const totNet=totSell-totBuy;
  ctx.font='bold 10px system-ui';ctx.textAlign='right';
  ctx.fillStyle='#dc2626';ctx.fillText('Verkoop: +€'+totSell.toFixed(2),pad.left+cW+pad.right-4,pad.top+cH-18);
  ctx.fillStyle='#16a34a';ctx.fillText('Inkoop: -€'+totBuy.toFixed(2),pad.left+cW+pad.right-4,pad.top+cH-6);
  ctx.fillStyle=totNet>=0?'#16a34a':'#dc2626';
  ctx.fillText('Netto: '+(totNet>=0?'+':'')+' €'+totNet.toFixed(2),pad.left+cW+pad.right-4,pad.top+cH+6);
}

function drawPlanChart(timeline,actions,batSoC,evSoC){
  const canvas=document.getElementById('planCanvas');
  if(!canvas)return;
  const dpr=window.devicePixelRatio||1;
  const rect=canvas.parentElement.getBoundingClientRect();
  canvas.width=rect.width*dpr;
  canvas.height=rect.height*dpr;
  canvas.style.width=rect.width+'px';
  canvas.style.height=rect.height+'px';
  const ctx=canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  const W=rect.width,H=rect.height;
  const pad={top:20,right:50,bottom:30,left:45};
  const cW=W-pad.left-pad.right,cH=H-pad.top-pad.bottom;
  const N=timeline.length;
  if(N===0)return;
  const barW=cW/N;

  // Price range
  const prices=timeline.map(s=>s.priceEurKwh);
  const minP=Math.min(...prices,0);
  const maxP=Math.max(...prices);
  const pRange=maxP-minP||0.01;

  // Map timeline slots to start times
  const slotStarts=timeline.map(s=>toLocal(s.startUtc));
  const now=new Date();

  // Build action lookup: for each slot index, which action kinds apply?
  const slotActions=timeline.map((_,i)=>{
    const slotStart=slotStarts[i];
    const slotEnd=new Date(slotStart.getTime()+3600000);
    const kinds=[];
    for(const a of actions){
      const as=toLocal(a.startUtc),ae=toLocal(a.endUtc);
      if(as<slotEnd&&ae>slotStart)kinds.push(a.kind);
    }
    return kinds;
  });

  // Draw price bars
  for(let i=0;i<N;i++){
    const x=pad.left+i*barW;
    const price=prices[i];
    const pctFromBottom=(price-minP)/pRange;
    const barH=Math.max(2,pctFromBottom*cH*0.65);
    const y=pad.top+cH-barH;

    // Bar color: action overlay or default price color
    const kinds=slotActions[i];
    let col='#d1d5db'; // default gray
    if(kinds.length){
      col=actionColors[kinds[0]]||col;
    }else if(price<0){
      col='#ef4444';
    }else{
      // Gradient from green (cheap) to blue (mid) to orange (expensive)
      const t=pctFromBottom;
      if(t<0.33)col='#22c55e';
      else if(t<0.66)col='#60a5fa';
      else col='#f97316';
    }

    // Highlight current hour
    const isNow=slotStarts[i]&&slotStarts[i]<=now&&new Date(slotStarts[i].getTime()+3600000)>now;
    if(isNow){
      ctx.fillStyle='rgba(26,122,46,0.08)';
      ctx.fillRect(x,pad.top,barW,cH);
    }

    ctx.fillStyle=col;
    ctx.fillRect(x+1,y,barW-2,barH);

    // Hour label every 3 hours
    if(slotStarts[i]&&slotStarts[i].getHours()%3===0){
      ctx.fillStyle='#999';
      ctx.font='9px system-ui';
      ctx.textAlign='center';
      ctx.fillText(slotStarts[i].getHours()+':00',x+barW/2,pad.top+cH+14);
    }

    // Day separator
    if(i>0&&slotStarts[i]&&slotStarts[i].getHours()===0){
      ctx.strokeStyle='#ccc';
      ctx.lineWidth=1;
      ctx.setLineDash([3,3]);
      ctx.beginPath();
      ctx.moveTo(x,pad.top);
      ctx.lineTo(x,pad.top+cH);
      ctx.stroke();
      ctx.setLineDash([]);
      // Day label
      ctx.fillStyle='#888';
      ctx.font='bold 9px system-ui';
      ctx.textAlign='left';
      ctx.fillText(slotStarts[i].toLocaleDateString('nl-NL',{weekday:'short',day:'numeric'}),x+3,pad.top+cH+26);
    }
  }

  // Price Y-axis labels
  ctx.fillStyle='#999';ctx.font='9px system-ui';ctx.textAlign='right';
  const steps=[minP,minP+pRange*0.33,minP+pRange*0.66,maxP];
  for(const v of steps){
    const y=pad.top+cH-(((v-minP)/pRange)*cH*0.65);
    ctx.fillText('€'+v.toFixed(2),pad.left-4,y+3);
    ctx.strokeStyle='#f0f0f0';ctx.lineWidth=0.5;
    ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(pad.left+cW,y);ctx.stroke();
  }

  // Battery SoC curve (left axis, 0-100%)
  if(batSoC.length>1){
    ctx.strokeStyle='#f59e0b';ctx.lineWidth=2.5;ctx.setLineDash([]);
    ctx.beginPath();
    let first=true;
    for(const pt of batSoC){
      const ts=toLocal(pt.timestampUtc);
      if(!ts)continue;
      // Find x position by time interpolation
      const t0=slotStarts[0].getTime(),tEnd=slotStarts[N-1].getTime()+3600000;
      const frac=(ts.getTime()-t0)/(tEnd-t0);
      const x=pad.left+frac*cW;
      const pct=pt.capacityKwh>0?pt.soCKwh/pt.capacityKwh:0;
      const y=pad.top+cH*(1-pct);
      if(x<pad.left||x>pad.left+cW)continue;
      if(first){ctx.moveTo(x,y);first=false;}else ctx.lineTo(x,y);
    }
    ctx.stroke();
    // Label
    ctx.fillStyle='#f59e0b';ctx.font='bold 9px system-ui';ctx.textAlign='left';
    ctx.fillText('Bat SoC',pad.left+cW+4,pad.top+12);
  }

  // EV SoC curve (right side label)
  if(evSoC.length>1){
    ctx.strokeStyle='#3b82f6';ctx.lineWidth=2;ctx.setLineDash([6,3]);
    ctx.beginPath();
    let first=true;
    for(const pt of evSoC){
      const ts=toLocal(pt.timestampUtc);
      if(!ts)continue;
      const t0=slotStarts[0].getTime(),tEnd=slotStarts[N-1].getTime()+3600000;
      const frac=(ts.getTime()-t0)/(tEnd-t0);
      const x=pad.left+frac*cW;
      const pct=pt.capacityKwh>0?pt.soCKwh/pt.capacityKwh:0;
      const y=pad.top+cH*(1-pct);
      if(x<pad.left||x>pad.left+cW)continue;
      if(first){ctx.moveTo(x,y);first=false;}else ctx.lineTo(x,y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle='#3b82f6';ctx.font='bold 9px system-ui';
    ctx.fillText('EV SoC',pad.left+cW+4,pad.top+26);
  }

  // SoC right axis labels (0%, 50%, 100%)
  if(batSoC.length>1||evSoC.length>1){
    ctx.fillStyle='#bbb';ctx.font='9px system-ui';ctx.textAlign='left';
    ctx.fillText('100%',pad.left+cW+4,pad.top+cH*0+10);
    ctx.fillText('50%',pad.left+cW+4,pad.top+cH*0.5+3);
    ctx.fillText('0%',pad.left+cW+4,pad.top+cH);
  }

  // "Now" line
  if(slotStarts[0]){
    const t0=slotStarts[0].getTime(),tEnd=slotStarts[N-1].getTime()+3600000;
    const frac=(now.getTime()-t0)/(tEnd-t0);
    if(frac>=0&&frac<=1){
      const x=pad.left+frac*cW;
      ctx.strokeStyle='#ef4444';ctx.lineWidth=1.5;ctx.setLineDash([4,2]);
      ctx.beginPath();ctx.moveTo(x,pad.top);ctx.lineTo(x,pad.top+cH);ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle='#ef4444';ctx.font='bold 9px system-ui';ctx.textAlign='center';
      ctx.fillText('nu',x,pad.top-4);
    }
  }

  // Legend
  const legendY=pad.top-8;
  const legendItems=[
    {col:'#22c55e',label:'Laden'},{col:'#f97316',label:'Ontladen'},
    {col:'#3b82f6',label:'Auto'},{col:'#a855f7',label:'Beperken'},
    {col:'#d1d5db',label:'Geen actie'}
  ];
  let lx=pad.left;
  ctx.font='8px system-ui';
  for(const li of legendItems){
    ctx.fillStyle=li.col;
    ctx.fillRect(lx,legendY-6,10,8);
    ctx.fillStyle='#888';
    ctx.textAlign='left';
    ctx.fillText(li.label,lx+13,legendY+1);
    lx+=ctx.measureText(li.label).width+22;
  }
}

async function poll(){
  try{
    const r=await fetch('./status');
    if(!r.ok)throw new Error(r.status);
    const d=await r.json();
    dot.className='status-dot green';
    conn.textContent='Verbonden — '+new Date(d.timestamp*1000).toLocaleTimeString('nl-NL');
    errEl.style.display='none';
    renderPowerFlow(d.readings||{}, d.executor||'', d.prices||{}, d.plan||null);
    syncControlPanel(d.override);
    let html='';
    for(const[k,v]of Object.entries(d.readings||{})){
      const suffix=k.replace(/^.*?_/,'');
      const lbl=labels[suffix]||k;
      const cls=v.value===0?'off':'ok';
      html+=`<div class="card ${cls}"><div class="label">${lbl}</div><div class="value">${v.value}</div><div class="unit">${v.unit||''}</div></div>`;
    }
    const p=d.prices||{};
    const pv=(k)=>{const o=p[k];return o&&o.value!=null?o.value:'—';};
    const pc=(k)=>{const v=pv(k);return typeof v==='number'?(v<0?'warn':'ok'):'off';};
    if(Object.keys(p).length){
      html+=`<div class="card ${pc('now')}"><div class="label">Prijs nu</div><div class="value">${typeof pv('now')==='number'?'€ '+pv('now').toFixed(4):'—'}</div><div class="unit">EUR/kWh${pv('rank_now')!=='—'?' · rang '+pv('rank_now')+'/24':''}</div></div>`;
      html+=`<div class="card ok"><div class="label">Vandaag gem.</div><div class="value">${typeof pv('today_avg')==='number'?'€ '+pv('today_avg').toFixed(4):'—'}</div><div class="unit">${typeof pv('today_min')==='number'?'min € '+pv('today_min').toFixed(4)+' · max € '+pv('today_max').toFixed(4):''}</div></div>`;
      if(pv('tomorrow_avg')!=='—'&&pv('tomorrow_avg')!=null)html+=`<div class="card ok"><div class="label">Morgen gem.</div><div class="value">${'€ '+pv('tomorrow_avg').toFixed(4)}</div><div class="unit">min € ${pv('tomorrow_min').toFixed(4)} · max € ${pv('tomorrow_max').toFixed(4)}</div></div>`;
      if(pv('negative_hours_today')!=='—')html+=`<div class="card ${pv('negative_hours_today')>0?'warn':'off'}"><div class="label">Negatieve uren</div><div class="value">${pv('negative_hours_today')}</div><div class="unit">uren vandaag</div></div>`;
    }
    grid.innerHTML=html||'<div class="card off"><div class="label">Wachten op data</div><div class="value">—</div></div>';
    // Render EMS plan section
    renderPlan(d.plan||null, d.pvHourly||{}, d.loadHourly||{});
  }catch(e){
    dot.className='status-dot red';
    conn.textContent='Geen verbinding';
    errEl.textContent=e.message;errEl.style.display='block';
  }
}
poll();setInterval(poll,10000);

// --- Simulator ---
async function runSim(){
  const btn=document.getElementById('sim-btn');
  const out=document.getElementById('sim-out');
  if(!btn)return;
  btn.disabled=true;btn.textContent='Berekenen...';
  out.textContent='';
  try{
    const days=document.getElementById('sim-days')?.value||7;
    const sweep=document.getElementById('sim-sweep')?.checked?'true':'false';
    const loads=document.getElementById('sim-loads')?.value||'';
    let url=`./simulate?days=${days}&sweep=${sweep}`;
    if(loads)url+=`&loads=${encodeURIComponent(loads)}`;
    const r=await fetch(url);
    const d=await r.json();
    let txt='Databron: '+d.data_source+'\\n';
    if(d.errors&&d.errors.length)txt+='⚠ '+d.errors.join('\\n⚠ ')+'\\n';
    if(d.schedule)txt+=d.schedule+'\\n';
    txt+=(d.comparison||'');
    if(d.daily_breakdown)txt+='\\n'+d.daily_breakdown;
    if(d.sweep)txt+='\\n'+d.sweep;
    if(d.optimal_params)txt+='\\nOptimale params: '+JSON.stringify(d.optimal_params);
    out.textContent=txt;
  }catch(e){out.textContent='Error: '+e.message;}
  btn.disabled=false;btn.textContent='Simulatie starten';
}
</script>
</body></html>"""
        return web.Response(text=html, content_type="text/html")

    async def simulate(req: web.Request) -> web.Response:
        """GET /simulate?days=7&sweep=false&strategy=saldering

        Data sources (in priority order):
          1. Already-fetched prices from PricesPoller (_latest_prices) — 48h, no extra call
          2. Historical prices from Saldox API (/api/prices/hourly) — multi-day backtest
          3. Synthetic data — fallback when no API configured
        """
        from datetime import datetime as dt, timedelta as td, timezone as tz

        days = int(req.query.get("days", "7"))
        do_sweep = req.query.get("sweep", "false").lower() in ("true", "1")
        strategy_filter = req.query.get("strategy", "")  # empty = all

        slots: list[HourSlot] = []
        data_source = "synthetic"
        errors: list[str] = []

        api_url = os.environ.get("SALDOX_API_URL", "").strip()
        api_token = os.environ.get("SALDOX_API_TOKEN", "").strip()

        # --- Source 1: use already-fetched prices from PricesPoller ---
        today_prices = _latest_prices.get("prices_today", {}).get("value", [])
        tomorrow_prices = _latest_prices.get("prices_tomorrow", {}).get("value", [])
        if today_prices or tomorrow_prices:
            now_utc = dt.now(tz.utc)
            from .prices_poller import _nl_offset_for
            offset = _nl_offset_for(now_utc)
            local_now = now_utc + offset
            local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_utc = local_midnight - offset

            for hp in (today_prices or []):
                hour_local = hp.get("hour", 0)
                hour_utc = today_start_utc + td(hours=hour_local) - offset + offset  # already local→utc via start
                dt_utc = today_start_utc + td(hours=hour_local)
                slots.append(HourSlot(
                    hour_utc=dt_utc,
                    price_eur_kwh=float(hp.get("price", 0)),
                ))
            for hp in (tomorrow_prices or []):
                hour_local = hp.get("hour", 0)
                dt_utc = today_start_utc + td(days=1, hours=hour_local)
                slots.append(HourSlot(
                    hour_utc=dt_utc,
                    price_eur_kwh=float(hp.get("price", 0)),
                ))
            if slots:
                data_source = f"live-prices ({len(slots)} uur)"
                _LOG.info("Simulator: %d uur uit PricesPoller cache", len(slots))

        # --- Source 2: historical prices from API (for multi-day backtest) ---
        if days > 2 and api_url and api_token:
            to_utc = dt.now(tz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            from_utc = to_utc - td(days=days)
            try:
                raw = await fetch_prices_from_api(api_url, api_token, from_utc, to_utc)
                if raw:
                    api_slots = parse_api_prices(raw)
                    if api_slots:
                        slots = api_slots  # replace with fuller dataset
                        data_source = f"saldox-api ({len(api_slots)} uur, {days} dagen)"
                        _LOG.info("Simulator: %d uur uit API (%d dagen)", len(api_slots), days)
                else:
                    errors.append(f"API gaf geen data terug voor {days} dagen")
            except Exception as ex:
                errors.append(f"API fout: {ex}")
                _LOG.warning("Simulator API fetch failed: %s", ex)
        elif days > 2 and not api_url:
            errors.append("SALDOX_API_URL niet geconfigureerd — kan geen historische prijzen ophalen")

        # --- Source 3: synthetic fallback ---
        if not slots:
            slots = generate_synthetic_dataset(days)
            data_source = "synthetic (geen echte data beschikbaar)"
            if not errors:
                errors.append("Geen prijsdata beschikbaar — synthetische data gebruikt")

        slots = enrich_slots_with_profiles(slots, pv_peak_kw=10.0, base_consumption_w=800.0)

        config = ArbitrageConfig()
        strategies = None
        if strategy_filter:
            strategies = [s.strip() for s in strategy_filter.split(",")]

        results = run_full_simulation(slots, config, strategies)
        output = {
            "data_source": data_source,
            "errors": errors,
            "days": days,
            "slots_count": len(slots),
            "comparison": format_comparison_table(results),
            "daily_breakdown": format_daily_breakdown(results),
            "results": [
                {
                    "strategy": r.strategy,
                    "total_profit_eur": r.total_profit_eur,
                    "total_naive_cost_eur": r.total_naive_cost_eur,
                    "total_savings_eur": r.total_savings_eur,
                    "avg_daily_profit_eur": r.avg_daily_profit_eur,
                    "total_cycles": r.total_cycles,
                }
                for r in results
            ],
        }

        if do_sweep:
            sweep_strategy = strategy_filter.split(",")[0] if strategy_filter else "saldering"
            sweep = parameter_sweep(slots, strategy=sweep_strategy)
            output["sweep"] = format_sweep_table(sweep)
            output["optimal_params"] = sweep[0].params if sweep else {}
            output["optimal_profit"] = sweep[0].profit_eur if sweep else 0

        # --- Planned loads scheduling ---
        # loads=wasmachine,vaatwasser or loads=wasmachine:2000:2.5,custom:1500:1
        loads_param = req.query.get("loads", "").strip()
        if loads_param:
            planned: list[PlannedLoad] = []
            for item in loads_param.split(","):
                parts = item.strip().split(":")
                name = parts[0]
                if len(parts) == 3:
                    # Custom: name:watts:hours
                    planned.append(PlannedLoad(
                        name=name,
                        avg_watts=float(parts[1]),
                        duration_hours=float(parts[2]),
                    ))
                elif name.lower().replace(" ", "_") in APPLIANCE_PROFILES:
                    planned.append(PlannedLoad.from_profile(name))
                else:
                    errors.append(f"Onbekend apparaat '{name}'. Keuze: {', '.join(APPLIANCE_PROFILES)}")

            if planned:
                schedule = schedule_multiple_loads(planned, slots)
                output["schedule"] = format_schedule_table(schedule)
                output["schedule_items"] = [
                    {
                        "name": r.name,
                        "start_hour": r.best_start_hour,
                        "end_hour": r.end_hour,
                        "start_utc": r.best_start_utc,
                        "kwh": r.kwh,
                        "cost_eur": r.cost_eur,
                        "worst_cost_eur": r.worst_cost_eur,
                        "savings_eur": r.savings_eur,
                        "avg_price_eur": r.avg_price_eur,
                        "pv_coverage_pct": r.pv_coverage_pct,
                    }
                    for r in schedule
                ]

        return web.json_response(output)

    async def price_index(_req: web.Request) -> web.Response:
        """GET /price-index — current EPEX price position + wait advice."""
        from datetime import datetime, timezone, timedelta
        prices = _latest_prices
        if not prices:
            return web.json_response({"available": False, "reason": "Geen prijsdata"})

        now_utc = datetime.now(timezone.utc)
        now_hour = now_utc.replace(minute=0, second=0, microsecond=0)

        # Build sorted price list for next 24h
        hourly = []
        for key, val in prices.items():
            try:
                h = datetime.fromisoformat(str(key).replace("Z", "+00:00"))
                p = float(val) if not isinstance(val, dict) else float(val.get("price", val.get("priceEurKwh", 0)))
            except (ValueError, TypeError, AttributeError):
                continue
            if h >= now_hour - timedelta(hours=1) and h <= now_hour + timedelta(hours=24):
                hourly.append({"hour": h.isoformat(), "price": round(p, 4)})
        hourly.sort(key=lambda x: x["hour"])

        if len(hourly) < 2:
            return web.json_response({"available": False, "reason": "Onvoldoende prijsdata"})

        all_prices = [h["price"] for h in hourly]
        current = next((h["price"] for h in hourly
                        if h["hour"][:13] == now_hour.isoformat()[:13]), all_prices[0])
        min_price = min(all_prices)
        max_price = max(all_prices)
        price_range = max_price - min_price if max_price > min_price else 0.01

        # Position 0-100 (0=cheapest, 100=most expensive)
        position = round((current - min_price) / price_range * 100)

        # Color: green < 25%, yellow 25-75%, red > 75%, dark green for negative
        if current < 0:
            color = "darkgreen"
            label = "Negatief"
        elif position <= 25:
            color = "green"
            label = "Goedkoop"
        elif position <= 75:
            color = "yellow"
            label = "Gemiddeld"
        else:
            color = "red"
            label = "Duur"

        # Find cheapest upcoming hour
        future = [h for h in hourly if h["hour"] > now_hour.isoformat()]
        cheapest_future = min(future, key=lambda h: h["price"]) if future else None
        hours_to_cheapest = None
        if cheapest_future:
            ch = datetime.fromisoformat(cheapest_future["hour"])
            hours_to_cheapest = round((ch - now_utc).total_seconds() / 3600, 1)

        # Wait advice: if price will drop ≥15% within next hours
        wait_advice = None
        if future:
            for h in sorted(future, key=lambda x: x["price"]):
                if h["price"] < current * 0.85:
                    wait_h = datetime.fromisoformat(h["hour"])
                    wait_hours = round((wait_h - now_utc).total_seconds() / 3600, 1)
                    saving_pct = round((1 - h["price"] / current) * 100) if current > 0 else 0
                    wait_advice = {
                        "waitHours": wait_hours,
                        "targetHour": h["hour"],
                        "targetPrice": h["price"],
                        "savingPercent": saving_pct,
                    }
                    break

        return web.json_response({
            "available": True,
            "currentPrice": current,
            "position": position,
            "color": color,
            "label": label,
            "minPrice": min_price,
            "maxPrice": max_price,
            "cheapestHour": cheapest_future,
            "hoursToCheapest": hours_to_cheapest,
            "waitAdvice": wait_advice,
            "hours": hourly,
        })

    async def schedule_appliance(req: web.Request) -> web.Response:
        """POST /commands/schedule-appliance  body: { "appliance": "wasmachine", "deadline": "18:00" }"""
        body = await req.json()
        appliance_name = str(body.get("appliance", "")).lower().replace(" ", "_")
        deadline_str = body.get("deadline")  # optional "HH:MM" or ISO

        profiles = {
            "wasmachine":  {"watts": 2000, "hours": 2.5, "label": "Wasmachine"},
            "droger":      {"watts": 3000, "hours": 2.0, "label": "Droger"},
            "vaatwasser":  {"watts": 1800, "hours": 2.5, "label": "Vaatwasser"},
            "oven":        {"watts": 2500, "hours": 1.5, "label": "Oven"},
            "ev_laden":    {"watts": 7400, "hours": 4.0, "label": "EV laden"},
            "warmtepomp":  {"watts": 1500, "hours": 3.0, "label": "Warmtepomp"},
            "airco":       {"watts": 1200, "hours": 2.0, "label": "Airco"},
            "boiler":      {"watts": 2000, "hours": 1.0, "label": "Boiler"},
        }

        if appliance_name not in profiles:
            return web.json_response({
                "ok": False,
                "error": f"Onbekend apparaat. Keuze: {', '.join(profiles.keys())}"
            }, status=400)

        profile = profiles[appliance_name]
        kwh = profile["watts"] * profile["hours"] / 1000

        # Find cheapest window in available prices
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        now_hour = now_utc.replace(minute=0, second=0, microsecond=0)

        hourly = []
        for key, val in _latest_prices.items():
            try:
                h = datetime.fromisoformat(str(key).replace("Z", "+00:00"))
                p = float(val) if not isinstance(val, dict) else float(val.get("price", val.get("priceEurKwh", 0)))
            except (ValueError, TypeError, AttributeError):
                continue
            if h >= now_hour:
                hourly.append({"hour": h, "price": p})
        hourly.sort(key=lambda x: x["hour"])

        if not hourly:
            return web.json_response({"ok": False, "error": "Geen prijsdata"}, status=400)

        # Apply deadline filter
        if deadline_str:
            try:
                if len(deadline_str) <= 5:  # "HH:MM"
                    dh, dm = map(int, deadline_str.split(":"))
                    deadline = now_utc.replace(hour=dh, minute=dm, second=0, microsecond=0)
                    if deadline <= now_utc:
                        deadline += timedelta(days=1)
                else:
                    deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                hourly = [h for h in hourly if h["hour"] + timedelta(hours=profile["hours"]) <= deadline]
            except (ValueError, TypeError):
                pass

        dur_slots = max(1, round(profile["hours"]))
        if len(hourly) < dur_slots:
            return web.json_response({"ok": False, "error": "Niet genoeg uren beschikbaar"}, status=400)

        # Sliding window: find cheapest contiguous block
        best_cost = float("inf")
        best_idx = 0
        worst_cost = 0
        for i in range(len(hourly) - dur_slots + 1):
            window_cost = sum(h["price"] for h in hourly[i:i + dur_slots]) * kwh / dur_slots
            if window_cost < best_cost:
                best_cost = window_cost
                best_idx = i
            if window_cost > worst_cost:
                worst_cost = window_cost

        best_window = hourly[best_idx:best_idx + dur_slots]
        now_cost = sum(h["price"] for h in hourly[:dur_slots]) * kwh / dur_slots if len(hourly) >= dur_slots else best_cost
        avg_price = sum(h["price"] for h in best_window) / len(best_window)

        start_local = best_window[0]["hour"].astimezone().strftime("%H:%M")
        end_local = (best_window[-1]["hour"] + timedelta(hours=1)).astimezone().strftime("%H:%M")

        return web.json_response({
            "ok": True,
            "appliance": profile["label"],
            "kwh": round(kwh, 1),
            "watts": profile["watts"],
            "durationHours": profile["hours"],
            "bestStart": best_window[0]["hour"].isoformat(),
            "bestStartLocal": start_local,
            "bestEndLocal": end_local,
            "bestCostEur": round(best_cost, 2),
            "nowCostEur": round(now_cost, 2),
            "worstCostEur": round(worst_cost, 2),
            "savingsEur": round(worst_cost - best_cost, 2),
            "savingsVsNowEur": round(now_cost - best_cost, 2),
            "avgPriceEurKwh": round(avg_price, 4),
            "advice": f"Start {profile['label']} om {start_local} (€{best_cost:.2f}, "
                      f"besparing €{worst_cost - best_cost:.2f} vs duurste moment)",
        })

    async def set_reserve(req: web.Request) -> web.Response:
        """POST /commands/reserve  body: { "target": "today|tomorrow", "time": "18:00", "socPercent": 90 }"""
        body = await req.json()
        target_day = str(body.get("target", "today"))
        time_str = str(body.get("time", "18:00"))
        soc_pct = int(body.get("socPercent", 90))

        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        try:
            hh, mm = map(int, time_str.split(":"))
        except (ValueError, TypeError):
            return web.json_response({"ok": False, "error": "time moet HH:MM zijn"}, status=400)

        deadline = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target_day == "tomorrow":
            deadline += timedelta(days=1)
        elif deadline <= now:
            deadline += timedelta(days=1)

        # Push as EmsEvent to Saldox API
        import aiohttp
        api_url = os.environ.get("SALDOX_API_URL", "").rstrip("/")
        api_token = os.environ.get("SALDOX_API_TOKEN", "")
        if not api_url or not api_token:
            return web.json_response({"ok": False, "error": "SALDOX_API_URL/TOKEN niet geconfigureerd"}, status=500)

        event_body = {
            "kind": "CarFullCharge",  # reuse existing event type for SoC target
            "startUtc": now.isoformat(),
            "endUtc": deadline.isoformat(),
            "additionalKwh": soc_pct / 100.0 * 30.0,  # approximate kWh for target SoC
            "notes": f"Reserve: batterij {soc_pct}% voor {time_str} ({target_day})",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_url}/api/ems/events",
                    json=event_body,
                    headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status in (200, 201):
                        result = await resp.json()
                        # Force plan refresh
                        if _plan_poller is not None:
                            asyncio.ensure_future(_plan_poller.tick())
                        return web.json_response({
                            "ok": True,
                            "deadline": deadline.isoformat(),
                            "socPercent": soc_pct,
                            "eventId": result.get("id"),
                        })
                    else:
                        text = await resp.text()
                        return web.json_response({"ok": False, "error": f"API {resp.status}: {text}"}, status=500)
        except Exception as ex:
            return web.json_response({"ok": False, "error": str(ex)}, status=500)

    # Airco control state: remembers original setpoints for restore.
    _airco_state: dict[str, Any] = {}  # {entity_id: {"original_temp": float, "mode": str, "modified_at": str}}

    async def airco_precondition(req: web.Request) -> web.Response:
        """POST /commands/airco-precondition  body: { "entity_id": "climate.daikin", "economy_temp": 18, "action": "start|restore" }"""
        body = await req.json()
        entity_id = str(body.get("entity_id", ""))
        action = str(body.get("action", "start"))
        economy_temp = float(body.get("economy_temp", 18))

        if not entity_id.startswith("climate."):
            return web.json_response({"ok": False, "error": "entity_id must be a climate.* entity"}, status=400)

        if action == "start":
            # Read current state to remember original setpoint
            try:
                states = await ha.get_states([entity_id])
                state_obj = states.get(entity_id, {})
                attrs = state_obj.get("attributes", {})
                original_temp = attrs.get("temperature", 21)
                current_temp = attrs.get("current_temperature")
                hvac_mode = state_obj.get("state", "off")

                # Guard: skip boost if already cool enough (< normal setpoint)
                normal_setpoint = 18.0  # default comfort temp
                if current_temp is not None and float(current_temp) < normal_setpoint:
                    _LOG.info("AIRCO: skip boost %s — already %.1f°C < %.1f°C",
                              entity_id, float(current_temp), normal_setpoint)
                    return web.json_response({
                        "ok": True,
                        "action": "skipped",
                        "entity": entity_id,
                        "reason": f"Al {current_temp}°C — onder {normal_setpoint}°C, boost niet nodig",
                        "currentTemp": current_temp,
                    })

                # Remember original values
                _airco_state[entity_id] = {
                    "original_temp": original_temp,
                    "original_mode": hvac_mode,
                    "modified_at": datetime.now(timezone.utc).isoformat(),
                    "economy_temp": economy_temp,
                }

                # Set boost temperature (16°C = aggressive pre-cool)
                await ha.call_service("climate", "set_temperature", {
                    "entity_id": entity_id,
                    "temperature": economy_temp,
                })
                _LOG.info("AIRCO: boost %s → %.1f°C (was %.1f°C, current %.1f°C)",
                          entity_id, economy_temp, original_temp, float(current_temp or 0))

                return web.json_response({
                    "ok": True,
                    "action": "start",
                    "entity": entity_id,
                    "originalTemp": original_temp,
                    "economyTemp": economy_temp,
                    "originalMode": hvac_mode,
                })
            except Exception as ex:
                return web.json_response({"ok": False, "error": str(ex)}, status=500)

        elif action == "restore":
            saved = _airco_state.get(entity_id)
            if not saved:
                return web.json_response({"ok": False, "error": f"Geen opgeslagen staat voor {entity_id}"}, status=400)

            try:
                await ha.call_service("climate", "set_temperature", {
                    "entity_id": entity_id,
                    "temperature": saved["original_temp"],
                })
                _LOG.info("AIRCO: restore %s → %.1f°C (was economy %.1f°C)",
                          entity_id, saved["original_temp"], saved["economy_temp"])

                result = {
                    "ok": True,
                    "action": "restore",
                    "entity": entity_id,
                    "restoredTemp": saved["original_temp"],
                    "wasEconomyTemp": saved["economy_temp"],
                    "economyDuration": saved["modified_at"],
                }
                del _airco_state[entity_id]
                return web.json_response(result)
            except Exception as ex:
                return web.json_response({"ok": False, "error": str(ex)}, status=500)

        elif action == "status":
            return web.json_response({
                "ok": True,
                "activePreconditioning": {k: v for k, v in _airco_state.items()},
            })

        return web.json_response({"ok": False, "error": "action must be start|restore|status"}, status=400)

    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/", ingress_page)
    app.router.add_get("/healthz", health)
    app.router.add_get("/status", status)
    app.router.add_get("/simulate", simulate)
    app.router.add_get("/price-index", price_index)
    app.router.add_post("/commands/active-power-limit", set_power_limit)
    app.router.add_post("/commands/battery-mode", set_battery_mode)
    app.router.add_post("/commands/battery-charge-power", set_battery_charge_power)
    app.router.add_post("/commands/battery-discharge-power", set_battery_discharge_power)
    app.router.add_post("/commands/override", set_override)
    app.router.add_post("/commands/schedule-appliance", schedule_appliance)
    app.router.add_post("/commands/reserve", set_reserve)
    async def mode_sync_status(_req: web.Request) -> web.Response:
        """GET /mode-sync — compare Saldox planned mode vs actual HA inverter mode."""
        ha_mode = {}
        if _ha_controller is not None and hasattr(_ha_controller, 'get_current_mode'):
            try:
                ha_mode = await _ha_controller.get_current_mode()
            except Exception as ex:
                ha_mode = {"error": str(ex)}

        # Determine what mode Saldox wants based on current plan
        planned_mode = "auto"
        planned_action = None
        if _executor is not None and _latest_plan:
            active = _executor._find_active_action(_latest_plan)
            if active:
                planned_action = active.get("kind", "")
                planned_mode = {
                    "ChargeBattery": "charge",
                    "DischargeBattery": "discharge_selfuse",
                    "ExportToGrid": "discharge",
                    "SolarCharge": "solar_charge",
                    "CurtailPv": "auto",
                }.get(planned_action, "auto")

        override_mode = _manual_override.get("mode", "auto")

        # Check for conflict
        ha_storage = ha_mode.get("storageMode", "unknown")
        saldox_wants = override_mode if override_mode != "auto" else planned_mode
        conflict = False
        if ha_storage == "Self Use" and saldox_wants in ("charge", "discharge", "discharge_selfuse", "solar_charge"):
            conflict = True
        elif ha_storage == "Passive Mode" and saldox_wants == "auto":
            conflict = True

        return web.json_response({
            "ok": True,
            "haMode": ha_mode,
            "saldoxPlannedMode": planned_mode,
            "saldoxPlannedAction": planned_action,
            "overrideMode": override_mode,
            "effectiveMode": saldox_wants,
            "conflict": conflict,
            "leading": "saldox",  # configurable later
        })

    async def backfill_history(req: web.Request) -> web.Response:
        """POST /commands/backfill  body: { "days": 30 }
        Fetches historical data from HA and pushes to Saldox API bulk-import."""
        body = await req.json()
        backfill_days = int(body.get("days", 30))
        backfill_days = min(backfill_days, 365)

        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        start = (now_utc - timedelta(days=backfill_days)).strftime("%Y-%m-%dT00:00:00+00:00")
        end = now_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        # Entities to backfill with their metric names for the bulk-import API.
        entities = {
            "sensor.sofar_inverter_sofar_active_power_load_sys": ("consumption", 1000),  # kW→W
            "sensor.sofar_inverter_sofar_battery_capacity_total": ("soc", 1),             # % direct
            "sensor.sofar_inverter_sofar_pv_power_total": ("pv", 1000),                   # kW→W
            "sensor.sofar_inverter_sofar_active_power_pcc_total": ("grid", 1000),         # kW→W (signed)
            "sensor.sofar_inverter_sofar_battery_power_total": ("battery", 1000),          # kW→W
        }

        # Try to get outdoor temp from weather entity.
        weather_entity = "weather.forecast_thuis"  # typical HA weather entity
        weather_state = await ha.get_state(weather_entity)
        if weather_state and weather_state.get("attributes", {}).get("temperature") is not None:
            entities[weather_entity] = ("temperature_weather", 1)

        all_readings: list[dict] = []
        entity_counts: dict[str, int] = {}

        for entity_id, (metric, scale) in entities.items():
            _LOG.info("Backfill: fetching %s (%d days)...", entity_id, backfill_days)
            try:
                history = await ha.get_history(entity_id, start, end)
            except Exception as ex:
                _LOG.warning("Backfill: failed to fetch %s: %s", entity_id, ex)
                continue

            count = 0
            for entry in history:
                state_val = entry.get("state", "")
                if state_val in ("unknown", "unavailable", ""):
                    continue
                try:
                    val = float(state_val) * scale
                except (ValueError, TypeError):
                    continue

                ts = entry.get("last_changed", entry.get("last_updated", ""))
                if not ts:
                    continue

                # For grid power: split into import/export by sign.
                if metric == "grid":
                    if val >= 0:
                        all_readings.append({"timestampUtc": ts, "metric": "grid_import", "value": abs(val)})
                    else:
                        all_readings.append({"timestampUtc": ts, "metric": "grid_export", "value": abs(val)})
                elif metric == "temperature_weather":
                    # Weather entity: temperature is in attributes, state is condition text.
                    temp = entry.get("attributes", {}).get("temperature")
                    if temp is not None:
                        all_readings.append({"timestampUtc": ts, "metric": "temperature", "value": float(temp)})
                else:
                    all_readings.append({"timestampUtc": ts, "metric": metric, "value": val})
                count += 1

            entity_counts[entity_id] = count
            _LOG.info("Backfill: %s → %d readings", entity_id, count)

        if not all_readings:
            return web.json_response({"ok": False, "error": "Geen historische data gevonden in HA", "entities": entity_counts})

        # Push to Saldox API in chunks.
        api_url = os.environ.get("SALDOX_API_URL", "").rstrip("/")
        api_token = os.environ.get("SALDOX_API_TOKEN", "")
        if not api_url or not api_token:
            return web.json_response({"ok": False, "error": "SALDOX_API_URL/TOKEN niet geconfigureerd"}, status=500)

        chunk_size = 2000
        total_stored = 0
        total_skipped = 0
        errors = []

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(all_readings), chunk_size):
                chunk = all_readings[i:i + chunk_size]
                try:
                    async with session.post(
                        f"{api_url}/api/ha/bulk-import",
                        json={"readings": chunk},
                        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            total_stored += result.get("stored", 0)
                            total_skipped += result.get("skipped", 0)
                        else:
                            text = await resp.text()
                            errors.append(f"Chunk {i//chunk_size}: HTTP {resp.status} — {text[:200]}")
                except Exception as ex:
                    errors.append(f"Chunk {i//chunk_size}: {ex}")

        _LOG.info("Backfill complete: %d stored, %d skipped, %d errors", total_stored, total_skipped, len(errors))
        return web.json_response({
            "ok": True,
            "days": backfill_days,
            "totalReadings": len(all_readings),
            "stored": total_stored,
            "skipped": total_skipped,
            "entities": entity_counts,
            "errors": errors[:5] if errors else [],
        })

    app.router.add_post("/commands/backfill", backfill_history)
    app.router.add_post("/commands/airco-precondition", airco_precondition)
    app.router.add_get("/mode-sync", mode_sync_status)
    return app


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

    conn_type = os.environ.get("MODBUS_CONNECTION_TYPE", "tcp")
    interval = int(os.environ.get("POLL_INTERVAL", "10"))

    slug = os.environ.get("HA_DEVICE_SLUG", "sofar_hyd")
    friendly = os.environ.get("HA_FRIENDLY_NAME", "Sofar HYD")

    modbus = SofarModbusClient(
        connection_type=conn_type,
        host=os.environ.get("MODBUS_HOST", "192.168.1.50"),
        port=int(os.environ.get("MODBUS_PORT", "502")),
        serial_port=os.environ.get("MODBUS_SERIAL_PORT", "/dev/ttyUSB0"),
        baudrate=int(os.environ.get("MODBUS_BAUDRATE", "9600")),
        parity=os.environ.get("MODBUS_PARITY", "N"),
        stopbits=int(os.environ.get("MODBUS_STOPBITS", "1")),
        unit_id=int(os.environ.get("MODBUS_UNIT_ID", "1")),
    )
    ha = HomeAssistantClient()
    ha_reader = HaSensorReader(ha)
    modbus_controller = ModbusBatteryController(modbus)

    global _executor, _ha_controller
    _ha_controller = modbus_controller
    _executor = ActionExecutor(controller=modbus_controller)
    _LOG.info("Action executor actief — battery control via direct Modbus RS485 (FC16)")

    poll_task = asyncio.create_task(poll_loop(modbus, ha, ha_reader, slug, friendly, interval), name="poll")

    prices_task = None
    plan_task = None
    saldox_api_url = os.environ.get("SALDOX_API_URL", "").strip()
    saldox_api_token = os.environ.get("SALDOX_API_TOKEN", "").strip()
    # DEV fallback: if env var not set, use hardcoded dev server URL.
    if not saldox_api_url:
        saldox_api_url = "http://127.0.0.1:5244"
        _LOG.warning("SALDOX_API_URL not set — using dev fallback: %s", saldox_api_url)
    if not saldox_api_token:
        saldox_api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Y2I3ZTczOC1jZmU3LTQ2NGMtYTAzMS1hODBiNmRiYTQxNzMiLCJlbWFpbCI6ImhoLmltbWluZ0BnbWFpbC5jb20iLCJqdGkiOiJjQ1gxd2VxZzYxRlJNVW1rOVQyeXRKIiwidHlwZSI6ImhhX2FwaV9rZXkiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJDdXN0b21lciIsImV4cCI6MTgxNTM2ODY3OCwiaXNzIjoiRW5lcmd5QWR2aXNvciIsImF1ZCI6IkVuZXJneUFkdmlzb3IifQ.WnxuLRbclxKaT7uNWtpAteWApQcUubuJpYQvCqNmr7k"
        _LOG.warning("SALDOX_API_TOKEN not set — using dev fallback")
    if saldox_api_url:
        prices = PricesPoller(
            ha=ha,
            saldox_api_url=saldox_api_url,
            saldox_api_token=saldox_api_token,
            slug=os.environ.get("PRICES_SLUG", "saldox_price"),
            friendly=os.environ.get("PRICES_FRIENDLY_NAME", "Saldox prijs"),
            poll_minutes=int(os.environ.get("PRICES_POLL_MINUTES", "15")),
            on_update=set_prices,
        )
        prices_task = asyncio.create_task(prices.run(), name="prices")
        _LOG.info("Saldox prices poller actief (API: %s)", saldox_api_url)

        plan = PlanPoller(
            ha=ha,
            saldox_api_url=saldox_api_url,
            saldox_api_token=saldox_api_token,
            slug=os.environ.get("PLAN_SLUG", "saldox_plan"),
            friendly=os.environ.get("PLAN_FRIENDLY_NAME", "Saldox plan"),
            poll_minutes=int(os.environ.get("PLAN_POLL_MINUTES", "5")),
            on_update=set_plan,
            get_readings=lambda: dict(_latest),
        )
        plan.set_hourly_usage_source(get_completed_hourly_usage)
        global _plan_poller, _arbitrage_optimizer
        _plan_poller = plan
        _arbitrage_optimizer = ArbitrageOptimizer(ArbitrageConfig())
        _LOG.info("Arbitrage optimizer geactiveerd (30 kWh, 15 kW, 90%% eff)")
        plan_task = asyncio.create_task(plan.run(), name="plan")
        _LOG.info("Saldox plan poller actief")

    web_app = make_webhook_app(modbus, ha)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8765)
    await site.start()
    _LOG.info("Webhook server luistert op :8765")

    # Wacht op SIGTERM (Supervisor stop) of poll-failure.
    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    await stop.wait()

    _LOG.info("Stopping…")
    poll_task.cancel()
    if prices_task:
        prices_task.cancel()
    if plan_task:
        plan_task.cancel()
    with suppress(asyncio.CancelledError):
        await poll_task
    if prices_task:
        with suppress(asyncio.CancelledError):
            await prices_task
    if plan_task:
        with suppress(asyncio.CancelledError):
            await plan_task
    await runner.cleanup()
    await modbus.close()
    await ha.close()


if __name__ == "__main__":
    asyncio.run(main())
