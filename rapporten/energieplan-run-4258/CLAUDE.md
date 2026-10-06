# Energieplan Run 4258, Veldhoven — instructies voor Claude Code

## Wat er in deze map staat

- `energieplan-run-4258.md` — het volledige rapport (bron van alle tekst, tabellen en cijfers).
- `CLAUDE.md` — dit bestand: opdracht, stijl en de data voor de twee grafieken die in de markdown als `<!-- GRAFIEK -->` en `<!-- DIAGRAM -->` zijn gemarkeerd.

## Opdracht

1. **Stijl ophalen van saldox.nl.** De site rendert met JavaScript, dus gewone HTTP-fetch geeft alleen de titel. Open de site met een headless browser (bijvoorbeeld Playwright), maak screenshots van de homepage en een paar subpagina's en lees de berekende stijlen uit: kleuren, lettertypes (font-family, gewichten), koppen, knoppen, kaarten, witruimte en tone of voice.
   - Wat al bekend is: titel "Saldox — Energieneutraal wonen, ook na de saldering", themakleur `#0f7a3e` (donkergroen).
2. **Rapport bouwen in Saldox-huisstijl** als één zelfstandige HTML-pagina (`rapport.html`) en een PDF-export (`rapport.pdf`, A4).
   - Gebruik de tekst en tabellen uit `energieplan-run-4258.md` letterlijk; verander geen bedragen.
   - Teken Grafiek 1 en Diagram 2 opnieuw met de data hieronder.
   - Pas de schrijfstijl aan de toon van saldox.nl aan, maar houd de cijfers en de inhoud gelijk.
   - **Saldox is de adviserende partij.** Schrijf vanuit Saldox als adviseur. Geen voorbehouden of disclaimers die afstand nemen van het advies, zoals "niet door Saldox gecontroleerd" of "volgens opgave van de opdrachtgever". Prijzen die de klant aanlevert (airco's, panelen, batterij, omvormer) worden niet ter discussie gesteld.
3. **Controleer** na het bouwen of alle totalen in de tabellen nog optellen (zie "Controletotalen").

## Grafiek 1 — netto cumulatieve kasstroom (scenario's)

- Titel: "Normaal is het pakket na ca. 6,6 jaar terugverdiend"
- Lijngrafiek, x-as 0 t/m 15 jaar, y-as in euro.
- Formule per scenario: `kasstroom(jaar) = -investering + netto_per_jaar × jaar`
- Investering: **€43.487,20** (airco's €17.987,20: 7 sets à €2.569,60 all-in)
- Netto per jaar (na jaarlijkse kosten):
  - Pessimistisch: €3.631 → terugverdiend na 12,0 jaar
  - Normaal: €6.563 → terugverdiend na 6,6 jaar (accentkleur)
  - Optimistisch: €9.673 → terugverdiend na 4,5 jaar
  - (herberekend oktober 2026: stroom €0,21, ERE €0,10–0,13, dynamisch contract met teruglevering tegen de uurprijs; zie `model.py`)
- Markeer de nullijn ("Terugverdiend") en het snijpunt per scenario met het aantal jaren.

## Diagram 2 — planning (week 1 t/m 14 + turbinespoor)

| Fase | Periode | Inhoud |
|---|---|---|
| Voorbereiding | Week 1 tot 4 | Dakinspectie, Enexis, offertes, btw en EIA, huurcontracten |
| Bestellen en leveren | Week 5 tot 8 | Bestellen en leveren, software EMS en app bouwen |
| Installatie energie | Week 9 tot 11 | Panelen, omvormer, batterij, laadpalen, meters, sensoren |
| Airco vervangen | Week 12 tot 13 | Per verdieping, inclusief verticaal transport en afvoer |
| Oplevering | Week 14 | Inspectie installatie, test EMS en app, Enexis-meter |
| Windturbine (optie, apart spoor) | Maand 6 tot 12 | Alleen na positieve windmeting en vergunning |

## Controletotalen

- Begroting basis: €43.487,20 excl. btw (incl. 21% btw: €52.619,51)
- Met beide opties (grote ruimte airco's €6.780,40 + windturbine €25.000): €75.267,60
- Per maatregel optellen tot €43.487,20: zonnepanelen €11.300 + smart control €2.100 + laadpalen €4.000 + batterij €4.000 + airco's €17.987,20 + meten per unit €3.350 + inspectie €750
- Netto per jaar per maatregel telt op tot €3.631 / €6.563 / €9.673
