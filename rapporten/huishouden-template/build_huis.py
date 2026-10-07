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

KLANT = dict(naam="Standaard huishouden", datum="7 oktober 2026", adviseur="Saldox")

# (post, bedrag excl. btw, btw-tarief, status)
PRIJZEN_BASIS = [
    ("10 zonnepanelen à 450 Wp (10 × €65)", 650.00, 0.00, "Inkoopprijs"),
    ("Montage zonnepanelen", 800.00, 0.00, "Stelpost"),
    ("Dakbevestiging en bekabeling", 450.00, 0.00, "Stelpost"),
    ("Batterijset Sofar BTS 10 kWh (2× BTS 5K) met 3-fase ESI 10 kW hybride omvormer", 2889.00, 0.21, "Offerte"),
    ("Installatie batterij en omvormer", 450.00, 0.21, "Stelpost"),
    ("Groepenkast: groepen voor zonnepanelen en batterij, aardlek", 300.00, 0.21, "Stelpost"),
    ("EMS-koppeling Saldox (P1-meter en gateway)", 150.00, 0.21, "Stelpost"),
]
PRIJZEN_LAADPAAL = [
    ("Zaptec Go 2 laadpaal (22 kW, MID-meter)", 825.62, 0.21, "Opgegeven"),
    ("Installatie laadpaal incl. groep en bekabeling", 580.00, 0.21, "Stelpost"),
]
RESERVERING = 75  # per jaar: vervanging omvormer na ca. 12 tot 15 jaar
BATT_FACTOR = (0.7, 1.0, 1.3)  # spreiding batterijopbrengst: prijsverschillen 2025 (×1) tot 2026 (+33%)
OPBRENGST = (861, 917, 1032)   # kWh/kWp: PVGIS oost-west, gemiddeld, zuid
PUBLIEK = (0.45, 0.50, 0.55)   # prijs publiek laden incl. btw
ERE = (0.10, 0.115, 0.13)      # ERE netto per geladen kWh
EV_KWH = 3000                  # thuis geladen per jaar (18.131 km × 20,4 kWh/100 km × 81% thuis)

VARIANTEN = {
    "met-zaptec-go2": dict(titel="Energieplan huishouden: met laadpaal", laadpaal=True,
                           chip="Energieplan · huishouden · zon, batterij en laadpaal"),
    "zonder-laadpaal": dict(titel="Energieplan huishouden: zon en batterij", laadpaal=False,
                            chip="Energieplan · huishouden · zon en batterij"),
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
def reken(laadpaal):
    posten = PRIJZEN_BASIS + (PRIJZEN_LAADPAAL if laadpaal else [])
    regels = [(p, ex, b, st, round(ex * (1 + b), 2)) for p, ex, b, st in posten]
    inv_ex = round(sum(r[1] for r in regels), 2)
    inv = round(sum(r[4] for r in regels), 2)
    inv_zon = round(sum(r[4] for r in regels[:3]), 2)
    inv_batt = round(sum(r[4] for r in regels[3:7]), 2)
    inv_laad = round(sum(r[4] for r in regels[7:]), 2)

    sc = []
    for k in range(3):
        a = dict(m.AANNAMES, opbrengst_kwh_per_kwp=OPBRENGST[k], ev_kwh=EV_KWH if laadpaal else 0,
                 publiek_laden=PUBLIEK[k])
        r = m.besparingen(a)
        zon = round(r["zon"], -1)
        batt = round(r["batterij"] * BATT_FACTOR[k], -1)
        laden = round(r["laden"], -1) if laadpaal else 0
        ere = round(EV_KWH * ERE[k], -1) if laadpaal else 0
        bruto = zon + batt + laden + ere
        sc.append(dict(r=r, zon=zon, batt=batt, laden=laden, ere=ere, bruto=bruto,
                       netto=bruto - RESERVERING, jaren=jr(inv, bruto - RESERVERING)))
    n = sc[1]["r"]
    a = dict(m.AANNAMES, ev_kwh=EV_KWH if laadpaal else 0)
    vast = m.besparingen(a, "vast")
    p27 = m.besparingen(dict(a, spot_factor=1.15))
    extra = {}
    if laadpaal:
        dom = m.simuleer(a, ev_slim=False)
        extra["ev_prijs_dom"] = (dom["netto"] - n["met_beide"]["netto"]) / EV_KWH
    return dict(regels=regels, inv_ex=inv_ex, inv=inv, inv_zon=inv_zon, inv_batt=inv_batt, inv_laad=inv_laad,
                sc=sc, n=n, vast=vast, p27=p27, **extra)


# ───────────────────────────────────────────── tekst
def markdown_tekst(v, R):
    lp = v["laadpaal"]
    A = m.AANNAMES
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

    t = []
    t.append(f"# {v['titel']}\n\n{KLANT['datum']} · {KLANT['adviseur']} · template voor een {KLANT['naam'].lower()}\n")

    # 1 Samenvatting
    t.append(f"""## Samenvatting

Het pakket kost {eur2(R['inv'])} incl. btw en levert na de jaarlijkse reservering netto {eur(sc[0]['netto'])} tot {eur(sc[2]['netto'])} per jaar op; normaal is het in ca. {N['jaren']} jaar terugverdiend ({sc[2]['jaren']} tot {sc[0]['jaren']} jaar).

- **Zonnestroom:** {A['panelen']} panelen van {A['wp']} Wp ({nl(kwp, 1)} kWp), ca. {nl(round(n['met_pv']['pv_kwh'], -1))} kWh per jaar. Zonder batterij gebruikt u {pct(zv_pv)} zelf, met batterij {pct(zv_b)}.
- **Thuisbatterij:** Sofar BTS 10 kWh ({nl(batt_bruikbaar, 1)} kWh bruikbaar) met een 3-fase ESI 10 kW hybride omvormer. Laadt goedkoop van het net en met zonnestroom, en levert op dure uren.
- **Stroomcontract:** dynamisch voor afname en teruglevering; het EMS van Saldox stuurt batterij{' en laadpaal' if lp else ''} op de uurprijs.
""" + (f"""- **Laadpaal:** Zaptec Go 2 voor eigen gebruik, slim laden op goedkope uren. Thuis laden kost ca. {eur(n['ev_prijs_thuis'], 2)} per kWh tegen ca. {eur(PUBLIEK[1], 2)} publiek, plus ERE-vergoeding.
""" if lp else "") + f"""- **Zonnepanelen** verdienen zich het snelst terug (ca. {j_zon} jaar); de batterij vooral via de prijsverschillen op een dynamisch contract.
- **Btw:** 0% op zonnepanelen, omvormer en montage; 21% op de batterij{' en de laadpaal' if lp else ''}.
""")

    # 2 Begroting
    rows = "\n".join(f"| {p} | {eur2(ex)} | {int(b * 100)}% | {eur2(inc)} | {st} |" for p, ex, b, st, inc in R["regels"])
    t.append(f"""## Begroting

Het pakket kost {eur2(R['inv_ex'])} excl. btw en {eur2(R['inv'])} incl. btw. Op zonnepanelen geldt het nultarief; de batterijset valt onder 21%.

| Post | Excl. btw | Btw | Incl. btw | Status |
| --- | --- | --- | --- | --- |
{rows}
| **Totaal** | **{eur2(R['inv_ex'])}** | | **{eur2(R['inv'])}** | |

<!-- FIG:begroting -->

- **Nultarief:** de Belastingdienst rekent 0% btw op levering en installatie van zonnepanelen op of bij een woning, inclusief omvormer, bekabeling, montagemateriaal en aanpassingen in de meterkast voor de panelen.
- **Batterij 21%:** levering en installatie van een thuisbatterij vallen expliciet onder 21%. De batterijset wordt als één prijs geleverd en staat daarom volledig op 21%. Vraag de leverancier het omvormerdeel apart te factureren: dat deel kan onder het nultarief vallen.
- **Stelposten** zijn inschattingen voor een standaard woning. Vervang ze door de offerte van de installateur.
- **Aanname:** de woning heeft een 3-fase aansluiting (3x25 A). Is die 1-fase, dan is een verzwaring nodig of een 1-fase omvormer.
""")

    # 3 Opbrengst per jaar
    wv = [("Zon", N["zon"]), ("Batterij", N["batt"])] + ([("Thuis laden", N["laden"]), ("ERE", N["ere"])] if lp else [])
    t.append(f"""## Wat het per jaar oplevert

Normaal levert het pakket {eur(N['bruto'])} per jaar op; na de reservering voor vervanging van de omvormer blijft {eur(N['netto'])} over.

| Per jaar | Pessimistisch | Normaal | Optimistisch |
| --- | --- | --- | --- |
| Zon (minder stroom inkopen, teruglevering) | {eur(sc[0]['zon'])} | {eur(sc[1]['zon'])} | {eur(sc[2]['zon'])} |
| Batterij (slim laden en ontladen) | {eur(sc[0]['batt'])} | {eur(sc[1]['batt'])} | {eur(sc[2]['batt'])} |
""" + (f"""| Thuis laden in plaats van publiek | {eur(sc[0]['laden'])} | {eur(sc[1]['laden'])} | {eur(sc[2]['laden'])} |
| ERE-vergoeding laadpaal | {eur(sc[0]['ere'])} | {eur(sc[1]['ere'])} | {eur(sc[2]['ere'])} |
""" if lp else "") + f"""| **Bruto per jaar** | **{eur(sc[0]['bruto'])}** | **{eur(sc[1]['bruto'])}** | **{eur(sc[2]['bruto'])}** |
| Reservering vervanging omvormer | −{eur(RESERVERING)} | −{eur(RESERVERING)} | −{eur(RESERVERING)} |
| **Netto per jaar** | **{eur(sc[0]['netto'])}** | **{eur(sc[1]['netto'])}** | **{eur(sc[2]['netto'])}** |

<!-- FIG:waterval -->

**Hoe dit is berekend.** Saldox simuleert elk uur van een jaar met de echte uurprijzen van 2025 (EPEX day-ahead Nederland) en het echte zonneprofiel van Nederland. Het EMS zet de batterij in zoals in de praktijk: met de day-ahead prijzen, die een dag vooruit bekend zijn.

- **Pessimistisch / normaal / optimistisch:** opbrengst {OPBRENGST[0]} / {OPBRENGST[1]} / {nl(OPBRENGST[2])} kWh per kWp (PVGIS: oost-west, gemiddeld, zuid); batterij ×0,7 / ×1 / ×1,3 (in 2026 waren de prijsverschillen binnen een dag ca. 33% groter dan in 2025)""" + (f"""; publiek laden {eur(PUBLIEK[0], 2)} / {eur(PUBLIEK[1], 2)} / {eur(PUBLIEK[2], 2)} per kWh; ERE {eur(ERE[0], 2)} / {eur(ERE[1], 3)} / {eur(ERE[2], 2)} per kWh.""" if lp else ".") + f"""
- **Stroomprijs:** uurprijs plus opslag van de leverancier (ca. €0,02 per kWh incl. btw), plus btw en energiebelasting ({eur(A['eb_incl'], 4)} per kWh incl. btw in 2026). Teruglevering tegen de uurprijs, zonder terugleverkosten; bij een negatieve prijs zet het EMS de teruglevering stop.
- **Verbruik:** {nl(A['verbruik_kwh'])} kWh per jaar (Milieu Centraal: gemiddeld 2.430 kWh, 2 personen ca. 2.550 kWh) met een standaard dagprofiel: ochtend- en avondpiek, in de winter hoger.""" + (f"""
- **Elektrische auto:** {nl(EV_KWH)} kWh per jaar thuis geladen (CBS: 18.131 km per jaar, TNO: 20,4 kWh per 100 km, 81% thuis).""" if lp else "") + "\n")

    # 4 Terugverdientijd
    t.append(f"""## Terugverdientijd

Het pakket van {eur2(R['inv'])} is normaal in ca. {N['jaren']} jaar terugverdiend; pessimistisch in {sc[0]['jaren']} jaar en optimistisch in {sc[2]['jaren']} jaar.

<!-- FIG:kasstroom -->

| Onderdeel | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd (normaal) |
| --- | --- | --- | --- |
| Zonnepanelen (panelen, montage, bevestiging) | {eur2(R['inv_zon'])} | {eur(zon_n)} | {j_zon} jaar |
| Batterij (set, installatie, groepenkast, EMS) | {eur2(R['inv_batt'])} | {eur(batt_n - RESERVERING)} | {j_batt} jaar |
""" + (f"""| Laadpaal (Zaptec Go 2 en installatie) | {eur2(R['inv_laad'])} | {eur(N['laden'] + N['ere'])} | {jr(R['inv_laad'], N['laden'] + N['ere'])} jaar |
""" if lp else "") + f"""| **Totaal** | **{eur2(R['inv'])}** | **{eur(N['netto'])}** | **{N['jaren']} jaar** |

<!-- FIG:payback -->

- **Zonnepanelen** verdienen zich snel terug, ook zonder saldering: het grootste deel van de waarde zit in de stroom die u zelf gebruikt.
- **De batterij** verdient minder dan de panelen: bij een verbruik van {nl(A['verbruik_kwh'])} kWh is 10 kWh ruim bemeten. Hij verdient sneller bij een groter verbruik (warmtepomp{', elektrische auto' if not lp else ''}) en bij grotere prijsverschillen. De reservering voor de omvormer staat bij de batterij.
""" + (f"""- **De laadpaal** verdient zich het snelst terug, omdat thuis laden veel goedkoper is dan publiek laden. Laadt u nu al thuis aan een gewone laadpaal, dan is de winst kleiner: dan bespaart slim laden ca. {eur((R['ev_prijs_dom'] - n['ev_prijs_thuis']) * EV_KWH)} per jaar, plus de ERE-vergoeding.
""" if lp else ""))

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
- **Een tweede batterijmodule** levert bij dit verbruik weinig extra op. Een warmtepomp{' of elektrische auto' if not lp else ''} verandert dat.
""")

    # 6 Laadpaal (alleen variant A)
    if lp:
        t.append(f"""## Laden met de Zaptec Go 2

Thuis slim laden kost ca. {eur(n['ev_prijs_thuis'], 2)} per kWh, tegen ca. {eur(PUBLIEK[1], 2)} bij een publieke laadpaal. Bij {nl(EV_KWH)} kWh per jaar scheelt dat ca. {eur(N['laden'])}, plus ca. {eur(N['ere'])} ERE-vergoeding.

| | Per kWh | Per jaar ({nl(EV_KWH)} kWh) |
| --- | --- | --- |
| Publiek laden (gemiddeld) | {eur(PUBLIEK[1], 2)} | {eur(PUBLIEK[1] * EV_KWH)} |
| Thuis laden, direct vanaf 18:00 | {eur(R['ev_prijs_dom'], 2)} | {eur(R['ev_prijs_dom'] * EV_KWH)} |
| Thuis laden, slim op goedkope uren | {eur(n['ev_prijs_thuis'], 2)} | {eur(n['ev_prijs_thuis'] * EV_KWH)} |
| ERE-vergoeding (netto) | −{eur(ERE[1], 3)} | −{eur(N['ere'])} |

- **Zaptec Go 2:** tot 22 kW (3-fase, 32 A) of 7,4 kW (1-fase), met ingebouwde MID-gecertificeerde meter, 4G, OCPP en dynamische load balancing via de P1-meter. Bidirectioneel voorbereid (V2G).
- **Slim laden:** het EMS van Saldox laadt de auto op de goedkoopste uren dat hij thuis is, en in het weekend zoveel mogelijk met zonnestroom.
- **ERE:** sinds 1 januari 2026 levert elke thuis geladen kWh ERE's op. Voorwaarden: MID-meter in de laadpaal, gekoppeld aan uw aansluiting, en een inboekdienstverlener (één per jaar). Netto ca. €0,07 tot 0,15 per kWh, gemiddeld rond €0,12. De opbrengst kan schommelen.
- **Gemiddelde prijzen:** publiek laden verschilt sterk per aanbieder en locatie; reken met de tarieven die de bestuurder nu betaalt.
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

- **Einde saldering per 1 januari 2027:** al verwerkt; dit plan rekent nergens met saldering. Bij een vast contract moet de leverancier tot 2030 ten minste 50% van de kale leveringsprijs vergoeden; terugleverkosten mogen alleen de werkelijke kosten dekken en staan vanaf 2027 per kWh op de factuur.
- **Prijzen 2027:** door de oorlog met Iran ligt de groothandelsprijs voor stroom in 2027 op de termijnmarkt ca. 15% hoger dan in 2026. Dan wordt het normale netto ca. {eur(p27_netto)} per jaar ({jr(R['inv'], p27_netto)} jaar).
- **Energiebelasting 2027:** stroom daalt naar €0,1065 per kWh incl. btw.
""")

    # 8 Installatie en veiligheid
    t.append(f"""## Installatie en veiligheid

De installatie is in één tot twee dagen klaar; de batterij hoort op een droge, vorstvrije plek met ruimte voor ventilatie.

- **Sofar ESI 10K-T1:** 3-fase hybride omvormer, 10 kW, tot 20 kWp zonnepanelen op 3 MPPT's, noodstroom (EPS) op alle drie de fasen, rendement tot 98,2%. Communicatie via RS485, CAN en wifi; het EMS van Saldox leest en stuurt hem uit.
- **Sofar BTS 5K (2×):** LFP-batterij, 5,12 kWh per module, samen 10,24 kWh, bruikbaar ca. 9,2 kWh (90%). Laden en ontladen tot 5 kW. Garantie 10 jaar: 70% capaciteit na 10 jaar of 11,3 MWh doorvoer per module.
- **Uitbreidbaar:** de omvormer kan tot 20 kWp panelen aan; er kunnen later panelen{' of een laadpaal' if not lp else ''} bij.
- **Veiligheid:** PGS 37-1 geldt niet voor thuisbatterijen; ook de nieuwe batterijregels van 2028 zonderen thuisbatterijen uit. De installatie moet voldoen aan NEN 1010. Laat een erkende installateur installeren en meld de batterij bij de opstalverzekeraar.
- **Aanmelden:** meld de zonnepanelen en de batterij bij de netbeheerder via energieleveren.nl.
""")

    # 9 Planning
    t.append(f"""## Planning

Van akkoord tot werkend systeem duurt het ca. 4 tot 6 weken.

| Week | Wat |
| --- | --- |
| 1 | Schouw: dak, meterkast, plek batterij{' en laadpaal' if lp else ''}, 3-fase aansluiting |
| 2 tot 3 | Bestellen en leveren; dynamisch contract regelen |
| 4 | Installatie panelen, omvormer en batterij{', laadpaal' if lp else ''} (1 tot 2 dagen) |
| 4 tot 5 | Aanmelden energieleveren.nl, EMS koppelen{', ERE-inboekdienst kiezen' if lp else ''}, oplevering en uitleg |
""")

    # 10 Aannames
    t.append(f"""## Aannames en te bevestigen

De cijfers gelden voor een standaard huishouden; vervang de aannames door de gegevens van de klant voordat het advies definitief is.

**Te bevestigen bij de klant**

- [ ] Jaarverbruik en verbruiksprofiel (slimme meter){'; aantal kilometers en huidige laadkosten van de auto' if lp else ''}
- [ ] Dak: oriëntatie, hellingshoek, schaduw en ruimte voor 10 panelen (ca. 20 m²)
- [ ] 3-fase aansluiting (3x25 A) en ruimte in de meterkast
- [ ] Plek voor de batterij: droog, vorstvrij, bereikbaar
- [ ] Stroomcontract: dynamisch voor afname en teruglevering
- [ ] Offerte installateur voor de stelposten

**Aannames**

- Verbruik {nl(A['verbruik_kwh'])} kWh per jaar; opbrengst {OPBRENGST[1]} kWh per kWp
- Uurprijzen en zonneprofiel van 2025; opslag dynamisch contract ca. €0,02 per kWh incl. btw; energiebelasting 2026
- Batterij {nl(batt_bruikbaar, 1)} kWh bruikbaar, 5 kW, rendement 90% heen en terug
- Reservering vervanging omvormer €{RESERVERING} per jaar""" + (f"""
- Elektrische auto {nl(EV_KWH)} kWh per jaar thuis; publiek laden {eur(PUBLIEK[1], 2)} per kWh; ERE {eur(ERE[1], 3)} per kWh netto""" if lp else "") + "\n")

    # 11 Begrippen
    t.append("""## Begrippen

De technische termen in dit advies, in gewone taal.

| Begrip | Uitleg |
| --- | --- |
| Dynamisch contract | Stroomcontract met een prijs die elk uur verandert, voor afname en teruglevering. |
| EMS | Energiemanagementsysteem: de software van Saldox die batterij""" + (", laadpaal" if lp else "") + """ en omvormer op de uurprijs stuurt. |
| ERE | Emissiereductie-eenheid: vergoeding voor stroom die in een elektrische auto wordt geladen, via een inboekdienstverlener. |
| Hybride omvormer | Omvormer die zonnepanelen én batterij aansluit en bij stroomuitval noodstroom kan leveren. |
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
    "Zonnestroom zelf gebruiken": "Uw eigen stroom is meer waard dan teruglevering.",
    "Laden met de Zaptec Go 2": "Thuis laden is de grootste winst.",
    "Stroomcontract en prijzen": "Dynamisch laat de batterij verdienen.",
    "Installatie en veiligheid": "Eén installatie, klaar voor later.",
    "Planning": "Binnen anderhalve maand werkend.",
    "Aannames en te bevestigen": "Wat we bij u thuis nog bevestigen.",
    "Begrippen": "Begrippen in gewone taal.",
}


def figuren(v, R):
    sc, N = R["sc"], R["sc"][1]
    lp = v["laadpaal"]
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
    wf += [("Bruto", N["bruto"], "totaal"), ("Reservering omvormer", -RESERVERING, "min"), ("Netto per jaar", N["netto"], "totaal")]
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
                                  sub="Netto, na reservering · incl. btw")
    return f


def main():
    uit = {}
    for key, v in VARIANTEN.items():
        R = reken(v["laadpaal"])
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
