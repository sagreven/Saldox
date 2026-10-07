# Energieplan huishouden: template

Universeel energieadvies voor een standaard huishouden in Saldox-huisstijl, in twee varianten:

| Variant | Bestand |
|---|---|
| Zon, batterij en Zaptec Go 2 (eigen gebruik) | `rapport-huishouden-met-zaptec-go2.pdf` / `.html` |
| Zon en batterij, zonder laadpaal | `rapport-huishouden-zonder-laadpaal.pdf` / `.html` |

Pakket: 10 zonnepanelen à 450 Wp, Sofar BTS 10 kWh (2× BTS 5K) met 3-fase ESI 10 kW hybride omvormer, EMS van Saldox, dynamisch contract.

## Hoe het werkt

- `model_huis.py`: simulatie per uur over een heel jaar met echte uurprijzen (EPEX day-ahead NL 2025) en het Nederlandse zonneprofiel (`data/nl_2025_uur.json`, Energy-Charts). De batterij wordt per uur optimaal ingezet (dynamisch programmeren), zoals een EMS op day-ahead prijzen doet.
- `build_huis.py`: rekent beide varianten door, schrijft de tekst (`energieplan-huishouden-*.md`) en bouwt HTML en PDF.
- `check_huis.py`: controleert optellingen, btw en terugverdientijden tegen `uitkomsten.json`.

## Aanpassen voor een klant

1. Prijzen en posten: `PRIJZEN_BASIS` en `PRIJZEN_LAADPAAL` in `build_huis.py`.
2. Verbruik, opbrengst, batterij, tarieven: `AANNAMES` in `model_huis.py`.
3. EV-gebruik en scenario's: `EV_KWH`, `PUBLIEK`, `ERE`, `OPBRENGST`, `BATT_FACTOR` in `build_huis.py`.
4. Klantnaam en datum: `KLANT` in `build_huis.py`.

```sh
pip install markdown        # eenmalig; Playwright/Chromium voor de PDF
python3 build_huis.py && python3 check_huis.py
```
