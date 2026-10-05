"""Simulatie per uur: direct verbruik van zonnestroom met en zonder batterij, incl. weekenden.

Invoer: zonne-opwek NL 2025 van energy-charts (https://api.energy-charts.info/public_power?country=nl&start=2025-01-01&end=2025-12-31),
opgeslagen als power_2025.json. Gebruik: python3 weekend.py [power_2025.json]
"""
import json, datetime as dt, math
from collections import defaultdict
from zoneinfo import ZoneInfo
tz=ZoneInfo("Europe/Amsterdam")
w=json.load(open(__import__('sys').argv[1] if len(__import__('sys').argv) > 1 else 'power_2025.json'))
sol=[pt for pt in w['production_types'] if pt['name']=='Solar'][0]['data']
sh=defaultdict(float)
for t,v in zip(w['unix_seconds'],sol):
    if v: sh[t//3600]+=v/4
hours=sorted(sh)
k=16500/sum(sh.values())
pv={h:sh[h]*k for h in hours}
def sim(base_kw, office_scale=1.0, batt=45, pmax=15, eff=0.9, weekend_extra=0.0):
    soc=0; direct=0; via_batt=0; load_tot=0; wk_pv=0; wk_load=0; exp=0
    for h in hours:
        d=dt.datetime.fromtimestamp(h*3600,tz)
        doy=d.timetuple().tm_yday
        season=(1+math.cos(2*math.pi*(doy-15)/365))/2   # 1 = winter, 0 = zomer
        workday=d.weekday()<5
        if workday and 8<=d.hour<18:
            load=(130+40*season)/10*office_scale
        else:
            load=base_kw
            if not workday: load+=weekend_extra
        load_tot+=load
        p=pv[h]
        if not workday: wk_pv+=p; wk_load+=load
        use=min(p,load); direct+=use
        surplus=p-use; deficit=load-use
        ch=min(surplus,pmax,(batt-soc)/eff); soc+=ch*eff; exp+=surplus-ch
        dis=min(deficit,pmax,soc); soc-=dis; via_batt+=dis
    tot=sum(pv.values())
    return dict(load=load_tot, direct=direct/tot, met_batt=(direct+via_batt)/tot, export=exp, wk_pv=wk_pv, wk_load=wk_load)
for b in (0.5,1.0,1.5,2.0):
    r=sim(b); print(f"basislast {b} kW: verbruik {r['load']:.0f} kWh, direct {r['direct']:.0%}, met batterij {r['met_batt']:.0%}, teruglevering {r['export']:.0f} kWh, weekend: opwek {r['wk_pv']:.0f} kWh, verbruik {r['wk_load']:.0f} kWh")
# kantoorverbruik zo schalen dat totaal 36.000 kWh
for b in (0.5,1.0):
    lo,hi=0.3,1.2
    for _ in range(40):
        m=(lo+hi)/2; (lo,hi)=(m,hi) if sim(b,m)['load']<36000 else (lo,m)
    r=sim(b,m); print(f"36.000 kWh totaal, basislast {b} kW: kantoorschaal {m:.2f}, direct {r['direct']:.0%}, met batterij {r['met_batt']:.0%}, teruglevering {r['export']:.0f} kWh")
