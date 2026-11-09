#!/usr/bin/env python3
"""Offerte voor een batterij-uitbreiding bij een woning die al zonnepanelen heeft: de bestaande
panelen gaan op een nieuwe hybride omvormer (Sofar HYD-3PH) met Sofar BTS 5K-modules.

Alleen wat er verandert, telt als opbrengst: de batterij (en de omvormer die hem mogelijk maakt).
De besparing van de bestaande panelen blijft buiten de terugverdientijd.

    python3 offerte_batterij.py --klant "Het Puyven 28" --plaats Nuenen \
        --bestaand-panelen 10 --bestaand-wp 350 --opbrengst 940 \
        --afname 3700 --teruglevering 1600 --verbruik 5400 \
        --auto-kwh 3900 --auto-laaddagen 5 --modules 3 --omvormer hyd10
"""
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import build_huis as B
import charts
import model_huis as m
import offerte as O
from opmaak import bouw

HERE = Path(__file__).parent


def posten(H, modules, alleen_apparatuur=False):
    """Begroting (post, excl. btw, btw, status). Alles 21%: de omvormer komt er voor de batterij."""
    torens = 1 if modules <= 4 else 2
    return [
        (f"Hybride omvormer {H['naam']}, 3-fase, {H['kw']} kW", H["prijs"], 0.21, H["status"]),
        (f"{modules} batterijmodules Sofar BTS 5K, samen {B.nl(modules * 5.12, 2)} kWh ({modules} × €{B.BTS5K:.0f})", round(modules * B.BTS5K, 2), 0.21, "Inkoopprijs"),
        (f"{torens} BDU-besturingsunit{'s' if torens > 1 else ''} ({torens} {'torens' if torens > 1 else 'toren'})", torens * O.BDU, 0.21, "Stelpost"),
    ] + ([("Installatieautomaat 3-fase met aardlek, groep omvormer (materiaal)", O.AUTOMAAT, 0.21, "Opgegeven")] if alleen_apparatuur else [
        ("Oude omvormer demonteren, bestaande panelen aansluiten op de nieuwe omvormer (werk)", 150.00, 0.21, "Stelpost"),
        ("Omvormer plaatsen en aansluiten (werk)", 200.00, 0.21, "Stelpost"),
        ("Installatie batterij en DC-bekabeling (werk)", 450.00, 0.21, "Stelpost"),
        ("Groep in de meterkast aanleggen en aansluiten (werk)", 150.00, 0.21, "Stelpost"),
        ("Installatieautomaat 3-fase met aardlek, groep omvormer (materiaal)", O.AUTOMAAT, 0.21, "Opgegeven"),
        ("Overspanningsbeveiliging AC en DC (materiaal)", 150.00, 0.21, "Stelpost"),
        ("EMS-koppeling Saldox (P1-meter en gateway)", 150.00, 0.21, "Stelpost"),
        ("Handmatige omschakelaar voor noodstroom (ATS), 3-fase (materiaal)", O.ATS_MATERIAAL, 0.21, "Opgegeven"),
        ("Omschakelaar aansluiten in de meterkast (werk)", O.ATS_WERK, 0.21, "Stelpost"),
        ("Transport", B.TRANSPORT, 0.21, "Tarief"),
    ])


def batterij_kw(H, modules):
    torens = 1 if modules <= 4 else 2
    return min(float(H["kw"]), torens * 25 * 102.4 * (modules / torens) / 1000)


def waarde(a, modules, kw, auto=True, contract="dynamisch", saldering=False):
    """Wat de batterij per jaar oplevert: kosten met panelen zonder batterij min kosten met batterij."""
    a = dict(a, batt_kwh=modules * 5.12, batt_bruikbaar=0.90, batt_kw=kw, rendement=0.90, saldering=saldering)
    if not auto:
        a["ev_kwh"] = 0
    zonder = m.simuleer(a, batterij=False, contract=contract)
    met = m.simuleer(a, batterij=True, contract=contract)
    return zonder["netto"] - met["netto"], zonder, met


def main():
    ap = argparse.ArgumentParser(description="Saldox-offerte: batterij bij bestaande zonnepanelen")
    ap.add_argument("--klant", required=True)
    ap.add_argument("--plaats", default="")
    ap.add_argument("--bestaand-panelen", type=int, required=True)
    ap.add_argument("--bestaand-wp", type=int, required=True)
    ap.add_argument("--opbrengst", type=int, help="kWh per kWp van de bestaande panelen (of --opwek)")
    ap.add_argument("--opwek", type=int, help="opwek van de panelen per jaar (kWh, omvormer of portaal)")
    ap.add_argument("--dagfactor", type=float, default=1.0, help="verbruik op werkdagen 9-17 uur t.o.v. het standaardprofiel")
    ap.add_argument("--opbrengst-bron", default="")
    ap.add_argument("--afname", type=int, required=True, help="meter: afname per jaar (kWh)")
    ap.add_argument("--teruglevering", type=int, required=True, help="meter: teruglevering per jaar (kWh)")
    ap.add_argument("--verbruik", type=int, required=True, help="totaal verbruik van het huis (afname + eigen zonnestroom)")
    ap.add_argument("--auto-kwh", type=int, default=0, help="thuis laden per jaar (kWh), auto die erbij komt")
    ap.add_argument("--auto-laaddagen", type=int, default=7)
    ap.add_argument("--auto-tekst", default="")
    ap.add_argument("--modules", type=int, default=3)
    ap.add_argument("--omvormer", choices=list(O.HYD), default="hyd10")
    ap.add_argument("--ere", type=float, default=0.13)
    ap.add_argument("--datum", default=dt.date.today().isoformat())
    ap.add_argument("--alleen-apparatuur", action="store_true",
                    help="alleen omvormer, batterijmodules en BDU; installatie, meterkast, noodstroom, EMS en transport niet in de prijs")
    ap.add_argument("--sectie-eind")
    ap.add_argument("--figuur", action="append", default=[])
    ap.add_argument("--kop", action="append", default=[])
    a = ap.parse_args()

    d = dt.date.fromisoformat(a.datum)
    B.KLANT["datum"] = f"{d.day} {O.MAANDEN[d.month - 1]} {d.year}"
    H = O.HYD[a.omvormer]
    kwp = a.bestaand_panelen * a.bestaand_wp / 1000
    if a.opwek:
        a.opbrengst = round(a.opwek / kwp)
    basis = dict(m.AANNAMES, panelen=a.bestaand_panelen, wp=a.bestaand_wp, opbrengst_kwh_per_kwp=a.opbrengst,
                 verbruik_kwh=a.verbruik, ev_kwh=a.auto_kwh, ev_kw=11.0, ev_laaddagen=a.auto_laaddagen,
                 dagfactor=a.dagfactor)
    nu = m.simuleer(dict(basis, ev_kwh=0), batterij=False)
    auto = bool(a.auto_kwh)

    # begroting
    regels = [(p, ex, b, st, round(ex * (1 + b), 2)) for p, ex, b, st in posten(H, a.modules, a.alleen_apparatuur)]
    inv_ex = round(sum(r[1] for r in regels), 2)
    inv = round(sum(r[4] for r in regels), 2)
    RES = 75

    # opbrengst: scenario's met de spreiding van de batterij (×0,7 / ×1 / ×1,3)
    kw = batterij_kw(H, a.modules)
    w_auto, zonder_b, met_b = waarde(basis, a.modules, kw, auto=auto)
    w_nu, _, met_nu = waarde(basis, a.modules, kw, auto=False)
    sc = []
    for f in B.BATT_FACTOR:
        batt = round(w_auto * f, -1)
        sc.append(dict(batt=batt, bruto=batt, netto=batt - RES, jaren=B.jr(inv, batt - RES)))
    N = sc[1]
    nu_netto = round(w_nu, -1) - RES
    w_vast, _, _ = waarde(basis, a.modules, kw, auto=auto, contract="vast")
    vast_netto = round(w_vast, -1) - RES
    w_sal, _, _ = waarde(basis, a.modules, kw, auto=auto, saldering=True)
    sal_netto = round(w_sal, -1) - RES

    # andere batterijgroottes (zelfde omvormer)
    maten = []
    for mod in (2, 3, 4):
        k = batterij_kw(H, mod)
        w, _, met = waarde(basis, mod, k, auto=auto)
        inv_m = round(sum(round(ex * (1 + b), 2) for _, ex, b, _ in posten(H, mod, a.alleen_apparatuur)), 2)
        net = round(w, -1) - RES
        maten.append(dict(mod=mod, kwh=mod * 5.12, kw=k, inv=inv_m, netto=net, jaren=B.jr(inv_m, net),
                          winst=15 * net - inv_m, zv=met["zelfverbruik"], huidig=mod == a.modules))

    # laadpaal-informatie (verbruik inclusief de auto)
    R_lp = dict(A=dict(basis, verbruik_kwh=a.verbruik + a.auto_kwh, batt_kwh=a.modules * 5.12, batt_bruikbaar=0.90,
                       batt_kw=kw, rendement=0.90))
    lp_tekst = O.info_laadpaal(R_lp, a.auto_kwh, a.ere, kw=11.0) if auto else ""
    L = O.LAADPAAL_INFO

    AA = a.alleen_apparatuur
    excl = ("exclusief installatie, noodstroomschakelaar en EMS-koppeling" if AA
            else "exclusief het trekken van de bedrading (op uurbasis)")
    t = []
    titel = f"Energieplan {a.klant}"
    t.append(f"# {titel}\n\n{B.KLANT['datum']} · Saldox · offerte voor {a.klant}" + (f", {a.plaats}" if a.plaats else "")
             + f" · thuisbatterij {round(a.modules * 5.12)} kWh bij de bestaande zonnepanelen\n")
    zv_nu = nu["zelfverbruik"]
    t.append(f"""## Samenvatting

De bestaande {a.bestaand_panelen} zonnepanelen gaan op een nieuwe hybride omvormer met een thuisbatterij van {B.nl(a.modules * 5.12, 1)} kWh. Dat kost {B.eur2(inv)} incl. btw, {excl}, en levert {'met de auto erbij ' if auto else ''}normaal netto {B.eur(N['netto'])} per jaar op; het is in ca. {N['jaren']} jaar terugverdiend ({sc[2]['jaren']} tot {sc[0]['jaren']} jaar){', zonder de kosten van installatie' if AA else ''}.

- **Nu:** u neemt {B.nl(a.afname)} kWh per jaar af en levert {B.nl(a.teruglevering)} kWh terug; van uw zonnestroom gebruikt u ca. {B.pct(zv_nu)} zelf.
- **Met batterij:** de batterij bewaart zonnestroom voor de avond en laadt op goedkope uren; u gebruikt dan ca. {B.pct(met_b['zelfverbruik'])} van uw zonnestroom zelf.""" + (f"""
- **De auto:** {a.auto_tekst or f'ca. {B.nl(a.auto_kwh)} kWh per jaar thuis laden'}. De batterij levert met de auto {B.eur(N['batt'])} per jaar op, zonder auto {B.eur(round(w_nu, -1))}.""" if auto else "") + f"""
""" + ("- **Installatie:** in deze prijs zitten de omvormer, de batterijmodules, de BDU en de installatieautomaat met aardlek; installatie en aansluiting worden apart afgesproken.\n"
         "- **Btw:** omvormer en batterij vallen onder 21%.\n" if AA else
         "- **Noodstroom:** met de handmatige omschakelaar draait het huis bij stroomuitval op batterij en panelen.\n"
         "- **Btw:** omvormer, batterij en installatie vallen onder 21%.\n") + f"""
""")

    t.append(f"""## Uw installatie nu

De woning heeft {a.bestaand_panelen} zonnepanelen op het platte dak, op frames naar het zuiden. Uit de meterstanden leidt Saldox af hoe groot de installatie is en hoeveel u zelf gebruikt.

| | Per jaar |
| --- | --- |
| Afname van het net (meter) | {B.nl(a.afname)} kWh |
| Teruglevering aan het net (meter) | {B.nl(a.teruglevering)} kWh |
| Opwek zonnepanelen ({'opgave' if a.opwek else 'berekend'}) | {B.nl(round(nu['pv_kwh'], -1))} kWh |
| Totaal verbruik van het huis (afname + eigen zonnestroom) | {B.nl(a.verbruik)} kWh |
| Zonnestroom zelf gebruikt | {B.pct(zv_nu)} |
""" + (f"| Auto, thuis laden (nieuw) | {B.nl(a.auto_kwh)} kWh |\n" if auto else "") + f"""
- **Panelen:** {a.bestaand_panelen} panelen van ca. {a.bestaand_wp} Wp ({B.nl(kwp, 1)} kWp), {B.nl(a.opbrengst)} kWh per kWp.
- **Weinig verbruik overdag:** u gebruikt maar {B.pct(zv_nu)} van uw zonnestroom zelf. Saldox heeft het verbruiksprofiel daarop afgestemd: op werkdagen tussen 9 en 17 uur is het verbruik ca. {B.pct(a.dagfactor)} van een standaard huishouden. Daarmee komt de simulatie per uur uit op {B.nl(round(nu['import_kwh'], -1))} kWh afname en {B.nl(round(nu['export_kwh'], -1))} kWh teruglevering, gelijk aan uw meterstanden.
- **Juist dan helpt een batterij:** de zonnestroom die overdag terug het net op gaat, gebruikt u 's avonds alsnog zelf.
- **Bij de schouw:** typeplaatje van panelen en omvormer bekijken; de exacte paneelgegevens maken de berekening definitief.
- **Bestaande omvormer:** die gaat eruit; de panelen komen op de nieuwe hybride omvormer.
""")

    rows = "\n".join(f"| {p} | {B.eur2(ex)} | {int(b * 100)}% | {B.eur2(inc)} | {st} |" for p, ex, b, st, inc in regels)
    t.append(f"""## Begroting

Het pakket kost {B.eur2(inv_ex)} excl. btw en {B.eur2(inv)} incl. btw, {excl}.

| Post | Excl. btw | Btw | Incl. btw | Status |
| --- | --- | --- | --- | --- |
{rows}
| **Totaal** | **{B.eur2(inv_ex)}** | | **{B.eur2(inv)}** | |

- **Btw 21%:** de omvormer komt er voor de batterij en valt daarom, net als de batterij{'' if AA else ' en de installatie'}, onder 21%.
""" + ("- **Niet in de prijs:** het demonteren van de oude omvormer, het plaatsen en aansluiten van omvormer en batterij, het aanleggen van de groep in de meterkast, "
         "overspanningsbeveiliging, een omschakelaar voor noodstroom, de EMS-koppeling en transport. Die worden na de schouw apart afgesproken.\n" if AA else
         f"- **Bedrading op uurbasis:** het trekken van de AC- en DC-kabels zit niet in de prijs; Saldox rekent dit werk af op uurbasis, à {B.eur2(B.UURTARIEF_BEDRADING)} per uur excl. btw.\n") + f"""- **Stelposten** zijn inschattingen; bij de schouw worden ze definitief.
- **Aansluiting:** de {H['naam']} is 3-fase; de woning heeft een 3-fase aansluiting nodig (3x25 A). Is de meterkast vol, dan is een uitbreiding van de groepenkast nodig (niet in de prijs).
""")

    t.append(f"""## Wat het per jaar oplevert

Normaal levert de batterij {B.eur(N['bruto'])} per jaar op; na de reservering voor de omvormer blijft {B.eur(N['netto'])} over.

| Per jaar | Pessimistisch | Normaal | Optimistisch |
| --- | --- | --- | --- |
| Batterij (eigen zonnestroom, slim laden en ontladen{', laden van de auto' if auto else ''}) | {B.eur(sc[0]['batt'])} | {B.eur(sc[1]['batt'])} | {B.eur(sc[2]['batt'])} |
| **Bruto per jaar** | **{B.eur(sc[0]['bruto'])}** | **{B.eur(sc[1]['bruto'])}** | **{B.eur(sc[2]['bruto'])}** |
| Reservering vervanging omvormer | −{B.eur(RES)} | −{B.eur(RES)} | −{B.eur(RES)} |
| **Netto per jaar** | **{B.eur(sc[0]['netto'])}** | **{B.eur(sc[1]['netto'])}** | **{B.eur(sc[2]['netto'])}** |

- **Alleen de batterij telt:** de besparing van de bestaande panelen had u al; die staat hier niet in.
- **Pessimistisch / optimistisch:** batterij ×0,7 / ×1,3; in 2026 waren de prijsverschillen binnen een dag ca. 33% groter dan in 2025.""" + (f"""
- **Zonder auto:** dan levert de batterij normaal netto {B.eur(nu_netto)} per jaar op ({B.jr(inv, nu_netto)} jaar).""" if auto else "") + f"""
- **Hoe dit is berekend:** Saldox simuleert elk uur van een jaar met de echte uurprijzen van 2025 (EPEX day-ahead Nederland) en het zonneprofiel van Nederland. Het EMS zet de batterij in met de day-ahead prijzen; de auto laadt {'op werkdagen ' if a.auto_laaddagen == 5 else ''}op de goedkoopste uren dat hij thuis is.
""")

    t.append(f"""## Terugverdientijd

Het pakket van {B.eur2(inv)}{' (zonder installatie)' if AA else ''} is normaal in ca. {N['jaren']} jaar terugverdiend; pessimistisch in {sc[0]['jaren']} jaar en optimistisch in {sc[2]['jaren']} jaar.

<!-- FIG:kasstroom -->

| Onderdeel | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd (normaal) |
| --- | --- | --- | --- |
| Omvormer, batterij en installatie | {B.eur2(inv)} | {B.eur(N['netto'])} | {N['jaren']} jaar |
| **Totaal** | **{B.eur2(inv)}** | **{B.eur(N['netto'])}** | **{N['jaren']} jaar** |
""")

    rij = lambda x: (f"| {'**' if x['huidig'] else ''}{round(x['kwh'] / 5) * 5} kWh ({x['mod']}× BTS 5K){' (deze offerte)**' if x['huidig'] else ''} | "
                     f"{B.eur2(x['inv'])} | {B.eur(x['netto'])} | {x['jaren']} jaar | {B.eur(x['winst'])} | {B.pct(x['zv'])} |")
    beste = max(maten, key=lambda x: x["winst"])
    t.append(f"""## Batterijgrootte

Met dezelfde omvormer kan de batterij kleiner of groter. Per grootte, {'met de auto erbij, ' if auto else ''}normaal scenario:

| Batterij | Prijs incl. btw | Netto per jaar | Terugverdiend in | Opbrengst na 15 jaar | Zonnestroom zelf gebruikt |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(rij(x) for x in maten)}

- **Na 15 jaar** levert {round(beste['kwh'] / 5) * 5} kWh het meeste op.
- **Uitbreiden kan later:** de {H['naam']} heeft twee batterij-ingangen; tot 4 modules per toren, maximaal 2 torens.
- **Vermogen:** laden en ontladen tot ca. {B.nl(kw, 1)} kW met {a.modules} modules (25 A per batterij-ingang).
""")
    if lp_tekst:
        t.append(lp_tekst.strip() + "\n")
    t.append(f"""## Stroomcontract en prijzen

De batterij verdient vooral met een dynamisch contract: dan laadt hij op goedkope uren en levert hij op dure uren.

| Per jaar, normaal scenario | Dynamisch{' (advies)' if N['netto'] >= vast_netto else ''} | Vast{' (advies)' if vast_netto > N['netto'] else ''} |
| --- | --- | --- |
| Batterij per jaar | {B.eur(N['batt'])} | {B.eur(round(w_vast, -1))} |
| Netto per jaar | {B.eur(N['netto'])} | {B.eur(vast_netto)} |
| Terugverdientijd | {N['jaren']} jaar | {B.jr(inv, vast_netto) if vast_netto > 0 else 'n.v.t.'} jaar |

- **Einde saldering per 1 januari 2027:** daarna levert teruggeleverde stroom alleen de uurprijs op. Juist dan is een batterij het meest waard.
- **Prijzen 2027:** door de oorlog met Iran ligt de groothandelsprijs voor stroom in 2027 ca. 15% hoger dan in 2026; grotere prijsverschillen maken de batterij meer waard.
""")
    t.append(f"""## Met en zonder saldering

Tot 1 januari 2027 mag u teruggeleverde stroom wegstrepen tegen afgenomen stroom. Zolang dat kan, levert de batterij minder op; dit plan rekent met de situatie vanaf 2027.

| Dynamisch contract, normaal scenario | Met saldering (tot 2027) | Zonder saldering (vanaf 2027) |
| --- | --- | --- |
| Batterij per jaar | {B.eur(round(w_sal, -1))} | {B.eur(N['batt'])} |
| Jaarlijkse kosten | −{B.eur(RES)} | −{B.eur(RES)} |
| **Netto per jaar** | **{B.eur(sal_netto)}** | **{B.eur(N['netto'])}** |
| Terugverdientijd | {B.jr(inv, sal_netto) if sal_netto > 0 else 'n.v.t.'} jaar | {N['jaren']} jaar |

- **Wat saldering doet:** met saldering is een teruggeleverde kWh evenveel waard als een afgenomen kWh; de batterij wint dan alleen nog door prijsverschillen.
""")
    t.append(f"""## Installatie en veiligheid

De installatie is in één tot twee dagen klaar; de batterij hoort op een droge, vorstvrije plek met ruimte voor ventilatie.

- **{H['naam']}:** 3-fase hybride omvormer, {H['kw']} kW, twee MPPT's en twee batterij-ingangen voor Sofar BTS 5K. Het EMS van Saldox stuurt hem op de uurprijs.
- **Sofar BTS 5K ({a.modules}×):** LFP-batterij, 5,12 kWh per module, samen {B.nl(a.modules * 5.12, 2)} kWh, bruikbaar ca. {B.nl(a.modules * 5.12 * 0.9, 1)} kWh. Garantie 10 jaar: 70% capaciteit na 10 jaar.
""" + ("- **Noodstroom:** de omvormer heeft een noodstroomuitgang; met een omschakelaar in de meterkast (niet in deze prijs) draait het huis bij stroomuitval op batterij en panelen.\n" if AA else
         "- **Noodstroom:** bij stroomuitval zet u de handmatige omschakelaar om; het huis, of de groepen op de noodstroom, draait dan op batterij en panelen.\n") + f"""
- **Veiligheid:** de installatie voldoet aan NEN 1010. Meld de batterij bij de opstalverzekeraar en de netbeheerder (energieleveren.nl).
""")
    t.append(f"""## Planning

Van akkoord tot werkend systeem duurt het ca. 4 tot 6 weken.

| Week | Wat |
| --- | --- |
| 1 | Schouw: meterkast, plek batterij, bestaande panelen en omvormer, kabelroute |
| 2 tot 3 | Bestellen en leveren; dynamisch contract regelen |
| 4 | Installatie omvormer, batterij en omschakelaar (1 tot 2 dagen) |
| 4 tot 5 | Aanmelden energieleveren.nl, EMS koppelen, oplevering en uitleg |
""")
    t.append(f"""## Aannames en te bevestigen

De cijfers gaan uit van de meterstanden en de aannames hieronder.

**Te bevestigen bij de klant**

- [ ] Typeplaatje panelen en omvormer (aantal, Wp, bouwjaar)
- [ ] 3-fase aansluiting (3x25 A) en ruimte in de meterkast
- [ ] Plek voor de batterij: droog, vorstvrij, bereikbaar
- [ ] Kabelroute dak–omvormer–meterkast (bedrading op uurbasis)
- [ ] Stroomcontract: dynamisch voor afname en teruglevering""" + ("""
- [ ] Laadgedrag van de auto en laadpaal""" if auto else "") + f"""

**Aannames**

- Verbruik {B.nl(a.verbruik)} kWh per jaar (afname {B.nl(a.afname)} kWh plus eigen zonnestroom); overdag op werkdagen {B.pct(a.dagfactor)} van een standaardprofiel""" + (f"""; auto {B.nl(a.auto_kwh)} kWh per jaar""" if auto else "") + f"""
- Panelen {B.nl(kwp, 1)} kWp, {B.nl(a.opbrengst)} kWh per kWp ({a.opbrengst_bron or 'PVGIS'})
- Batterij {B.nl(a.modules * 5.12 * 0.9, 1)} kWh bruikbaar, {B.nl(kw, 1)} kW, rendement 90% heen en terug
- Reservering vervanging omvormer €{RES} per jaar
""")
    if a.sectie_eind:
        t.append(Path(a.sectie_eind).read_text(encoding="utf-8").strip() + "\n")
    src = "\n".join(t)

    koppen = {"Samenvatting": "Wat het kost, en wat het u oplevert.",
              "Uw installatie nu": "Uw panelen, uit de meterstanden afgeleid.",
              "Begroting": "Elke post op een rij.",
              "Wat het per jaar oplevert": "Uur voor uur doorgerekend.",
              "Terugverdientijd": "Wanneer de batterij zich heeft terugverdiend.",
              "Batterijgrootte": "Kleiner of groter kan ook.",
              "Wist u dat? Laden met de Zaptec Go 2": "Thuis laden levert ERE-vergoeding op.",
              "Stroomcontract en prijzen": "Dynamisch laat de batterij verdienen.",
              "Met en zonder saldering": "Vanaf 2027 telt elke eigen kWh zwaarder.",
              "Installatie en veiligheid": "Eén installatie, klaar voor noodstroom.",
              "Planning": "Binnen anderhalve maand werkend.",
              "Aannames en te bevestigen": "Wat we bij u thuis nog bevestigen."}
    koppen.update(dict(k.split("=", 1) for k in a.kop))
    figs = {"kasstroom": charts.kasstroom(inv, [("Pessimistisch", sc[0]["netto"], sc[0]["jaren"], False),
                                                ("Normaal", N["netto"], N["jaren"], True),
                                                ("Optimistisch", sc[2]["netto"], sc[2]["jaren"], False)],
                                          horizon=15, titel=f"Normaal is de batterij na ca. {N['jaren']} jaar terugverdiend")}
    for f in a.figuur:
        naam, rest = f.split("=", 1)
        pad, eyebrow, titel_f, sub = (rest.split("|") + ["", "", ""])[:4]
        figs[naam] = O.eigen_figuur(Path(pad), eyebrow, titel_f, sub)

    map_ = O.UIT / f"{a.datum}-{O.slug(a.klant)}"
    map_.mkdir(parents=True, exist_ok=True)
    (map_ / "energieplan-huishouden-offerte.md").write_text(src, encoding="utf-8")
    kpis = [(B.eur2(inv), "omvormer en batterij incl. btw, excl. installatie" if AA else "investering incl. btw, excl. bedrading op uurbasis", False),
            (f"ca. {N['jaren']} jaar", "terugverdientijd, normaal scenario", True),
            (B.eur(N["netto"]), "netto per jaar (normaal)", False),
            (B.pct(met_b["zelfverbruik"]), "zonnestroom zelf gebruikt met batterij", False)]
    html = map_ / "offerte.html"
    titel = bouw(src, koppen, figs, kpis, f"Energieplan · thuisbatterij {round(a.modules * 5.12)} kWh bij bestaande zonnepanelen", html)
    subprocess.run(["node", str(HERE / "render_pdf.js"), str(html), str(map_ / "offerte.pdf"), titel], check=True,
                   stdout=subprocess.DEVNULL)
    uit = {"offerte": dict(inv=inv, inv_ex=inv_ex, netto=[s["netto"] for s in sc], jaren=[s["jaren"] for s in sc],
                           profiel=vars(a), meter_model=dict(afname=round(nu["import_kwh"]), teruglevering=round(nu["export_kwh"])))}
    (map_ / "uitkomsten.json").write_text(json.dumps(uit, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Batterij {a.modules * 5.12:.2f} kWh · {B.eur2(inv)} incl. btw · netto {B.eur(N['netto'])}/jaar · {N['jaren']} jaar · "
          f"zonder auto {B.eur(nu_netto)} · met saldering {B.eur(sal_netto)} · map {map_}")
    for x in maten:
        print(f"  {x['mod']} modules: {B.eur2(x['inv'])} netto {B.eur(x['netto'])} {x['jaren']} jr winst15 {B.eur(x['winst'])}")


if __name__ == "__main__":
    main()
