# Energieplan huishouden: template

Universeel energieadvies voor een standaard huishouden in Saldox-huisstijl:

| Variant | Pakket | Bestand |
|---|---|---|
| Met Zaptec Go 2 (eigen gebruik) | 10 panelen 450 Wp + Sofar BTS 10 kWh met ESI 10 kW hybride omvormer | `rapport-huishouden-met-zaptec-go2.pdf` |
| Zonder laadpaal | idem | `rapport-huishouden-zonder-laadpaal.pdf` |
| 8 panelen en Marstek | 8 panelen A Solar 460 Wp + 4 APsystems DS3 + Marstek Venus E 3.0 (5,12 kWh) | `rapport-huishouden-marstek-8-panelen.pdf` |

Alle varianten: EMS van Saldox, dynamisch contract. Inkoopprijzen komen uit `../prijzen/inkoopprijzen.json`.

## Hoe het werkt

- `model_huis.py`: simulatie per uur over een heel jaar met echte uurprijzen (EPEX day-ahead NL 2025) en het Nederlandse zonneprofiel (`data/nl_2025_uur.json`, Energy-Charts). De batterij wordt per uur optimaal ingezet (dynamisch programmeren), zoals een EMS op day-ahead prijzen doet.
- `build_huis.py`: rekent beide varianten door, schrijft de tekst (`energieplan-huishouden-*.md`) en bouwt HTML en PDF.
- `check_huis.py`: controleert optellingen, btw en terugverdientijden tegen `uitkomsten.json`.

## Aanpassen voor een klant

1. Prijzen: nieuwe inkoopprijzen in `../prijzen/inkoopprijzen.json` (en `.md`); posten per pakket in `PAKKETTEN`, laadpaal in `PRIJZEN_LAADPAAL` (`build_huis.py`). Een nieuw pakket of nieuwe variant: voeg een item toe aan `PAKKETTEN` en `VARIANTEN`.
2. Verbruik, opbrengst, batterij, tarieven: `AANNAMES` in `model_huis.py`.
3. EV-gebruik en scenario's: `EV_KWH`, `PUBLIEK`, `ERE`, `OPBRENGST`, `BATT_FACTOR` in `build_huis.py`.
4. Klantnaam en datum: `KLANT` in `build_huis.py`.

```sh
pip install markdown        # eenmalig; Playwright/Chromium voor de PDF
python3 build_huis.py && python3 check_huis.py
```
