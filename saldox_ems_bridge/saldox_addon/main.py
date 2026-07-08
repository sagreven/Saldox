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

import aiohttp
from aiohttp import web

from .ha_api import HomeAssistantClient
from .modbus_client import SofarModbusClient
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
    "inverter_temperature_c": ("temperature",    "temperature",     "measurement"),
    "inverter_status":        ("status",         None,              None),
    "battery_voltage_v":      ("battery_voltage","voltage",         "measurement"),
}


# Shared state: latest poll results, updated by poll_loop, read by /status endpoint.
_latest: dict[str, dict] = {}
_latest_ts: float = 0.0

# Shared state: latest price data, updated by PricesPoller via set_prices().
_latest_prices: dict[str, dict] = {}


def set_prices(snapshot: dict[str, dict]) -> None:
    """Called by PricesPoller.tick() to share latest prices with /status."""
    _latest_prices.clear()
    _latest_prices.update(snapshot)


async def poll_loop(client: SofarModbusClient, ha: HomeAssistantClient, slug: str, friendly: str, interval: int) -> None:
    global _latest_ts
    while True:
        try:
            readings = await client.read_all()
            snapshot: dict[str, dict] = {}
            for r in readings:
                snapshot[r.name] = {"value": r.value, "unit": r.unit}
            _latest.clear()
            _latest.update(snapshot)
            _latest_ts = time.time()
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
            _LOG.info("Poll OK — %d readings naar HA", len(readings))
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
        return web.json_response({
            "ok": True,
            "timestamp": _latest_ts,
            "readings": _latest,
            "prices": _latest_prices,
        })

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
        body = await req.json()
        mode = str(body.get("mode", ""))
        if mode not in BATTERY_MODE_MAP:
            return web.json_response({"ok": False, "error": f"mode must be one of {list(BATTERY_MODE_MAP)}"}, status=400)
        try:
            await client.write_holding(by_name("battery_mode"), BATTERY_MODE_MAP[mode])
            return web.json_response({"ok": True, "mode": mode})
        except Exception as ex:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(ex)}, status=500)

    async def set_battery_charge_power(req: web.Request) -> web.Response:
        body = await req.json()
        watts = int(body.get("watts", -1))
        if watts < 0:
            return web.json_response({"ok": False, "error": "watts moet >= 0 zijn"}, status=400)
        try:
            # Schaal × 100 omdat het register 0.01 kW = 10 W resolutie heeft.
            raw = watts // 100
            await client.write_holding(by_name("battery_charge_power_w"), raw)
            return web.json_response({"ok": True, "watts": watts})
        except Exception as ex:  # noqa: BLE001
            return web.json_response({"ok": False, "error": str(ex)}, status=500)

    async def set_battery_discharge_power(req: web.Request) -> web.Response:
        body = await req.json()
        watts = int(body.get("watts", -1))
        if watts < 0:
            return web.json_response({"ok": False, "error": "watts moet >= 0 zijn"}, status=400)
        try:
            raw = watts // 100
            await client.write_holding(by_name("battery_discharge_power_w"), raw)
            return web.json_response({"ok": True, "watts": watts})
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

    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/healthz", health)
    app.router.add_get("/status", status)
    app.router.add_post("/commands/active-power-limit", set_power_limit)
    app.router.add_post("/commands/battery-mode", set_battery_mode)
    app.router.add_post("/commands/battery-charge-power", set_battery_charge_power)
    app.router.add_post("/commands/battery-discharge-power", set_battery_discharge_power)
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

    poll_task = asyncio.create_task(poll_loop(modbus, ha, slug, friendly, interval), name="poll")

    prices_task = None
    if os.environ.get("PRICES_ENABLED", "true").lower() in ("1", "true", "yes"):
        prices = PricesPoller(
            ha=ha,
            slug=os.environ.get("PRICES_SLUG", "saldox_price"),
            friendly=os.environ.get("PRICES_FRIENDLY_NAME", "Saldox prijs"),
            vat_inclusive=os.environ.get("PRICES_VAT_INCLUSIVE", "true").lower() in ("1", "true", "yes"),
            poll_minutes=int(os.environ.get("PRICES_POLL_MINUTES", "15")),
            on_update=set_prices,
        )
        prices_task = asyncio.create_task(prices.run(), name="prices")
        _LOG.info("EPEX prices poller actief")

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
    with suppress(asyncio.CancelledError):
        await poll_task
    if prices_task:
        with suppress(asyncio.CancelledError):
            await prices_task
    await runner.cleanup()
    await modbus.close()
    await ha.close()


if __name__ == "__main__":
    asyncio.run(main())
