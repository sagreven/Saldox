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
from .ha_api import HomeAssistantClient
from .ha_sensor_reader import HaBatteryController, HaSensorReader
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
    "inverter_temperature_c": ("temperature",    "temperature",     "measurement"),
    "inverter_status":        ("status",         None,              None),
    "battery_voltage_v":      ("battery_voltage","voltage",         "measurement"),
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


def set_prices(snapshot: dict[str, dict]) -> None:
    """Called by PricesPoller.tick() to share latest prices with /status."""
    _latest_prices.clear()
    _latest_prices.update(snapshot)


def set_plan(plan: dict[str, Any]) -> None:
    """Called by PlanPoller.tick() to share latest EMS plan with /status.
    Also triggers the action executor to check for active actions.
    """
    global _executor_status
    _latest_plan.clear()
    _latest_plan.update(plan)
    if _executor is not None:
        import asyncio
        asyncio.ensure_future(_run_executor(plan))


async def _run_executor(plan: dict[str, Any]) -> None:
    """Run the action executor and update the shared status string."""
    global _executor_status
    if _executor is None:
        return
    try:
        result = await _executor.execute(plan)
        if result:
            _executor_status = result
    except Exception as ex:  # noqa: BLE001
        _LOG.error("Action executor failed: %s", ex)
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
            # Try direct Modbus first; if it fails, fall back to HA sensors.
            readings = None
            source = "modbus"
            if _modbus_ok:
                try:
                    readings = await client.read_all()
                except Exception:
                    _modbus_ok = False
                    _LOG.info("Modbus niet beschikbaar — schakel over naar HA sensor bridge")

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

            # Only push to HA as separate sensors when reading from direct Modbus
            # (HA sensors already exist from the Solax integration).
            if source == "modbus":
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
        return web.json_response({
            "ok": True,
            "timestamp": _latest_ts,
            "readings": _latest,
            "prices": _latest_prices,
            "plan": _latest_plan,
            "executor": _executor_status,
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
</style>
</head><body>
<h1>Saldox EMS Bridge</h1>
<p class="subtitle"><span class="status-dot" id="dot"></span><span id="conn">Verbinden...</span></p>
<div id="error"></div>
<div class="pf-wrap" id="powerflow"></div>
<div class="grid" id="grid"></div>
<div id="plan-section"></div>
<p style="color:#aaa;font-size:.75rem;margin-top:16px">Auto-refresh elke 10 seconden</p>
<script>
const grid=document.getElementById('grid'),dot=document.getElementById('dot'),
      conn=document.getElementById('conn'),errEl=document.getElementById('error'),
      planSection=document.getElementById('plan-section'),
      pfEl=document.getElementById('powerflow');

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
  const batCapKwh=plan&&plan.batterySoC&&plan.batterySoC.length?plan.batterySoC[0].capacityKwh:10;
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
const actionLabels={ChargeBattery:'Batterij laden',DischargeBattery:'Batterij ontladen',
  ChargeCar:'Auto laden',CurtailPv:'PV beperken',RunHeavyLoad:'Zwaar verbruik'};
const actionColors={ChargeBattery:'#22c55e',DischargeBattery:'#f97316',ChargeCar:'#3b82f6',
  CurtailPv:'#a855f7',RunHeavyLoad:'#6b7280'};

function toLocal(utcStr){
  if(!utcStr)return null;
  return new Date(utcStr.endsWith('Z')?utcStr:utcStr+'Z');
}
function fmtHour(d){return d?d.getHours()+':00':'?';}
function fmtTime(d){return d?d.toLocaleTimeString('nl-NL',{hour:'2-digit',minute:'2-digit'}):'?';}

function renderPlan(plan){
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
      const tp=p.prices_today&&p.prices_today.value||[];
      const tm=p.prices_tomorrow&&p.prices_tomorrow.value||[];
      const nowH=new Date().getHours();
      const next24=[...tp.filter(h=>h.hour>=nowH),...tm.filter(h=>h.hour<nowH)].slice(0,24);
      if(next24.length){
        const prices=next24.map(h=>h.price);
        const minP=Math.min(...prices);
        const maxP=Math.max(...prices);
        const range=maxP-minP||0.01;
        html+='<div class="card" style="grid-column:1/-1"><div class="label">Komende 24 uur</div><div style="display:flex;align-items:flex-end;gap:1px;height:200px;margin-top:12px;padding-bottom:20px;position:relative">';
        for(let i=0;i<next24.length;i++){
          const h=next24[i];
          const pct=((h.price-minP)/range)*80+15;
          const neg=h.price<0;
          const isNow=i===0;
          const col=neg?'#ef4444':isNow?'#1a7a2e':'#60a5fa';
          html+=`<div style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%"><div style="background:${col};width:90%;height:${pct}%;border-radius:3px 3px 0 0;min-height:4px;position:relative" title="${h.hour}:00 — € ${h.price.toFixed(4)}"><span style="position:absolute;top:-14px;left:50%;transform:translateX(-50%);font-size:.5rem;color:#555;white-space:nowrap">${h.price.toFixed(2)}</span></div><div style="font-size:.55rem;color:#999;margin-top:3px">${h.hour}</div></div>`;
        }
        html+='</div></div>';
      }
    }
    grid.innerHTML=html||'<div class="card off"><div class="label">Wachten op data</div><div class="value">—</div></div>';
    // Render EMS plan section
    renderPlan(d.plan||null);
  }catch(e){
    dot.className='status-dot red';
    conn.textContent='Geen verbinding';
    errEl.textContent=e.message;errEl.style.display='block';
  }
}
poll();setInterval(poll,10000);
</script>
</body></html>"""
        return web.Response(text=html, content_type="text/html")

    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/", ingress_page)
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
    ha_reader = HaSensorReader(ha)
    ha_controller = HaBatteryController(ha)

    global _executor
    _executor = ActionExecutor(controller=ha_controller)
    _LOG.info("Action executor actief — battery control via HA Solax integration")

    poll_task = asyncio.create_task(poll_loop(modbus, ha, ha_reader, slug, friendly, interval), name="poll")

    prices_task = None
    plan_task = None
    saldox_api_url = os.environ.get("SALDOX_API_URL", "").strip()
    saldox_api_token = os.environ.get("SALDOX_API_TOKEN", "").strip()
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
