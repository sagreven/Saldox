#!/usr/bin/env python3
"""Offertegenerator: van klantprofiel naar het juiste pakket en een offerte in Saldox-huisstijl.

Voorbeeld (bij de klant: "PHEV dagelijks nodig, klein huishouden, plat dak, 10 panelen"):

    python3 offerte.py --klant "Fam. Jansen" --huishouden klein --auto phev --dak plat --panelen 10

Het script rekent alle passende pakketten door (Marstek Venus E 1× of 2×, Sofar 10 kWh;
met Zaptec Go 2 als er een auto is), kiest het pakket met de hoogste nettowinst over
15 jaar en schrijft de offerte naar rapporten/offertes/<datum>-<klant>/.
"""
import argparse
import datetime as dt
import json
import math
import re
import subprocess
from pathlib import Path

import build_huis as B
from opmaak import bouw

HERE = Path(__file__).parent
UIT = HERE.parent / "offertes"

HUISHOUDEN = {"klein": 2000, "gemiddeld": 2500, "groot": 3600}  # kWh/jaar (Milieu Centraal: 1–2, 2–3, 4 personen)
HUISHOUDEN_TEKST = {"klein": "klein huishouden (1 tot 2 personen)", "gemiddeld": "gemiddeld huishouden",
                    "groot": "groot huishouden (4 personen)"}
JAREN_HORIZON = 15
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"]


# ───────────────────────────────────────────── pakketten samenstellen
def zonnedeel(n, dak, micro):
    """Posten voor n panelen A Solar 460 Wp; micro=True: APsystems DS3 (1 per 2 panelen)."""
    p = [(f"{n} zonnepanelen A Solar 460 Wp, glas-glas ({n} × €69,46)", B.bedrag(n, "A Solar zonnepaneel 460 Wp"), 0.0, "Inkoopprijs", "zon")]
    if micro:
        k = math.ceil(n / 2)
        p += [(f"{k} micro-omvormers APsystems DS3, 880 VA ({k} × €110,74)", B.bedrag(k, "MFQ-023-0106911"), 0.0, "Inkoopprijs", "zon"),
              (f"{2 * k} Y3 AC-buskabels en {2 * k} eindkappen (APsystems)",
               round(B.bedrag(2 * k, "MFQ-023-0106912") + B.bedrag(2 * k, "MFQ-023-0106913"), 2), 0.0, "Inkoopprijs", "zon"),
              ("Monitoring APsystems ECU-B", 67.00, 0.0, "Stelpost", "zon")]
    p.append(("Transport", B.TRANSPORT, 0.0, "Tarief", "zon"))
    if dak == "plat":
        p += [("Montage zonnepanelen op plat dak (vast)", B.PLATDAK_MONTAGE, 0.0, "Tarief", "zon"),
              ("Plat-dak-opstelling met ballast en bekabeling", 55.0 * n, 0.0, "Stelpost", "zon")]
    else:
        p += [("Montage zonnepanelen" + (" en micro-omvormers" if micro else ""), 80.0 * n, 0.0, "Stelpost", "zon"),
              ("Dakbevestiging en bekabeling", 45.0 * n, 0.0, "Stelpost", "zon")]
    return p


def micro_installatie(n):
    """Installatieteksten voor n panelen A Solar met APsystems DS3 (1 per 2 panelen)."""
    k = math.ceil(n / 2)
    return [f"- **A Solar 460 Wp ({n}×):** N-type, glas-glas, zwart; 1.762 × 1.134 mm per paneel, samen ca. {B.nl(n * 1.762 * 1.134)} m² dak.",
            f"- **APsystems DS3 ({k}×):** micro-omvormer voor twee panelen, 880 VA, 2 MPPT's, rendement ca. 97%. Elk paneelpaar werkt apart, "
            "dus schaduw op één paneel kost weinig. Monitoring via de APsystems ECU-B."]


def pakket(soort, n, dak):
    if soort == "geen":
        P = dict(B.PAKKETTEN["marstek"])
        P["prijzen"] = zonnedeel(n, dak, True)
        P["model"] = dict(P["model"], panelen=n, wp=460, batt_kwh=0)
        P["naam"] = "Zonnepanelen met micro-omvormers, zonder batterij"
        P["batterij_kort"] = f"{math.ceil(n / 2)} APsystems DS3 micro-omvormers (elk voor twee panelen), monitoring via de APsystems ECU-B"
        P["btw_bullet"] = "- **Alles 0%:** panelen, micro-omvormers, bekabeling en montage vallen onder het nultarief."
        P["aansluiting"] = "- **Aansluiting:** de micro-omvormers zijn 1-fase; een gewone aansluiting volstaat, met een eigen groep voor de panelen."
        P["uitbreiding"] = ("- **Later een batterij:** een AC-gekoppelde thuisbatterij, zoals de Marstek Venus E, kan later worden bijgeplaatst "
                            "zonder iets aan de panelen te veranderen. Dat loont vooral bij een groter verbruik (warmtepomp{ev}).")
        P["installatie"] = micro_installatie(n) + [
            "- **Uitbreidbaar:** later kunnen er panelen met extra micro-omvormers{laad} bij, en een thuisbatterij op een eigen groep."]
        P["schouw_extra"] = ", ruimte in de groepenkast voor een groep voor de panelen"
        P["checklist_aansluiting"] = "- [ ] Ruimte in de groepenkast voor een eigen groep voor de zonnepanelen"
        P["begrip_omvormer"] = "| Micro-omvormer | Kleine omvormer onder de panelen; de APsystems DS3 bedient twee panelen. |"
        P["installatie_omvormer"] = "micro-omvormers"
        P["jaarkosten"] = ("Reservering vervanging micro-omvormers", 20, "na een kleine reservering voor de micro-omvormers")
        P["label_zon"] = "Zonnepanelen (panelen, micro-omvormers, montage)"
        P["batt_kosten_zin"] = ""
    elif soort == "marstek":
        P = dict(B.PAKKETTEN["marstek"])
        P["prijzen"] = zonnedeel(n, dak, True) + [p for p in B.PAKKETTEN["marstek"]["prijzen"] if p[4] == "batt"]
        P["model"] = dict(P["model"], panelen=n, wp=460)
        P["naam"] = "Marstek Venus E (5,12 kWh) met micro-omvormers"
        P["installatie"] = micro_installatie(n) + P["installatie"][2:]
    elif soort == "marstek2":
        P = dict(B.PAKKETTEN["marstek"])
        P["prijzen"] = zonnedeel(n, dak, True) + [
            ("2 thuisbatterijen Marstek Venus E 3.0, samen 10,24 kWh, incl. P1-meter", round(2 * 990.91, 2), 0.21, "Marktprijs", "batt"),
            ("Twee eigen groepen voor de batterijen en aansluiten", 400.00, 0.21, "Stelpost", "batt"),
            ("EMS-koppeling Saldox (Modbus TCP)", 100.00, 0.21, "Stelpost", "batt")]
        P["model"] = dict(P["model"], panelen=n, wp=460, batt_kwh=10.24, batt_kw=5.0)
        P["batterij_kort"] = "2× Marstek Venus E 3.0 ({bruikbaar} kWh bruikbaar, samen 5 kW); de panelen hebben APsystems-micro-omvormers"
        P["batt_aanname"] = "Batterij {bruikbaar} kWh bruikbaar (2× Venus E), 5 kW, rendement 85% heen en terug, stand-by ca. 100 kWh per jaar"
        P["jaarkosten"] = ("Stand-by batterijen en reservering", 70, "na het stand-byverbruik van de batterijen en een kleine reservering")
        P["batt_oordeel"] = "twee Venus E's (10 kWh) zijn ruim voor een verbruik van {verbruik} kWh; het rendement van 85% en het stand-byverbruik drukken de winst"
        P["label_batt"] = "Batterij (2× Venus E, eigen groepen, EMS)"
        P["naam"] = "2× Marstek Venus E (10,24 kWh) met micro-omvormers"
        P["installatie"] = micro_installatie(n) + P["installatie"][2:]
    else:  # sofar
        P = dict(B.PAKKETTEN["sofar"])
        P["prijzen"] = zonnedeel(n, dak, False) + [p for p in B.PAKKETTEN["sofar"]["prijzen"] if p[4] == "batt"]
        P["model"] = dict(P["model"], panelen=n, wp=460)
        P["naam"] = "Sofar BTS 10 kWh met ESI 10 kW hybride omvormer"
    if dak == "plat":
        P["aansluiting"] = P["aansluiting"] + " Het dak is plat: de panelen komen op een opstelling met ballast."
    return P


# ───────────────────────────────────────────── profiel → offerte
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    ap = argparse.ArgumentParser(description="Saldox-offerte uit een klantprofiel")
    ap.add_argument("--klant", default="Klant")
    ap.add_argument("--plaats", default="")
    ap.add_argument("--huishouden", choices=HUISHOUDEN, default="gemiddeld")
    ap.add_argument("--verbruik", type=int, help="jaarverbruik in kWh (overschrijft --huishouden)")
    ap.add_argument("--auto", choices=["geen", "phev", "ev"], default="geen")
    ap.add_argument("--auto-kwh", type=int, help="thuis geladen kWh per jaar (overschrijft het autoprofiel)")
    ap.add_argument("--dak", choices=["plat", "schuin"], default="schuin")
    ap.add_argument("--panelen", type=int, default=10)
    ap.add_argument("--aansluiting", choices=["1-fase", "3-fase", "onbekend"], default="onbekend")
    ap.add_argument("--batterij", choices=["auto", "geen", "marstek", "marstek2", "sofar"], default="auto")
    ap.add_argument("--opstelling", default="", help='legplan, bijvoorbeeld "2 rijen van 5, ca. 5,7 × 3,5 m"')
    ap.add_argument("--datum", default=dt.date.today().isoformat())
    a = ap.parse_args()

    verbruik = a.verbruik or HUISHOUDEN[a.huishouden]
    d = dt.date.fromisoformat(a.datum)
    B.KLANT["datum"] = f"{d.day} {MAANDEN[d.month - 1]} {d.year}"
    auto = dict(B.AUTO[a.auto]) if a.auto != "geen" else None
    if auto and a.auto_kwh:
        auto["kwh"] = a.auto_kwh
    met_batt = ["marstek", "marstek2"] + ([] if a.aansluiting == "1-fase" else ["sofar"])
    # "geen": zonder batterij, met de batterijpakketten ter vergelijking
    kandidaten = met_batt if a.batterij == "auto" else (["geen"] + met_batt if a.batterij == "geen" else [a.batterij])

    profiel_tekst = ", ".join(filter(None, [
        HUISHOUDEN_TEKST[a.huishouden] if not a.verbruik else f"verbruik {B.nl(verbruik)} kWh",
        {"phev": "plug-in hybride, dagelijks geladen", "ev": "elektrische auto"}.get(a.auto, "geen auto"),
        f"{'plat' if a.dak == 'plat' else 'schuin'} dak", f"{a.panelen} panelen" + (f" ({a.opstelling})" if a.opstelling else ""),
        "zonder batterij" if a.batterij == "geen" else ""]))
    meta = f"offerte voor {a.klant}" + (f", {a.plaats}" if a.plaats else "") + f" · {profiel_tekst}"

    print(f"Profiel: {profiel_tekst}; verbruik {verbruik} kWh; kandidaten: {', '.join(kandidaten)}")
    res = {}
    for k in kandidaten:
        P = pakket(k, a.panelen, a.dak)
        v = dict(titel=f"Energieplan {a.klant}", laadpaal=bool(auto), P=P, auto=auto,
                 model=dict(verbruik_kwh=verbruik), meta=meta, opstelling=a.opstelling,
                 chip="Energieplan · " + profiel_tekst)
        R = B.reken(v)
        N = R["sc"][1]
        winst = JAREN_HORIZON * N["netto"] - R["inv"]
        res[k] = (v, R, winst)
        print(f"  {P['naam']:52} investering €{R['inv']:>9,.2f}  netto €{N['netto']:>6,.0f}/jr  "
              f"{N['jaren']:>5} jr  winst 15 jr €{winst:>8,.0f}")
    keuze = "geen" if a.batterij == "geen" else max(res, key=lambda k: res[k][2])
    v, R, winst = res[keuze]
    N = R["sc"][1]

    # referentie: alleen zonnepanelen (met micro-omvormers) en eventueel laadpaal
    ref = res.get("geen") or res.get("marstek") or res[keuze]
    Rr = ref[1]
    zon_netto = Rr["sc"][1]["zon"] + (Rr["sc"][1]["laden"] + Rr["sc"][1]["ere"] if auto else 0)
    zon_inv = Rr["inv_zon"] + (Rr["inv_laad"] if auto else 0)

    rijen = []
    for k, (vv, RR, w) in sorted(res.items(), key=lambda x: -x[1][2]):
        NN = RR["sc"][1]
        rijen.append(f"| {'**' if k == keuze else ''}{vv['P']['naam']}{(' (uw keuze)**' if keuze == 'geen' else ' (advies)**') if k == keuze else ''} | "
                     f"{B.eur2(RR['inv'])} | {B.eur(NN['netto'])} | {NN['jaren']} jaar | {B.eur(w)} |")
    if "geen" not in res:
        rijen.append(f"| Alleen zonnepanelen{' en laadpaal' if auto else ''}, zonder batterij (ter vergelijking) | {B.eur2(zon_inv)} | "
                     f"{B.eur(zon_netto)} | {B.jr(zon_inv, zon_netto)} jaar | {B.eur(JAREN_HORIZON * zon_netto - zon_inv)} |")
    batt_meer = winst - (JAREN_HORIZON * zon_netto - zon_inv)
    beste = max(res, key=lambda k: res[k][2])
    if keuze == "geen":
        bv, bR, bw = res[beste]
        lede = (f"U kiest voor zonnepanelen zonder batterij: na 15 jaar levert dat na aftrek van de investering ca. {B.eur(winst)} op."
                + ("" if beste == "geen" else f" Met een {bv['P']['naam'].split(' met ')[0]} erbij zou dat ca. {B.eur(bw)} zijn, {B.eur(bw - winst)} meer,"
                   f" voor {B.eur2(bR['inv'] - R['inv'])} extra investering."))
        batt_bullet = ("- **Een batterij later toevoegen** kan altijd: de micro-omvormers blijven gewoon werken en een AC-gekoppelde batterij "
                       "komt op een eigen groep. De tabel laat zien wat dat bij dit verbruik zou opleveren.")
    else:
        lede = f"Voor dit huishouden levert {v['P']['naam']} over 15 jaar het meeste op: na aftrek van de investering ca. {B.eur(winst)}."
        batt_bullet = (f"- **De batterij** voegt over 15 jaar ca. {B.eur(batt_meer)} toe ten opzichte van alleen zonnepanelen"
                       f"{'' if batt_meer > 0 else '; bij dit profiel kunt u de batterij ook later toevoegen'}.")
    v["waarom"] = f"""## Waarom dit pakket

{lede}

| Pakket | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd | Opbrengst na 15 jaar |
| --- | --- | --- | --- | --- |
{chr(10).join(rijen)}

- **Profiel:** {profiel_tekst}; verbruik ca. {B.nl(verbruik)} kWh per jaar""" + (f"; {auto['naam']} ca. {B.nl(auto['kwh'])} kWh per jaar thuis geladen" if auto else "") + f""".
- **Keuze:** Saldox rekent elk passend pakket door met dezelfde uurprijzen{'' if keuze == 'geen' else ' en kiest het pakket met de hoogste opbrengst na 15 jaar, de levensduur van de batterij en de omvormers'}.
{batt_bullet}""" + (
        "\n- **Sofar 10 kWh** is niet meegenomen: die vraagt een 3-fase aansluiting." if a.aansluiting == "1-fase" and a.batterij == "auto" else "") + "\n"

    map_ = UIT / f"{a.datum}-{slug(a.klant)}"
    map_.mkdir(parents=True, exist_ok=True)
    src = B.markdown_tekst(v, R)
    (map_ / "energieplan-huishouden-offerte.md").write_text(src, encoding="utf-8")
    kpis = [(B.eur2(R["inv"]), "investering incl. btw", False),
            (f"ca. {N['jaren']} jaar", "terugverdientijd, normaal scenario", True),
            (B.eur(N["netto"]), "netto per jaar (normaal)", False),
            (f"{B.nl(round(R['n']['met_pv']['pv_kwh'], -1))} kWh", "zonnestroom per jaar", False)]
    html = map_ / "offerte.html"
    koppen = dict(B.HEADLINES, **(B.HEADLINES_ZONDER_BATTERIJ if keuze == "geen" else {}),
                  **({"Waarom dit pakket": "Zonder batterij, met ruimte voor later."} if keuze == "geen" else {}))
    titel = bouw(src, koppen, B.figuren(v, R), kpis, v["chip"], html)
    subprocess.run(["node", str(HERE / "render_pdf.js"), str(html), str(map_ / "offerte.pdf"), titel], check=True,
                   stdout=subprocess.DEVNULL)
    uit = {"offerte": dict(inv=R["inv"], inv_ex=R["inv_ex"], netto=[s["netto"] for s in R["sc"]],
                           jaren=[s["jaren"] for s in R["sc"]], keuze=keuze, pakket=v["P"]["naam"],
                           profiel=vars(a), verbruik=verbruik)}
    (map_ / "uitkomsten.json").write_text(json.dumps(uit, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nAdvies: {v['P']['naam']} · {B.eur2(R['inv'])} incl. btw · normaal {N['jaren']} jaar · map {map_}")


if __name__ == "__main__":
    main()
