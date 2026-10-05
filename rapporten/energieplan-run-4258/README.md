# Energieplan Run 4258, Veldhoven

Rapport in Saldox-huisstijl, gebouwd uit `energieplan-run-4258.md` (bron) en `CLAUDE.md` (opdracht en grafiekdata).

| Bestand | Wat |
|---|---|
| `rapport.html` | Zelfstandige pagina (lettertype ingebed, geen externe bestanden), met hover op de grafieken |
| `rapport.pdf` | A4-export |
| `review-bevindingen.md` | Inconsistenties, kritische aannames en ontbrekende posten |
| `build.py`, `charts.py`, `template.html` | Generator: markdown → HTML, SVG-grafieken, huisstijl |
| `render_pdf.js` | PDF-export via Playwright/Chromium |
| `check.py` | Controle: tabellen letterlijk overgenomen, alle totalen en grafiekdata kloppen |

Opnieuw bouwen (vereist `pip install markdown` en Playwright):

```sh
python3 build.py && node render_pdf.js && python3 check.py
```
