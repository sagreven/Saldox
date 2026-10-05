#!/usr/bin/env python3
"""Rekenmodel achter de scenario's van het energieplan.

Met de oorspronkelijke aannames (stroom €0,25, ERE €0,07–0,10) reproduceert dit
model de getallen uit de eerste versie van het rapport; daarmee is de rekenwijze
gecontroleerd. De actuele aannames (oktober 2026) staan in ACTUEEL.

Bronnen actuele aannames:
- Stroom: CBS 85592NED (variabel leveringstarief aug 2026 €0,121 excl. btw) plus
  energiebelasting 2026 (€0,09161 tot 10.000 kWh, €0,06671 daarboven): bij
  36.000 kWh gemiddeld ca. €0,20–0,21 excl. btw.
- ERE: netto-uitbetaling inboekdienstverleners juli 2026 ca. €0,12–0,13 per
  geladen kWh (Joulo, Laadloon, Zeres via keuze.nl); bandbreedte €0,10–0,13.
"""
from dataclasses import dataclass

INVESTERING = 48987.80


@dataclass
class Aannames:
    stroom: float          # €/kWh excl. btw
    ere_lo: float          # €/kWh geladen
    ere_hi: float
    teruglever: tuple = (0.08, 0.08, 0.08)  # €/kWh teruggeleverd (pess, norm, opt)
    gas: float = 1.00      # €/m³
    batterij: tuple = (600, 1000, 1500)     # €/jaar; arbitrage op een dynamisch contract


OORSPRONKELIJK = Aannames(stroom=0.25, ere_lo=0.07, ere_hi=0.10)
# Hoofdscenario = dynamisch/dynamisch: teruglevering tegen de uurprijs. Gemiddelde
# prijs tijdens zonne-opwek NL (EPEX day-ahead via energy-charts): 2025 €53/MWh,
# 2026 jan-sep €65/MWh; min opslag leverancier en omdat het eigen overschot op de
# zonnigste uren valt: €0,03 / 0,04 / 0,05 per kWh.
TERUG_DYN = (0.03, 0.04, 0.05)
ACTUEEL = Aannames(stroom=0.21, ere_lo=0.10, ere_hi=0.13, teruglever=TERUG_DYN)

# Batterij zonder prijsverschil: alleen zonne-overschot opslaan i.p.v. terugleveren.
# 60 / 75 / 90% van het overschot (2.475 kWh), rendement 90%.
OPSLAG_AANDEEL = (0.60, 0.75, 0.90)


def batterij_zonder_arbitrage(stroom, teruglever):
    surplus = 16500 * (1 - 0.85)
    return tuple(r(surplus * a * (0.9 * stroom - t), 10) for a, t in zip(OPSLAG_AANDEEL, teruglever))

# vaste invoer uit het rapport
OPWEK, DIRECT = 16500, 0.85                 # kWh/jaar, aandeel direct verbruik
VERBRUIK = 36000
GAS_M3_BESPAARD, AIRCO_EXTRA_KWH = 2000, 5000
KOEL_KWH = 4000
BATTERIJ = (600, 1000, 1500)                # dynamisch/dynamisch: prijsverschil-gedreven
KOSTEN = {                                   # jaarlijkse kosten (pess, norm, opt)
    "airco": (1500, 1200, 1000), "zon_batt": (300, 200, 150), "verzekering": (400, 300, 200),
    "backoffice": (480, 360, 240), "software": (300, 300, 300), "reservering": (550, 550, 550),
}
# toedeling zon/batterij-kosten per maatregel (uit de eerste versie): zon-deel, rest batterij
ZON_KOSTEN = (650, 550, 475)
BATT_KOSTEN = (600, 500, 425)
KWH_LAAD = {3: 7800, 4: 10400}              # 25 kWh × 2 palen × dagen × 52
LAAD_INVEST = 4000
EMS_VERW, EMS_KOEL = (0.10, 0.15, 0.20), (0.15, 0.25, 0.35)
SENS = (0.05, 0.10, 0.15)


def r(x, n=1):
    return int(round(x / n) * n)


def bereken(a: Aannames):
    zon_basis = OPWEK * DIRECT * a.stroom + OPWEK * (1 - DIRECT) * 0.08  # schaal met vaste teruglevering; correctie hieronder
    zon_basis_oud = OPWEK * DIRECT * 0.25 + OPWEK * (1 - DIRECT) * 0.08
    f = zon_basis / zon_basis_oud
    zon = tuple(v if a is OORSPRONKELIJK else r(v * f - OPWEK * (1 - DIRECT) * (0.08 - t), 10)
                for v, t in zip((3500, 3650, 3800), a.teruglever))

    stroombesp = 0.10 * VERBRUIK * a.stroom
    gasnetto = GAS_M3_BESPAARD * a.gas - AIRCO_EXTRA_KWH * a.stroom
    airco_n = stroombesp + gasnetto
    airco = (r(airco_n * 2 / 3, 10), r(airco_n, 10), r(airco_n * 4 / 3, 10))

    verw = GAS_M3_BESPAARD * a.gas + AIRCO_EXTRA_KWH * a.stroom
    koel = KOEL_KWH * a.stroom
    ems_v = tuple(r(verw * p, 5) for p in EMS_VERW)
    ems_k = tuple(r(koel * p, 5) for p in EMS_KOEL)
    ems = tuple(v + k for v, k in zip(ems_v, ems_k))
    sens = tuple(r((verw + koel - e) * p, 5) for e, p in zip(ems, SENS))

    def laad(tarief, dagen):
        kwh = KWH_LAAD[dagen]
        marge = round(kwh * (tarief - a.stroom))
        e_lo, e_hi = round(kwh * a.ere_lo), round(kwh * a.ere_hi)
        return kwh, marge, e_lo, e_hi, marge + e_lo, marge + e_hi
    laadplan = {(t, d): laad(t, d) for t in (0.39, 0.49) for d in (3, 4)}
    lp_pess = round(0.9 * laadplan[(0.39, 3)][4])
    lp_norm = round(0.9 * (laadplan[(0.49, 3)][4] + laadplan[(0.49, 3)][5]) / 2)
    lp_opt = round(0.9 * laadplan[(0.49, 4)][5])
    laadpalen = (lp_pess, lp_norm, lp_opt)

    bruto = tuple(sum(x) for x in zip(zon, a.batterij, airco, ems, sens, laadpalen))
    kosten = tuple(sum(k[i] for k in KOSTEN.values()) for i in range(3))
    netto = tuple(b - k for b, k in zip(bruto, kosten))

    per = {
        "zon": tuple(z - k for z, k in zip(zon, ZON_KOSTEN)),
        "smart": tuple(e + s - 300 for e, s in zip(ems, sens)),
        "laad": tuple(l - b for l, b in zip(laadpalen, KOSTEN["backoffice"])),
        "batt": tuple(b - k for b, k in zip(a.batterij, BATT_KOSTEN)),
        "airco": tuple(a_ - k for a_, k in zip(airco, KOSTEN["airco"])),
    }
    return dict(batterij=a.batterij, zon=zon, airco=airco, airco_stroom=stroombesp, airco_gas=gasnetto, verw=verw, koel=koel,
                ems_v=ems_v, ems_k=ems_k, ems=ems, sens=sens, laadplan=laadplan, laadpalen=laadpalen,
                bruto=bruto, kosten=kosten, netto=netto, per=per)


def varianten():
    """Stroomcontract nu → straks. Wat de investering oplevert hangt af van het contract
    straks; 'vast → dynamisch' rekent als dynamisch (het overstapeffect zelf telt niet mee)."""
    vast_terug = (0.08, 0.08, 0.08)
    v = {
        "vast/vast": Aannames(0.21, 0.10, 0.13, vast_terug, batterij=batterij_zonder_arbitrage(0.21, vast_terug)),
        "vast/dynamisch": ACTUEEL,
        "dynamisch/dynamisch": ACTUEEL,
    }
    return {k: bereken(a) for k, a in v.items()}


def jaren(inv, netto):
    return "niet" if netto <= 0 else f"{inv / netto:.1f}".replace(".", ",")


if __name__ == "__main__":
    oud = bereken(OORSPRONKELIJK)
    assert oud["netto"] == (3809, 6762, 9732), oud["netto"]
    assert oud["bruto"] == (7339, 9672, 12172), oud["bruto"]
    assert oud["ems"] == (475, 740, 1000) and oud["sens"] == (190, 350, 490)
    assert oud["airco"] == (1100, 1650, 2200) and oud["laadpalen"] == (1474, 2282, 3182)
    print("Model reproduceert de oorspronkelijke getallen.\n")
    m = bereken(ACTUEEL)
    for k, v in m.items():
        print(f"{k:13} {v}")
    print("terugverdientijd", [jaren(INVESTERING, n) for n in m["netto"]])
    print()
    for k, v in varianten().items():
        print(f"{k:20} zon {v['zon']} batterij {v['batterij']} batt-netto {v['per']['batt']} netto {v['netto']} "
              f"jaren {[jaren(INVESTERING, n) for n in v['netto']]}")
