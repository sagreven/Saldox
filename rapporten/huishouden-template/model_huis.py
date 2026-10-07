#!/usr/bin/env python3
"""Rekenmodel voor de huishouden-template: simulatie per uur over een heel jaar.

Invoer: echte uurprijzen (EPEX day-ahead NL 2025) en het Nederlandse zonneprofiel
2025 (Energy-Charts, data/nl_2025_uur.json). Daarop: een standaard huishoudprofiel,
zonnepanelen, een thuisbatterij en eventueel een elektrische auto die thuis laadt.

Alle bedragen voor de klant zijn incl. btw (consument). Zie AANNAMES hieronder;
een template-variant past alleen deze waarden aan (zie varianten.py).
"""
import datetime as dt
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
TZ = ZoneInfo("Europe/Amsterdam")
BTW = 1.21

AANNAMES = dict(
    verbruik_kwh=2500,          # Milieu Centraal: gemiddeld 2.430 kWh; 2 personen ca. 2.550
    panelen=10, wp=450,
    opbrengst_kwh_per_kwp=917,  # PVGIS Veldhoven: 861 (oost-west) tot 1.032 (zuid)
    batt_kwh=10.24, batt_bruikbaar=0.90, batt_kw=5.0, rendement=0.90,  # 2x BTS 5K: 9,2 kWh bruikbaar, 2x 2,5 kW
    ev_kwh=0,                   # thuis geladen per jaar (0 = geen EV)
    ev_kw=11.0,                 # Zaptec Go 2 kan 22 kW; 11 kW is gangbaar thuis
    eb_incl=0.1108,             # energiebelasting stroom 2026 incl. btw per kWh
    opslag_excl=0.0165,         # dynamisch: inkoopvergoeding ca. €0,018–0,020 incl. btw
    terug_fee=0.0,              # dynamisch: veel leveranciers rekenen in 2027 geen terugleverkosten
    terug_btw=False,            # voorzichtig: uurprijs zonder btw
    vast_incl=0.28,             # vast contract: kWh-prijs incl. btw en energiebelasting
    vast_terug=0.05,            # vast: vergoeding ca. €0,10 min terugleverkosten €0,045–0,065
    spot_factor=1.0,            # 1,15 = groothandelsprijs 2027 volgens de termijnmarkt
    publiek_laden=0.50,         # gemiddelde prijs publiek laden incl. btw per kWh
    ere_netto=(0.10, 0.13),     # ERE-uitbetaling per geladen kWh (netto, na commissie)
)


def laad_data():
    d = json.loads((HERE / "data/nl_2025_uur.json").read_text())
    return d["uur_unix"], [p / 1000 for p in d["prijs_eur_mwh"]], d["zon_mw"]


UUR, SPOT, ZON = laad_data()
TIJD = [dt.datetime.fromtimestamp(t, TZ) for t in UUR]
ZON_SOM = sum(ZON)


def huisprofiel():
    """Genormaliseerd verbruik per uur: nacht laag, ochtend- en avondpiek, winter hoger."""
    vorm_werk = [0.45, 0.4, 0.38, 0.38, 0.4, 0.5, 0.9, 1.3, 1.1, 0.8, 0.75, 0.8,
                 0.85, 0.8, 0.75, 0.85, 1.1, 1.6, 2.0, 1.9, 1.7, 1.5, 1.1, 0.7]
    vorm_weekend = [0.5, 0.45, 0.4, 0.4, 0.4, 0.45, 0.6, 0.9, 1.2, 1.3, 1.3, 1.3,
                    1.3, 1.2, 1.1, 1.1, 1.3, 1.7, 1.9, 1.8, 1.6, 1.4, 1.1, 0.75]
    w = []
    for t in TIJD:
        seizoen = 1 + 0.25 * math.cos(2 * math.pi * (t.timetuple().tm_yday - 15) / 365)
        vorm = vorm_werk if t.weekday() < 5 else vorm_weekend
        w.append(vorm[t.hour] * seizoen)
    s = sum(w)
    return [x / s for x in w]


PROFIEL = huisprofiel()


def ev_profiel(kwh_jaar, kw, slim):
    """EV-laden per uur. Slim: goedkoopste uren waarin de auto thuis is (avond/nacht,
    in het weekend ook overdag). Niet slim: direct vanaf 18:00 op vol vermogen."""
    if not kwh_jaar:
        return [0.0] * len(UUR)
    per_dag = kwh_jaar / 365
    load = [0.0] * len(UUR)
    dagen = {}
    for i, t in enumerate(TIJD):
        dagen.setdefault(t.date(), []).append(i)
    for dag, idx in dagen.items():
        weekend = TIJD[idx[0]].weekday() >= 5
        thuis = [i for i in idx if TIJD[i].hour >= 18 or TIJD[i].hour < 7 or (weekend and 9 <= TIJD[i].hour < 17)]
        if slim:
            # zonne-uren in het weekend tellen als goedkoop: daar is eigen stroom
            volgorde = sorted(thuis, key=lambda i: SPOT[i] - (0.10 if weekend and ZON[i] > 0.3 * max(ZON) else 0))
        else:
            volgorde = sorted(thuis, key=lambda i: (TIJD[i].hour < 18, TIJD[i].hour))
        rest = per_dag
        for i in volgorde:
            if rest <= 0:
                break
            q = min(kw, rest)
            load[i] += q
            rest -= q
    return load


def simuleer(a, pv=True, batterij=True, contract="dynamisch", ev_slim=True, stap=0.5):
    """Jaarkosten (incl. btw) en energiestromen. De batterij wordt per uur optimaal
    ingezet met dynamisch programmeren over de laadtoestand: zo stuurt een EMS op
    day-ahead prijzen (die een dag vooruit bekend zijn)."""
    kwp = a["panelen"] * a["wp"] / 1000
    pv_kwh = kwp * a["opbrengst_kwh_per_kwp"] if pv else 0
    ev = ev_profiel(a["ev_kwh"], a["ev_kw"], ev_slim)
    netto_vraag = [a["verbruik_kwh"] * f + ev[i] - pv_kwh * ZON[i] / ZON_SOM for i, f in enumerate(PROFIEL)]
    dyn = contract == "dynamisch"
    if dyn:
        f = a.get("spot_factor", 1.0)
        p_imp = [(sp * f + a["opslag_excl"]) * BTW + a["eb_incl"] for sp in SPOT]
        p_exp = [max(sp * f - a["terug_fee"], 0) * (BTW if a["terug_btw"] else 1) for sp in SPOT]
    else:
        p_imp = [a["vast_incl"]] * len(SPOT)
        p_exp = [a["vast_terug"]] * len(SPOT)

    def kost(i, net):
        return net * p_imp[i] if net > 0 else net * p_exp[i]

    n = len(SPOT)
    cap = a["batt_kwh"] * a["batt_bruikbaar"] if batterij else 0
    if cap:
        eta = math.sqrt(a["rendement"])
        S = int(cap / stap)
        dmax = int(a["batt_kw"] / stap)
        V = [0.0] * (S + 1)
        keuze = []
        for i in range(n - 1, -1, -1):
            Vn, kz = [0.0] * (S + 1), [0] * (S + 1)
            for s_ in range(S + 1):
                best, bk = None, s_
                for s2 in range(max(0, s_ - dmax), min(S, s_ + dmax) + 1):
                    d = (s2 - s_) * stap
                    flow = d / eta if d > 0 else d * eta
                    c = kost(i, netto_vraag[i] + flow) + V[s2]
                    if best is None or c < best:
                        best, bk = c, s2
                Vn[s_], kz[s_] = best, bk
            V = Vn
            keuze.append(kz)
        keuze.reverse()
    s_ = 0
    kosten = opbrengst = imp = exp_ = 0.0
    for i in range(n):
        net = netto_vraag[i]
        if cap:
            s2 = keuze[i][s_]
            d = (s2 - s_) * stap
            net += d / eta if d > 0 else d * eta
            s_ = s2
        if net > 0:
            kosten += net * p_imp[i]; imp += net
        else:
            opbrengst += -net * p_exp[i]; exp_ += -net
    eigen = pv_kwh - min(exp_, pv_kwh)
    return dict(netto=kosten - opbrengst, kosten=kosten, opbrengst=opbrengst, import_kwh=imp,
                export_kwh=exp_, pv_kwh=pv_kwh, eigen_kwh=eigen,
                zelfverbruik=(eigen / pv_kwh if pv_kwh else 0))


def besparingen(a, contract="dynamisch"):
    """Besparing per onderdeel t.o.v. een huishouden zonder installatie (zelfde contract)."""
    zonder_ev = dict(a, ev_kwh=0)
    basis = simuleer(zonder_ev, pv=False, batterij=False, contract=contract)
    met_pv = simuleer(zonder_ev, pv=True, batterij=False, contract=contract)
    met_beide = simuleer(zonder_ev, pv=True, batterij=True, contract=contract)
    r = dict(basis=basis, met_pv=met_pv, met_beide=met_beide,
             zon=basis["netto"] - met_pv["netto"],
             batterij=met_pv["netto"] - met_beide["netto"])
    if a["ev_kwh"]:
        met_ev = simuleer(a, pv=True, batterij=True, contract=contract, ev_slim=True)
        thuis_laden = met_ev["netto"] - met_beide["netto"]       # extra kosten van thuisladen
        publiek = a["ev_kwh"] * a["publiek_laden"]
        r.update(met_ev=met_ev, ev_thuis_kosten=thuis_laden, ev_publiek_kosten=publiek,
                 ev_prijs_thuis=thuis_laden / a["ev_kwh"], laden=publiek - thuis_laden,
                 ere=(a["ev_kwh"] * a["ere_netto"][0], a["ev_kwh"] * a["ere_netto"][1]))
    return r


if __name__ == "__main__":
    a = dict(AANNAMES)
    for naam, ev in (("zonder EV", 0), ("met EV 2.500 kWh", 2500)):
        a["ev_kwh"] = ev
        for c in ("dynamisch", "vast"):
            r = besparingen(a, c)
            print(f"{naam:18} {c:10} zon €{r['zon']:.0f}  batterij €{r['batterij']:.0f}  "
                  f"zelfverbruik zon {r['met_pv']['zelfverbruik']:.0%} → met batterij {r['met_beide']['zelfverbruik']:.0%}  "
                  f"teruglevering {r['met_beide']['export_kwh']:.0f} kWh"
                  + (f"  thuisladen €{r['ev_prijs_thuis']:.3f}/kWh, besparing laden €{r['laden']:.0f}, ERE €{r['ere'][0]:.0f}-{r['ere'][1]:.0f}" if ev else ""))
