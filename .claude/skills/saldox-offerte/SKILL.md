---
name: saldox-offerte
description: Maak een Saldox-offerte voor een huishouden uit een korte klantbeschrijving, bijvoorbeeld "PHEV dagelijks nodig, klein huishouden, plat dak, 10 panelen". Gebruik deze skill wanneer de gebruiker een klantprofiel geeft en een offerte, energieplan of advies voor een woning wil.
---

# Saldox-offerte uit een klantprofiel

De gebruiker staat vaak bij de klant en geeft een korte beschrijving. Zet die om naar argumenten voor
`rapporten/huishouden-template/offerte.py`, draai het script en stuur de PDF.

## 1. Beschrijving → argumenten

| Gezegd | Argument |
|---|---|
| klein huishouden, 1–2 personen, alleenstaand, stel | `--huishouden klein` (2.000 kWh) |
| gemiddeld, gezin met 1 kind, 3 personen | `--huishouden gemiddeld` (2.500 kWh) |
| groot gezin, 4+ personen | `--huishouden groot` (3.600 kWh) |
| een exact jaarverbruik ("verbruikt 3.200 kWh") | `--verbruik 3200` |
| PHEV, plug-in hybride, hybride die dagelijks laadt | `--auto phev` (2.000 kWh thuis) |
| elektrische auto, EV, Tesla, volledig elektrisch | `--auto ev` (3.000 kWh thuis) |
| bekende kilometers of laadhoeveelheid | `--auto-kwh <kWh>` (km × 0,20 kWh/km × deel thuis) |
| geen auto of geen laadpaal nodig | `--auto geen` (standaard) |
| plat dak | `--dak plat` (montage vast €250, ballastopstelling) |
| schuin dak, pannendak | `--dak schuin` (standaard) |
| aantal panelen | `--panelen N` |
| 1-fase aansluiting (1x35 A) | `--aansluiting 1-fase` (Sofar valt dan af) |
| 3-fase aansluiting | `--aansluiting 3-fase` |
| klant wil een specifieke batterij | `--batterij marstek` / `marstek2` / `sofar` (anders `auto`) |
| klantnaam en plaats | `--klant "…" --plaats "…"` |

Ontbreekt iets, neem dan de standaard en noem die aanname kort in je antwoord; vraag alleen door als het
aantal panelen of het type auto echt onduidelijk is.

## 2. Draaien

```sh
cd rapporten/huishouden-template
python3 offerte.py --klant "Fam. Jansen" --plaats "Veldhoven" --huishouden klein --auto phev --dak plat --panelen 10
python3 check_huis.py ../offertes/<datum>-<klant>
```

Het script rekent elk passend pakket door (Marstek Venus E 1×, 2×, Sofar 10 kWh; met Zaptec Go 2 als er een auto is)
en kiest het pakket met de hoogste opbrengst na 15 jaar. Uitvoer: `rapporten/offertes/<datum>-<klant>/offerte.pdf`.

## 3. Opleveren

- Stuur `offerte.pdf` naar de gebruiker en vat samen: gekozen pakket, investering incl. btw, netto per jaar,
  terugverdientijd, en kort waarom (de vergelijkingstabel in de sectie "Waarom dit pakket").
- Commit en push de offertemap.

## Regels

- Saldox is de adviserende partij: geen disclaimers die afstand nemen van het advies.
- Prijzen komen uit `rapporten/prijzen/inkoopprijzen.json`; nieuwe prijzen van de gebruiker eerst daar invoeren (zie
  `rapporten/huishouden-template/CLAUDE.md`). Pas nooit getallen in de gegenereerde tekst met de hand aan.
