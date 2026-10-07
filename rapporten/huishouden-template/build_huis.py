#!/usr/bin/env python3
"""Bouwt de huishouden-templates (met en zonder Zaptec Go 2) in Saldox-huisstijl.

Alle getallen komen uit model_huis.py (simulatie per uur) en uit VARIANTEN/PRIJZEN
hieronder. Pas voor een klant alleen KLANT, PRIJZEN of de AANNAMES in model_huis.py aan
en draai:   python3 build_huis.py && python3 check_huis.py
"""
import json
import subprocess
from pathlib import Path

import charts
import model_huis as m
from opmaak import bouw

HERE = Path(__file__).parent

# Inkoopprijzen uit de centrale prijslijst (rapporten/prijzen/inkoopprijzen.json)
_PRIJSLIJST = json.loads((HERE.parent / "prijzen/inkoopprijzen.json").read_text(encoding="utf-8"))


def inkoop(zoek):
    """Netto prijs per stuk (excl. btw) van het artikel waarvan ref of omschrijving `zoek` bevat."""
    hits = [r for o in _PRIJSLIJST["offertes"] for r in o["regels"] if zoek in r["ref"] or zoek in r["artikel"]]
    assert len(hits) == 1, f"prijslijst: {len(hits)} treffers voor {zoek!r}"
    return hits[0]["netto_per_stuk"]


def bedrag(aantal, zoek):
    from decimal import Decimal, ROUND_HALF_UP
    return float((Decimal(str(inkoop(zoek))) * aantal).quantize(Decimal("0.01"), ROUND_HALF_UP))


KLANT = dict(naam="Standaard huishouden", datum="7 oktober 2026", adviseur="Saldox")

PLATDAK_MONTAGE = next(t["prijs"] for t in _PRIJSLIJST["tarieven"] if "plat dak" in t["artikel"])
TRANSPORT = next(t["prijs"] for t in _PRIJSLIJST["tarieven"] if t["artikel"].startswith("Transport"))

# Pakketten: per pakket de posten (post, excl. btw, btw-tarief, status, groep), de
# modelwaarden (overschrijven AANNAMES in model_huis.py) en de productteksten.
PAKKETTEN = {
    "sofar": dict(
        model=dict(panelen=10, batt_kwh=10.24, batt_bruikbaar=0.90, batt_kw=5.0, rendement=0.90),
        prijzen=[
            ("10 zonnepanelen à 450 Wp (10 × €65)", 650.00, 0.00, "Inkoopprijs", "zon"),
            ("Montage zonnepanelen", 800.00, 0.00, "Stelpost", "zon"),
            ("Dakbevestiging en bekabeling", 450.00, 0.00, "Stelpost", "zon"),
            ("Batterijset Sofar BTS 10 kWh (2× BTS 5K) met 3-fase ESI 10 kW hybride omvormer", bedrag(1, "MFQ-023-0106934"), 0.21, "Offerte", "batt"),
            ("Installatie batterij en omvormer", 450.00, 0.21, "Stelpost", "batt"),
            ("Groepenkast: groepen voor zonnepanelen en batterij, aardlek", 300.00, 0.21, "Stelpost", "batt"),
            ("EMS-koppeling Saldox (P1-meter en gateway)", 150.00, 0.21, "Stelpost", "batt"),
        ],
        batterij_kort="Sofar BTS 10 kWh ({bruikbaar} kWh bruikbaar) met een 3-fase ESI 10 kW hybride omvormer",
        btw_bullet="- **Batterij 21%:** levering en installatie van een thuisbatterij vallen expliciet onder 21%. De batterijset wordt als één prijs geleverd en staat daarom volledig op 21%. Vraag de leverancier het omvormerdeel apart te factureren: dat deel kan onder het nultarief vallen.",
        aansluiting="- **Aanname:** de woning heeft een 3-fase aansluiting (3x25 A). Is die 1-fase, dan is een verzwaring nodig of een 1-fase omvormer.",
        uitbreiding="- **Een tweede batterijmodule** levert bij dit verbruik weinig extra op. Een warmtepomp{ev} verandert dat.",
        installatie=[
            "- **Sofar ESI 10K-T1:** 3-fase hybride omvormer, 10 kW, tot 20 kWp zonnepanelen op 3 MPPT's, noodstroom (EPS) op alle drie de fasen, rendement tot 98,2%. Communicatie via RS485, CAN en wifi; het EMS van Saldox leest en stuurt hem uit.",
            "- **Sofar BTS 5K (2×):** LFP-batterij, 5,12 kWh per module, samen 10,24 kWh, bruikbaar ca. 9,2 kWh (90%). Laden en ontladen tot 5 kW. Garantie 10 jaar: 70% capaciteit na 10 jaar of 11,3 MWh doorvoer per module.",
            "- **Uitbreidbaar:** de omvormer kan tot 20 kWp panelen aan; er kunnen later panelen{laad} bij.",
        ],
        schouw_extra=", 3-fase aansluiting",
        checklist_aansluiting="- [ ] 3-fase aansluiting (3x25 A) en ruimte in de meterkast",
        begrip_omvormer="| Hybride omvormer | Omvormer die zonnepanelen én batterij aansluit en bij stroomuitval noodstroom kan leveren. |",
        installatie_omvormer="omvormer en batterij",
        batt_aanname="Batterij {bruikbaar} kWh bruikbaar, 5 kW, rendement 90% heen en terug",
        jaarkosten=("Reservering vervanging omvormer", 75, "na de reservering voor vervanging van de omvormer"),
        batt_oordeel="bij een verbruik van {verbruik} kWh is 10 kWh ruim bemeten",
        label_zon="Zonnepanelen (panelen, montage, bevestiging)",
        label_batt="Batterij (set met omvormer, installatie, groepenkast, EMS)",
        batt_kosten_zin=" De reservering voor de omvormer staat bij de batterij.",
    ),
    "marstek": dict(
        model=dict(panelen=8, wp=460, batt_kwh=5.12, batt_bruikbaar=0.90, batt_kw=2.5, rendement=0.85),
        prijzen=[
            ("8 zonnepanelen A Solar 460 Wp, glas-glas (8 × €69,46)", bedrag(8, "A Solar zonnepaneel 460 Wp"), 0.00, "Inkoopprijs", "zon"),
            ("4 micro-omvormers APsystems DS3, 880 VA (4 × €110,74)", bedrag(4, "MFQ-023-0106911"), 0.00, "Inkoopprijs", "zon"),
            ("8 Y3 AC-buskabels en 8 eindkappen (APsystems)", round(bedrag(8, "MFQ-023-0106912") + bedrag(8, "MFQ-023-0106913"), 2), 0.00, "Inkoopprijs", "zon"),
            ("Monitoring APsystems ECU-B", 67.00, 0.00, "Stelpost", "zon"),
            ("Transport", TRANSPORT, 0.00, "Tarief", "zon"),
            ("Montage zonnepanelen en micro-omvormers", 700.00, 0.00, "Stelpost", "zon"),
            ("Dakbevestiging en bekabeling", 400.00, 0.00, "Stelpost", "zon"),
            ("Thuisbatterij Marstek Venus E 3.0, 5,12 kWh, incl. P1-meter", 990.91, 0.21, "Marktprijs", "batt"),
            ("Eigen groep voor de batterij (2.500 W) en aansluiten", 250.00, 0.21, "Stelpost", "batt"),
            ("EMS-koppeling Saldox (Modbus TCP)", 100.00, 0.21, "Stelpost", "batt"),
        ],
        batterij_kort="Marstek Venus E 3.0 ({bruikbaar} kWh bruikbaar, 2,5 kW); de panelen hebben APsystems-micro-omvormers",
        btw_bullet="- **Batterij 21%:** levering en installatie van een thuisbatterij vallen onder 21%. Panelen, micro-omvormers, bekabeling en montage vallen onder het nultarief.",
        aansluiting="- **Aansluiting:** de micro-omvormers en de Venus E zijn 1-fase; een gewone aansluiting volstaat. De Venus E krijgt een eigen groep, zodat hij met 2.500 W kan laden en ontladen. Op een gewoon stopcontact is het maximaal 800 W.",
        uitbreiding="- **Een tweede Venus E** (tot 3 op één fase) levert bij dit verbruik weinig extra op. Een warmtepomp{ev} verandert dat.",
        installatie=[
            "- **A Solar 460 Wp (8×):** N-type, glas-glas, zwart; 1.762 × 1.134 mm per paneel, samen ca. 16 m² dak.",
            "- **APsystems DS3 (4×):** micro-omvormer voor twee panelen, 880 VA, 2 MPPT's, rendement ca. 97%. Elk paneelpaar werkt apart, dus schaduw op één paneel kost weinig. Monitoring via de APsystems ECU-B.",
            "- **Marstek Venus E 3.0:** LFP-batterij, 5,12 kWh, bruikbaar ca. 4,6 kWh, 2.500 W laden en ontladen op een eigen groep, rendement ca. 85% heen en terug, stand-by ca. 5 W. Meer dan 6.000 cycli, garantie 10 jaar. Het EMS van Saldox stuurt hem via Modbus TCP op de uurprijs.",
            "- **Plaatsing:** op een eigen groep, nooit via een verlengsnoer of stekkerdoos; op een droge, geventileerde plek buiten de vluchtroute. De batterij schakelt zichzelf uit bij stroomuitval van het net.",
            "- **Uitbreidbaar:** later kunnen er panelen met extra micro-omvormers{laad} bij, en tot 3 Venus E's op één fase.",
        ],
        schouw_extra=", ruimte in de groepenkast",
        checklist_aansluiting="- [ ] Ruimte in de groepenkast voor een eigen groep voor de batterij",
        begrip_omvormer="| Micro-omvormer | Kleine omvormer onder de panelen; de APsystems DS3 bedient twee panelen. |\n| AC-gekoppelde batterij | Batterij met een eigen omvormer die op het huisnet wordt aangesloten, los van de zonnepanelen. |",
        installatie_omvormer="micro-omvormers en batterij",
        batt_aanname="Batterij {bruikbaar} kWh bruikbaar, 2,5 kW, rendement 85% heen en terug, stand-by ca. 50 kWh per jaar",
        jaarkosten=("Stand-by batterij en reservering", 40, "na het stand-byverbruik van de batterij en een kleine reservering"),
        batt_oordeel="een batterij van 5 kWh past bij een verbruik van {verbruik} kWh, maar het rendement van 85% en het stand-byverbruik drukken de winst",
        label_zon="Zonnepanelen (panelen, micro-omvormers, montage)",
        label_batt="Batterij (Venus E, eigen groep, EMS)",
        batt_kosten_zin=" Het stand-byverbruik en de reservering staan bij de batterij.",
    ),
}

PRIJZEN_LAADPAAL = [
    ("Zaptec Go 2 laadpaal (22 kW, MID-meter)", 825.62, 0.21, "Opgegeven"),
    ("Installatie laadpaal incl. groep en bekabeling", 580.00, 0.21, "Stelpost"),
]
BATT_FACTOR = (0.7, 1.0, 1.3)  # spreiding batterijopbrengst: prijsverschillen 2025 (×1) tot 2026 (+33%)
OPBRENGST = (861, 917, 1032)   # kWh/kWp: PVGIS oost-west, gemiddeld, zuid
PUBLIEK = (0.45, 0.50, 0.55)   # prijs publiek laden incl. btw
ERE = (0.10, 0.115, 0.13)      # ERE netto per geladen kWh
EV_KWH = 3000                  # thuis geladen per jaar (18.131 km × 20,4 kWh/100 km × 81% thuis)

# Autoprofielen: hoeveel er thuis geladen wordt en waarmee thuisladen wordt vergeleken.
AUTO = {
    "ev": dict(naam="elektrische auto", kwh=EV_KWH, kw=11.0, basis=PUBLIEK, ere=ERE,
               bron="CBS: 18.131 km per jaar, TNO: 20,4 kWh per 100 km, 81% thuis",
               basis_kort="publiek", basis_reeks="publiek laden", basis_label="Publiek laden (gemiddeld)", basis_zin="bij een publieke laadpaal",
               basis_lang="dan publiek laden",
               basis_toelichting="- **Gemiddelde prijzen:** publiek laden verschilt sterk per aanbieder en locatie; reken met de tarieven die de bestuurder nu betaalt."),
    "phev": dict(naam="plug-in hybride", kwh=2000, kw=3.7, basis=(0.50, 0.60, 0.66), ere=ERE,
                 bron="dagelijks geladen: ca. 40 km per werkdag elektrisch, 20 kWh per 100 km",
                 basis_kort="op benzine", basis_reeks="benzine omgerekend", basis_label="Dezelfde kilometers op benzine", basis_zin="als u dezelfde kilometers op benzine rijdt",
                 basis_lang="dan dezelfde kilometers op benzine rijden",
                 basis_toelichting="- **Vergelijking met benzine:** 6 liter per 100 km à €2,00 tegenover 20 kWh per 100 km elektrisch; dat is ca. €0,60 per kWh. Laadt u nu al thuis aan het stopcontact, dan is de winst kleiner."),
}

VARIANTEN = {
    "met-zaptec-go2": dict(titel="Energieplan huishouden: met laadpaal", laadpaal=True, pakket="sofar",
                           chip="Energieplan · huishouden · zon, batterij en laadpaal"),
    "zonder-laadpaal": dict(titel="Energieplan huishouden: zon en batterij", laadpaal=False, pakket="sofar",
                            chip="Energieplan · huishouden · zon en batterij"),
    "marstek-8-panelen": dict(titel="Energieplan huishouden: 8 panelen en Marstek", laadpaal=False, pakket="marstek",
                              chip="Energieplan · huishouden · 8 panelen en stekkerbatterij"),
}


# ───────────────────────────────────────────── opmaak getallen
def nl(v, dec=0):
    return f"{abs(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def eur(v, dec=0):
    return ("−€" if v < 0 else "€") + nl(v, dec)


def eur2(v):
    return eur(v, 2)


def jr(inv, netto):
    return "niet" if netto <= 0 else nl(inv / netto, 1)


def pct(v):
    return f"{v * 100:.0f}%"


# ───────────────────────────────────────────── rekenen
def reken(v):
    laadpaal = v["laadpaal"]
    P = v.get("P") or PAKKETTEN[v["pakket"]]
    A = dict(m.AANNAMES, **P["model"], **v.get("model", {}))
    EVd = v.get("auto") or AUTO["ev"]
    EV_KWH, PUBLIEK, ERE = EVd["kwh"], EVd["basis"], EVd["ere"]
    A["ev_kw"] = EVd["kw"]
    posten = P["prijzen"] + ([p + ("laad",) for p in PRIJZEN_LAADPAAL] if laadpaal else [])
    regels = [(p, ex, b, st, round(ex * (1 + b), 2), g) for p, ex, b, st, g in posten]
    inv_ex = round(sum(r[1] for r in regels), 2)
    inv = round(sum(r[4] for r in regels), 2)
    inv_zon = round(sum(r[4] for r in regels if r[5] == "zon"), 2)
    inv_batt = round(sum(r[4] for r in regels if r[5] == "batt"), 2)
    inv_laad = round(sum(r[4] for r in regels if r[5] == "laad"), 2)

    sc = []
    for k in range(3):
        a = dict(A, opbrengst_kwh_per_kwp=OPBRENGST[k], ev_kwh=EV_KWH if laadpaal else 0,
                 publiek_laden=PUBLIEK[k])
        r = m.besparingen(a)
        zon = round(r["zon"], -1)
        batt = round(r["batterij"] * BATT_FACTOR[k], -1)
        laden = round(r["laden"], -1) if laadpaal else 0
        ere = round(EV_KWH * ERE[k], -1) if laadpaal else 0
        bruto = zon + batt + laden + ere
        sc.append(dict(r=r, zon=zon, batt=batt, laden=laden, ere=ere, bruto=bruto,
                       netto=bruto - P["jaarkosten"][1], jaren=jr(inv, bruto - P["jaarkosten"][1])))
    n = sc[1]["r"]
    a = dict(A, ev_kwh=EV_KWH if laadpaal else 0)
    vast = m.besparingen(a, "vast")
    p27 = m.besparingen(dict(a, spot_factor=1.15))
    sal = m.besparingen(dict(a, saldering=True))
    sal_vast = m.besparingen(dict(a, saldering=True), "vast")
    extra = {}
    if laadpaal:
        dom = m.simuleer(a, ev_slim=False)
        extra["ev_prijs_dom"] = (dom["netto"] - n["met_beide"]["netto"]) / EV_KWH
    montage = next(r for r in regels if r[0].startswith("Montage zonnepanelen"))
    extra["inv_plat"] = round(inv - montage[4] + PLATDAK_MONTAGE, 2)
    extra["montage_basis"] = montage[1]
    return dict(EV=EVd, A=A, P=P, regels=regels, inv_ex=inv_ex, inv=inv, inv_zon=inv_zon, inv_batt=inv_batt, inv_laad=inv_laad,
                sc=sc, n=n, vast=vast, p27=p27, sal=sal, sal_vast=sal_vast, **extra)


# ───────────────────────────────────────────── tekst
def markdown_tekst(v, R):
    lp = v["laadpaal"]
    A, P, EVd = R["A"], R["P"], R["EV"]
    EV_KWH, PUBLIEK, ERE = EVd["kwh"], EVd["basis"], EVd["ere"]
    RESERVERING = P["jaarkosten"][1]
    sc, n = R["sc"], R["n"]
    N = sc[1]
    kwp = A["panelen"] * A["wp"] / 1000
    zv_pv, zv_b = n["met_pv"]["zelfverbruik"], n["met_beide"]["zelfverbruik"]
    batt_bruikbaar = A["batt_kwh"] * A["batt_bruikbaar"]
    zon_n, batt_n = N["zon"], N["batt"]
    j_zon = jr(R["inv_zon"], zon_n)
    j_batt = jr(R["inv_batt"], batt_n - RESERVERING)
    vast_netto = round(R["vast"]["zon"], -1) + round(R["vast"]["batterij"], -1) - RESERVERING + (
        round(R["vast"]["laden"], -1) + N["ere"] if lp else 0)
    p27_netto = round(R["p27"]["zon"], -1) + round(R["p27"]["batterij"], -1) - RESERVERING + (
        round(R["p27"]["laden"], -1) + N["ere"] if lp else 0)

    def netto_van(r, ere=N["ere"]):
        return round(r["zon"], -1) + round(r["batterij"], -1) - RESERVERING + (round(r["laden"], -1) + ere if lp else 0)
    sal, sal_vast = R["sal"], R["sal_vast"]
    sal_netto, sal_vast_netto = netto_van(sal), netto_van(sal_vast)
    zonder_netto = netto_van(n)
    assert zonder_netto == N["netto"], (zonder_netto, N["netto"])
    verlies_zon = round(sal["zon"], -1) - round(n["zon"], -1)
    gesaldeerd = min(sal["met_beide"]["export_kwh"], sal["met_beide"]["import_kwh"])
    batt_rel_met = round(sal["batterij"], -1) / (round(sal["zon"], -1) + round(sal["batterij"], -1))
    batt_rel_zonder = round(n["batterij"], -1) / (round(n["zon"], -1) + round(n["batterij"], -1))

    platdak_bullet = "" if R["montage_basis"] == PLATDAK_MONTAGE else (
        f"- **Optie plat dak:** de montage kost bij een plat dak vast {eur2(PLATDAK_MONTAGE)} (0% btw) in plaats van "
        f"{eur2(R['montage_basis'])}. Het pakket kost dan {eur2(R['inv_plat'])} incl. btw en is normaal in ca. "
        f"{jr(R['inv_plat'], N['netto'])} jaar terugverdiend.")
    t = []
    t.append(f"# {v['titel']}\n\n{KLANT['datum']} · {KLANT['adviseur']} · " + (v.get("meta") or f"template voor een {KLANT['naam'].lower()}") + "\n")

    # 1 Samenvatting
    t.append(f"""## Samenvatting

Het pakket kost {eur2(R['inv'])} incl. btw en levert na de jaarlijkse kosten netto {eur(sc[0]['netto'])} tot {eur(sc[2]['netto'])} per jaar op; normaal is het in ca. {N['jaren']} jaar terugverdiend ({sc[2]['jaren']} tot {sc[0]['jaren']} jaar).

- **Zonnestroom:** {A['panelen']} panelen van {A['wp']} Wp ({nl(kwp, 1)} kWp), ca. {nl(round(n['met_pv']['pv_kwh'], -1))} kWh per jaar. Zonder batterij gebruikt u {pct(zv_pv)} zelf, met batterij {pct(zv_b)}.
- **Thuisbatterij:** {P['batterij_kort'].format(bruikbaar=nl(batt_bruikbaar, 1))}. Laadt goedkoop van het net en met zonnestroom, en levert op dure uren.
- **Stroomcontract:** dynamisch voor afname en teruglevering; het EMS van Saldox stuurt batterij{' en laadpaal' if lp else ''} op de uurprijs.
""" + (f"""- **Laadpaal:** Zaptec Go 2 voor eigen gebruik, slim laden op goedkope uren. Thuis laden kost ca. {eur(n['ev_prijs_thuis'], 2)} per kWh tegen ca. {eur(PUBLIEK[1], 2)} {EVd['basis_kort']}, plus ERE-vergoeding.
""" if lp else "") + f"""- **Zonnepanelen** verdienen zich het snelst terug (ca. {j_zon} jaar); de batterij vooral via de prijsverschillen op een dynamisch contract.
- **Btw:** 0% op zonnepanelen, omvormer en montage; 21% op de batterij{' en de laadpaal' if lp else ''}.
""")

    # 2 Begroting
    rows = "\n".join(f"| {p} | {eur2(ex)} | {int(b * 100)}% | {eur2(inc)} | {st} |" for p, ex, b, st, inc, _ in R["regels"])
    t.append(f"""## Begroting

Het pakket kost {eur2(R['inv_ex'])} excl. btw en {eur2(R['inv'])} incl. btw. Op zonnepanelen geldt het nultarief; de batterijset valt onder 21%.

| Post | Excl. btw | Btw | Incl. btw | Status |
| --- | --- | --- | --- | --- |
{rows}
| **Totaal** | **{eur2(R['inv_ex'])}** | | **{eur2(R['inv'])}** | |

<!-- FIG:begroting -->

- **Nultarief:** de Belastingdienst rekent 0% btw op levering en installatie van zonnepanelen op of bij een woning, inclusief omvormer, bekabeling, montagemateriaal en aanpassingen in de meterkast voor de panelen.
{P['btw_bullet']}
{platdak_bullet}
- **Stelposten** zijn inschattingen voor een standaard woning. Vervang ze door de offerte van de installateur.
{P['aansluiting']}
""")

    # 3 Opbrengst per jaar
    wv = [("Zon", N["zon"]), ("Batterij", N["batt"])] + ([("Thuis laden", N["laden"]), ("ERE", N["ere"])] if lp else [])
    t.append(f"""## Wat het per jaar oplevert

Normaal levert het pakket {eur(N['bruto'])} per jaar op; {P['jaarkosten'][2]} blijft {eur(N['netto'])} over.

| Per jaar | Pessimistisch | Normaal | Optimistisch |
| --- | --- | --- | --- |
| Zon (minder stroom inkopen, teruglevering) | {eur(sc[0]['zon'])} | {eur(sc[1]['zon'])} | {eur(sc[2]['zon'])} |
| Batterij (slim laden en ontladen) | {eur(sc[0]['batt'])} | {eur(sc[1]['batt'])} | {eur(sc[2]['batt'])} |
""" + (f"""| Thuis laden in plaats van {EVd['basis_kort']} | {eur(sc[0]['laden'])} | {eur(sc[1]['laden'])} | {eur(sc[2]['laden'])} |
| ERE-vergoeding laadpaal | {eur(sc[0]['ere'])} | {eur(sc[1]['ere'])} | {eur(sc[2]['ere'])} |
""" if lp else "") + f"""| **Bruto per jaar** | **{eur(sc[0]['bruto'])}** | **{eur(sc[1]['bruto'])}** | **{eur(sc[2]['bruto'])}** |
| {P['jaarkosten'][0]} | −{eur(RESERVERING)} | −{eur(RESERVERING)} | −{eur(RESERVERING)} |
| **Netto per jaar** | **{eur(sc[0]['netto'])}** | **{eur(sc[1]['netto'])}** | **{eur(sc[2]['netto'])}** |

<!-- FIG:waterval -->

**Hoe dit is berekend.** Saldox simuleert elk uur van een jaar met de echte uurprijzen van 2025 (EPEX day-ahead Nederland) en het echte zonneprofiel van Nederland. Het EMS zet de batterij in zoals in de praktijk: met de day-ahead prijzen, die een dag vooruit bekend zijn.

- **Pessimistisch / normaal / optimistisch:** opbrengst {OPBRENGST[0]} / {OPBRENGST[1]} / {nl(OPBRENGST[2])} kWh per kWp (PVGIS: oost-west, gemiddeld, zuid); batterij ×0,7 / ×1 / ×1,3 (in 2026 waren de prijsverschillen binnen een dag ca. 33% groter dan in 2025)""" + (f"""; {EVd['basis_reeks']} {eur(PUBLIEK[0], 2)} / {eur(PUBLIEK[1], 2)} / {eur(PUBLIEK[2], 2)} per kWh; ERE {eur(ERE[0], 2)} / {eur(ERE[1], 3)} / {eur(ERE[2], 2)} per kWh.""" if lp else ".") + f"""
- **Stroomprijs:** uurprijs plus opslag van de leverancier (ca. €0,02 per kWh incl. btw), plus btw en energiebelasting ({eur(A['eb_incl'], 4)} per kWh incl. btw in 2026). Teruglevering tegen de uurprijs, zonder terugleverkosten; bij een negatieve prijs zet het EMS de teruglevering stop.
- **Verbruik:** {nl(A['verbruik_kwh'])} kWh per jaar (Milieu Centraal: gemiddeld 2.430 kWh, 2 personen ca. 2.550 kWh) met een standaard dagprofiel: ochtend- en avondpiek, in de winter hoger.""" + (f"""
- **{EVd['naam'][0].upper() + EVd['naam'][1:]}:** {nl(EV_KWH)} kWh per jaar thuis geladen ({EVd['bron']}).""" if lp else "") + "\n")

    # 4 Terugverdientijd
    t.append(f"""## Terugverdientijd

Het pakket van {eur2(R['inv'])} is normaal in ca. {N['jaren']} jaar terugverdiend; pessimistisch in {sc[0]['jaren']} jaar en optimistisch in {sc[2]['jaren']} jaar.

<!-- FIG:kasstroom -->

| Onderdeel | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd (normaal) |
| --- | --- | --- | --- |
| {P['label_zon']} | {eur2(R['inv_zon'])} | {eur(zon_n)} | {j_zon} jaar |
| {P['label_batt']} | {eur2(R['inv_batt'])} | {eur(batt_n - RESERVERING)} | {j_batt} jaar |
""" + (f"""| Laadpaal (Zaptec Go 2 en installatie) | {eur2(R['inv_laad'])} | {eur(N['laden'] + N['ere'])} | {jr(R['inv_laad'], N['laden'] + N['ere'])} jaar |
""" if lp else "") + f"""| **Totaal** | **{eur2(R['inv'])}** | **{eur(N['netto'])}** | **{N['jaren']} jaar** |

<!-- FIG:payback -->

- **Zonnepanelen** verdienen zich snel terug, ook zonder saldering: het grootste deel van de waarde zit in de stroom die u zelf gebruikt.
- **De batterij** verdient minder dan de panelen: {P['batt_oordeel'].format(verbruik=nl(A['verbruik_kwh']))}. Hij verdient sneller bij een groter verbruik (warmtepomp{', elektrische auto' if not lp else ''}) en bij grotere prijsverschillen.{P['batt_kosten_zin']}
""" + (f"""- **De laadpaal** verdient zich het snelst terug, omdat thuis laden veel goedkoper is {EVd['basis_lang']}. Laadt u nu al thuis aan een gewone laadpaal, dan is de winst kleiner: dan bespaart slim laden ca. {eur((R['ev_prijs_dom'] - n['ev_prijs_thuis']) * EV_KWH)} per jaar, plus de ERE-vergoeding.
""" if lp else ""))

    if v.get("waarom"):
        t.append(v["waarom"])

    # 5 Zelfverbruik
    t.append(f"""## Zonnestroom zelf gebruiken

Overdag is er weinig verbruik in huis, dus een groot deel van de zonnestroom gaat zonder batterij terug het net op. Met de batterij gebruikt u {pct(zv_b)} van de zonnestroom zelf in plaats van {pct(zv_pv)}.

| | Zonder batterij | Met batterij |
| --- | --- | --- |
| Opwek per jaar | {nl(round(n['met_pv']['pv_kwh'], -1))} kWh | {nl(round(n['met_beide']['pv_kwh'], -1))} kWh |
| Zelf gebruikt | {pct(zv_pv)} | {pct(zv_b)} |
| Teruggeleverd | {nl(round(n['met_pv']['export_kwh'], -1))} kWh | {nl(round(n['met_beide']['export_kwh'], -1))} kWh |
| Ingekocht van het net | {nl(round(n['met_pv']['import_kwh'], -1))} kWh | {nl(round(n['met_beide']['import_kwh'], -1))} kWh |

- **Teruglevering is weinig waard:** zonder saldering krijgt u bij een dynamisch contract de uurprijs, en die is laag als de zon schijnt (in 2025 gemiddeld ca. €0,05 per kWh tijdens zonne-uren).
- **De batterij laadt ook van het net:** op goedkope uren 's nachts of midden op de dag, en levert op dure uren in de ochtend en avond. Daardoor stijgt de inkoop van het net soms, terwijl de kosten dalen.
{P['uitbreiding'].format(ev=' of elektrische auto' if not lp else '')}
""")

    # 6 Laadpaal (alleen variant A)
    if lp:
        t.append(f"""## Laden met de Zaptec Go 2

Thuis slim laden kost ca. {eur(n['ev_prijs_thuis'], 2)} per kWh, tegen ca. {eur(PUBLIEK[1], 2)} {EVd['basis_zin']}. Bij {nl(EV_KWH)} kWh per jaar scheelt dat ca. {eur(N['laden'])}, plus ca. {eur(N['ere'])} ERE-vergoeding.

| | Per kWh | Per jaar ({nl(EV_KWH)} kWh) |
| --- | --- | --- |
| {EVd['basis_label']} | {eur(PUBLIEK[1], 2)} | {eur(PUBLIEK[1] * EV_KWH)} |
| Thuis laden, direct vanaf 18:00 | {eur(R['ev_prijs_dom'], 2)} | {eur(R['ev_prijs_dom'] * EV_KWH)} |
| Thuis laden, slim op goedkope uren | {eur(n['ev_prijs_thuis'], 2)} | {eur(n['ev_prijs_thuis'] * EV_KWH)} |
| ERE-vergoeding (netto) | −{eur(ERE[1], 3)} | −{eur(N['ere'])} |

- **Zaptec Go 2:** tot 22 kW (3-fase, 32 A) of 7,4 kW (1-fase), met ingebouwde MID-gecertificeerde meter, 4G, OCPP en dynamische load balancing via de P1-meter. Bidirectioneel voorbereid (V2G).
- **Slim laden:** het EMS van Saldox laadt de auto op de goedkoopste uren dat hij thuis is, en in het weekend zoveel mogelijk met zonnestroom.
- **ERE:** sinds 1 januari 2026 levert elke thuis geladen kWh ERE's op. Voorwaarden: MID-meter in de laadpaal, gekoppeld aan uw aansluiting, en een inboekdienstverlener (één per jaar). Netto ca. €0,07 tot 0,15 per kWh, gemiddeld rond €0,12. De opbrengst kan schommelen.
{EVd['basis_toelichting']}
""")

    # 7 Contract en prijzen
    t.append(f"""## Stroomcontract en prijzen

Het pakket werkt het best met een dynamisch contract: alleen dan kan de batterij goedkoop laden en duur leveren. Met een vast contract wordt het normale netto {eur(vast_netto)} per jaar ({jr(R['inv'], vast_netto)} jaar).

| | Dynamisch (advies) | Vast |
| --- | --- | --- |
| Afname | Uurprijs plus opslag, btw en energiebelasting | Vaste prijs, ca. €0,28 per kWh incl. btw |
| Teruglevering | Uurprijs, bij veel leveranciers zonder terugleverkosten | Vergoeding ca. €0,10 min terugleverkosten €0,045 tot 0,065 |
| Zon per jaar | {eur(round(n['zon'], -1))} | {eur(round(R['vast']['zon'], -1))} |
| Batterij per jaar | {eur(round(n['batterij'], -1))} | {eur(round(R['vast']['batterij'], -1))} |
| Netto per jaar (normaal) | {eur(N['netto'])} | {eur(vast_netto)} |
| Terugverdientijd (normaal) | {N['jaren']} jaar | {jr(R['inv'], vast_netto)} jaar |

- **Einde saldering per 1 januari 2027:** al verwerkt; dit plan rekent zonder saldering (zie *Met en zonder saldering*). Bij een vast contract moet de leverancier tot 2030 ten minste 50% van de kale leveringsprijs vergoeden; terugleverkosten mogen alleen de werkelijke kosten dekken en staan vanaf 2027 per kWh op de factuur.
- **Prijzen 2027:** door de oorlog met Iran ligt de groothandelsprijs voor stroom in 2027 op de termijnmarkt ca. 15% hoger dan in 2026. Dan wordt het normale netto ca. {eur(p27_netto)} per jaar ({jr(R['inv'], p27_netto)} jaar).
- **Energiebelasting 2027:** stroom daalt naar €0,1065 per kWh incl. btw.
""")

    # 7b Saldering
    laad_rij = (f"| Thuis laden en ERE | {eur(round(sal['laden'], -1) + N['ere'])} | {eur(round(n['laden'], -1) + N['ere'])} |\n"
                if lp else "")
    laad_bullet = ("- **Thuis laden:** met saldering is zonnestroom die in de auto gaat al de volle kWh-prijs waard; "
                   "zonder saldering levert laden met eigen zonnestroom juist extra op.\n" if lp else "")
    t.append(f"""## Met en zonder saldering

Tot 1 januari 2027 mag u teruggeleverde stroom wegstrepen tegen stroom die u afneemt; daarna niet meer. Dit plan rekent met de situatie vanaf 2027. Met saldering zou het pakket normaal netto {eur(sal_netto)} per jaar opleveren, zonder {eur(zonder_netto)}.

| Dynamisch contract, normaal scenario | Met saldering (tot 2027) | Zonder saldering (vanaf 2027) |
| --- | --- | --- |
| Zon per jaar | {eur(round(sal['zon'], -1))} | {eur(round(n['zon'], -1))} |
| Batterij per jaar | {eur(round(sal['batterij'], -1))} | {eur(round(n['batterij'], -1))} |
{laad_rij}| Jaarlijkse kosten | −{eur(RESERVERING)} | −{eur(RESERVERING)} |
| **Netto per jaar** | **{eur(sal_netto)}** | **{eur(zonder_netto)}** |
| Terugverdientijd | {jr(R['inv'], sal_netto)} jaar | {jr(R['inv'], zonder_netto)} jaar |
| Netto per jaar bij een vast contract | {eur(sal_vast_netto)} | {eur(vast_netto)} |

- **Wat saldering doet:** met saldering levert elke teruggeleverde kWh, tot uw jaarverbruik, ook de energiebelasting van {eur(A['eb_incl'], 4)} per kWh op (bij een vast contract de volle kWh-prijs). Hier gaat het om ca. {nl(round(gesaldeerd, -1))} kWh per jaar.
- **Zonnepanelen leveren minder op:** zonder saldering ca. {eur(verlies_zon)} per jaar minder. Daarom telt zelf gebruiken vanaf 2027 zwaarder.
- **De batterij wordt belangrijker:** zonder saldering komt {pct(batt_rel_zonder)} van de opbrengst van zon en batterij uit de batterij, met saldering {pct(batt_rel_met)}. De batterij vangt de zonnestroom op die anders bijna niets oplevert.
{laad_bullet}- **Dit plan is niet afhankelijk van saldering:** de terugverdientijd van {jr(R['inv'], zonder_netto)} jaar geldt voor de regels vanaf 2027.
""")

    # 8 Installatie en veiligheid
    t.append(f"""## Installatie en veiligheid

De installatie is in één tot twee dagen klaar; de batterij hoort op een droge, vorstvrije plek met ruimte voor ventilatie.

{chr(10).join(P['installatie']).format(laad=' of een laadpaal' if not lp else '')}
- **Veiligheid:** PGS 37-1 geldt niet voor thuisbatterijen; ook de nieuwe batterijregels van 2028 zonderen thuisbatterijen uit. De installatie moet voldoen aan NEN 1010. Laat een erkende installateur installeren en meld de batterij bij de opstalverzekeraar.
- **Aanmelden:** meld de zonnepanelen en de batterij bij de netbeheerder via energieleveren.nl.
""")

    # 9 Planning
    t.append(f"""## Planning

Van akkoord tot werkend systeem duurt het ca. 4 tot 6 weken.

| Week | Wat |
| --- | --- |
| 1 | Schouw: dak, meterkast, plek batterij{' en laadpaal' if lp else ''}{P['schouw_extra']} |
| 2 tot 3 | Bestellen en leveren; dynamisch contract regelen |
| 4 | Installatie panelen, {P['installatie_omvormer']}{', laadpaal' if lp else ''} (1 tot 2 dagen) |
| 4 tot 5 | Aanmelden energieleveren.nl, EMS koppelen{', ERE-inboekdienst kiezen' if lp else ''}, oplevering en uitleg |
""")

    # 10 Aannames
    t.append(f"""## Aannames en te bevestigen

De cijfers gelden voor een standaard huishouden; vervang de aannames door de gegevens van de klant voordat het advies definitief is.

**Te bevestigen bij de klant**

- [ ] Jaarverbruik en verbruiksprofiel (slimme meter){'; aantal kilometers en huidige laadkosten van de auto' if lp else ''}
- [ ] Dak: plat of schuin (plat dak: montage vast {eur(PLATDAK_MONTAGE)}), oriëntatie, hellingshoek, schaduw en ruimte voor {A['panelen']} panelen (ca. {A['panelen'] * 2} m²)
{P['checklist_aansluiting']}
- [ ] Plek voor de batterij: droog, vorstvrij, bereikbaar
- [ ] Stroomcontract: dynamisch voor afname en teruglevering
- [ ] Offerte installateur voor de stelposten

**Aannames**

- Verbruik {nl(A['verbruik_kwh'])} kWh per jaar; opbrengst {OPBRENGST[1]} kWh per kWp
- Uurprijzen en zonneprofiel van 2025; opslag dynamisch contract ca. €0,02 per kWh incl. btw; energiebelasting 2026
- {P['batt_aanname'].format(bruikbaar=nl(batt_bruikbaar, 1))}
- {P['jaarkosten'][0]} €{RESERVERING} per jaar""" + (f"""
- {EVd['naam'][0].upper() + EVd['naam'][1:]} {nl(EV_KWH)} kWh per jaar thuis; {EVd['basis_reeks']} {eur(PUBLIEK[1], 2)} per kWh; ERE {eur(ERE[1], 3)} per kWh netto""" if lp else "") + "\n")

    # 11 Begrippen
    t.append("""## Begrippen

De technische termen in dit advies, in gewone taal.

| Begrip | Uitleg |
| --- | --- |
| Dynamisch contract | Stroomcontract met een prijs die elk uur verandert, voor afname en teruglevering. |
| EMS | Energiemanagementsysteem: de software van Saldox die batterij""" + (", laadpaal" if lp else "") + """ en omvormer op de uurprijs stuurt. |
| ERE | Emissiereductie-eenheid: vergoeding voor stroom die in een elektrische auto wordt geladen, via een inboekdienstverlener. |
""" + P["begrip_omvormer"] + """
| kWh en kWp | kWh is een hoeveelheid energie; kWp is het piekvermogen van zonnepanelen. |
| LFP | Lithium-ijzerfosfaat: veilige, lang meegaande batterijchemie. |
| MID-meter | Geijkte kWh-meter; nodig voor de ERE-vergoeding. |
| Nultarief | 0% btw op zonnepanelen en hun installatie bij woningen. |
| Saldering | Wegstrepen van teruggeleverde tegen afgenomen stroom; stopt per 1 januari 2027. |
| Stelpost | Geschat bedrag voor een post waarvan de exacte prijs nog niet bekend is. |
| Zelfverbruik | Het deel van de zonnestroom dat u zelf gebruikt in plaats van terug te leveren. |
""")
    return "\n".join(t)


HEADLINES = {
    "Samenvatting": "Wat het kost, en wat het u oplevert.",
    "Begroting": "Elke post op een rij.",
    "Wat het per jaar oplevert": "Uur voor uur doorgerekend.",
    "Terugverdientijd": "Zonnepanelen eerst, de batterij doet het rustiger aan.",
    "Waarom dit pakket": "Het pakket dat over 15 jaar het meeste oplevert.",
    "Zonnestroom zelf gebruiken": "Uw eigen stroom is meer waard dan teruglevering.",
    "Laden met de Zaptec Go 2": "Thuis laden is de grootste winst.",
    "Stroomcontract en prijzen": "Dynamisch laat de batterij verdienen.",
    "Met en zonder saldering": "Vanaf 2027 telt elke eigen kWh zwaarder.",
    "Installatie en veiligheid": "Eén installatie, klaar voor later.",
    "Planning": "Binnen anderhalve maand werkend.",
    "Aannames en te bevestigen": "Wat we bij u thuis nog bevestigen.",
    "Begrippen": "Begrippen in gewone taal.",
}


def figuren(v, R):
    sc, N = R["sc"], R["sc"][1]
    lp = v["laadpaal"]
    RESERVERING = R["P"]["jaarkosten"][1]
    scen = [("Pessimistisch", sc[0]["netto"], sc[0]["jaren"], False), ("Normaal", N["netto"], N["jaren"], True),
            ("Optimistisch", sc[2]["netto"], sc[2]["jaren"], False)]
    f = {}
    f["kasstroom"] = charts.kasstroom(R["inv"], scen, horizon=15,
                                      titel=f"Normaal is het pakket na ca. {N['jaren']} jaar terugverdiend")
    items = [("Zonnepanelen", R["inv_zon"]), ("Batterij", R["inv_batt"])] + ([("Laadpaal", R["inv_laad"])] if lp else [])
    f["begroting"] = charts.begroting(items, R["inv"], titel="Investering per onderdeel, incl. btw",
                                      sub=f"Totaal {eur2(R['inv'])} incl. btw")
    wf = [("Zon", N["zon"], "plus"), ("Batterij", N["batt"], "plus")]
    if lp:
        wf += [("Thuis laden", N["laden"], "plus"), ("ERE", N["ere"], "plus")]
    wf += [("Bruto", N["bruto"], "totaal"), (R["P"]["jaarkosten"][0], -RESERVERING, "min"), ("Netto per jaar", N["netto"], "totaal")]
    f["waterval"] = charts.waterval(wf, sub="Normaal scenario, uit de tabel hierboven")
    pb = []
    zon = [s["zon"] for s in sc]
    pb.append(("Zonnepanelen",) + tuple(R["inv_zon"] / z for z in zon))
    bt = [s["batt"] - RESERVERING for s in sc]
    pb.append(("Batterij",) + tuple((R["inv_batt"] / b if b > 0 and R["inv_batt"] / b <= 25 else None) for b in bt))
    if lp:
        la = [s["laden"] + s["ere"] for s in sc]
        pb.append(("Laadpaal",) + tuple(R["inv_laad"] / x for x in la))
    pb = [(n_, p, nn, o) for n_, p, nn, o in pb]
    f["payback"] = charts.payback(pb, R["inv"] / N["netto"], refs=[(R["inv"] / N["netto"], f"totaal pakket {N['jaren']} jaar", "ref-sun", 20)],
                                  lw=160, cap=25, fid="payback-chart", eyebrow="Terugverdientijd per onderdeel",
                                  title="Per onderdeel: optimistisch tot pessimistisch",
                                  sub="Netto, na jaarlijkse kosten · incl. btw")
    return f


def main():
    uit = {}
    for key, v in VARIANTEN.items():
        R = reken(v)
        src = markdown_tekst(v, R)
        (HERE / f"energieplan-huishouden-{key}.md").write_text(src, encoding="utf-8")
        N = R["sc"][1]
        kpis = [(eur2(R["inv"]), "investering incl. btw", False),
                (f"ca. {N['jaren']} jaar", "terugverdientijd, normaal scenario", True),
                (eur(N["netto"]), "netto per jaar (normaal)", False),
                (f"{nl(round(R['n']['met_pv']['pv_kwh'], -1))} kWh", "zonnestroom per jaar", False)]
        out = HERE / f"rapport-huishouden-{key}.html"
        titel = bouw(src, HEADLINES, figuren(v, R), kpis, v["chip"], out)
        subprocess.run(["node", str(HERE / "render_pdf.js"), str(out), str(out.with_suffix(".pdf")), titel], check=True)
        uit[key] = dict(inv=R["inv"], inv_ex=R["inv_ex"], netto=[s["netto"] for s in R["sc"]], jaren=[s["jaren"] for s in R["sc"]],
                        zon=[s["zon"] for s in R["sc"]], batt=[s["batt"] for s in R["sc"]],
                        laden=[s["laden"] for s in R["sc"]], ere=[s["ere"] for s in R["sc"]])
    (HERE / "uitkomsten.json").write_text(json.dumps(uit, indent=1), encoding="utf-8")
    print(json.dumps(uit, indent=1))


if __name__ == "__main__":
    main()
