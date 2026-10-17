# Gridfinity-draagsysteem: overpakken zonder ompakken

**Het probleem:** schroevendraaiers en schroeven liggen los in een grote
Packout-koffer. Ga je met de motor, dan moet alles één voor één de rugzak in, en
daarna weer terug.

**Het idee:** je pakt geen spullen meer over, maar **dichte cassettes**. Elke
cassette is een plat doosje met deksel, scharnier en twee klikbeugels, met
binnenin een Gridfinity-bodem. In de werkplaats en in de Packout staan de
cassettes naast elkaar. Ga je met de motor, dan schuif je de cassettes die je
nodig hebt zó in de rugzak.

![open](img/open.png)
![dicht](img/dicht.png)

## Hoe het systeem werkt

```
 Werkplaats / Packout-koffer            Rugzak (motor)
┌───────────────────────────┐          ┌──────────────┐
│ [cassette A] [cassette B] │  ──────► │ [cassette A] │
│ [cassette C] [cassette D] │  pak de  │ [cassette C] │
└───────────────────────────┘ cassette └──────────────┘
        │                     niet de
        └─ binnenin: losse Gridfinity-bakjes (42 mm raster)
```

1. **Eén cassette per taak**, niet per soort spul. Bijvoorbeeld:
   - *Basis*: bitset, kleine schroevendraaiers, cutter, potlood, meetlint
   - *Bevestiging*: schroeven, pluggen en ringen in kleine bakjes
   - *Elektra*: lasklemmen, wago's, spanningzoeker, striptang
   - *Schroevendraaiers*: de volle lengtes, in een cassette met vlakke bodem
2. **De deksel klemt de bakjes vast.** De binnenhoogte is zo berekend dat de
   deksel net (0,4 mm) boven de bakjes sluit. Kantelt de cassette in je rugzak,
   dan kunnen schroeven niet van het ene vakje naar het andere: elk bakje is
   zelf ook dicht. Dat is het belangrijkste detail van het systeem.
3. **Binnen is het gewoon Gridfinity.** Bakjes uit je bestaande
   Gridfinity-verzameling passen erin, en je kunt de indeling later nog
   wijzigen.
4. **Plat en rechthoekig formaat (4×2).** Een 4×2-cassette is ca. 173 × 102 ×
   29 mm. Daarvan passen er meerdere naast elkaar in een gewone rugzak en in
   een Packout-koffer.

## Maten

| Variant | Buitenmaat (b × d × h) | Inhoud |
|---|---|---|
| `klein-4x2-h3` | 173 × 102 × 29 mm | 8 vakjes, bakjes 3u hoog (schroeven, bits) |
| `hoog-4x2-h6`  | 173 × 102 × 50 mm | 8 vakjes, bakjes 6u hoog (gereedschap) |
| `schroevendraaiers-5x2-vlak` | 215 × 102 × 36 mm | vlakke bodem voor schuim/TPU-inleg, schroevendraaiers tot ~210 mm |

De diepte is inclusief scharnier en klikbeugels; de romp zelf is 89 mm diep.

**Meet eerst je Packout-koffer** (binnenmaat, en de hoogte tot de deksel), en
kies daarna `gx`, `gy` en `hu`. Elke eenheid in `gx`/`gy` voegt 42 mm toe en
elke eenheid in `hu` 7 mm.

## Printen

Kant-en-klare STL's staan in [`stl/`](stl/). Body en deksel zijn twee aparte
prints:

- **Materiaal:** PETG (aanbevolen voor de klikbeugels; PLA wordt na een tijdje
  bros en kan in een warme koffer/zon vervormen).
- **Body** rechtop, **deksel** met de bovenkant op het bed (de STL is al zo
  georiënteerd). Geen support nodig.
- 3 wanden, 15–20 % infill.
- **Scharnierpen:** schuif een stuk 1,75 mm filament door de knokkels en smelt
  of knip de uiteinden iets dikker, zodat de pen er niet uitglijdt.
- Druk de deksel dicht: de veerbeugels klikken achter de nok. Openen doe je
  door aan het randje onderaan de beugel naar buiten te trekken.

## Zelf aanpassen

Het model is parametrisch ([`cassette.scad`](cassette.scad), OpenSCAD):

```sh
openscad -D gx=3 -D gy=2 -D hu=4 -D 'part="body"' -o body.stl cassette.scad
openscad -D gx=3 -D gy=2 -D hu=4 -D 'part="lid"'  -o lid.stl  cassette.scad
```

| Parameter | Betekenis |
|---|---|
| `gx`, `gy` | aantal Gridfinity-vakjes (42 mm) in breedte en diepte |
| `hu` | hoogte van de bakjes erin (eenheden van 7 mm) |
| `bin_lip` | stapelrand van je bakjes; **meet een bakje na** en zet dit op 0 als je bakjes zonder rand print |
| `lid_gap` | speling tussen bakje en deksel: kleiner = vaster |
| `baseplate` | `false` = vlakke bodem voor een schuim- of TPU-inleg |
| `part` | `body`, `lid`, `both` (printlay-out) of `assembled` (preview) |

## Tips voor de bakjes erin

- **Schroeven:** print de bakjes *zonder* stapelrand (`bin_lip = 0`). De deksel
  sluit dan vlak over alle vakjes, en er kan niets tussen de vakjes door.
- **Bits en kleine schroevendraaiers:** gebruik een Gridfinity-bithouder of een
  bakje met uitsparingen (genoeg ontwerpen op Printables/MakerWorld, zoek op
  "gridfinity bit holder" of "gridfinity screwdriver").
- **Schroevendraaiers:** gebruik de vlakke variant met een inleg van Kaizen-schuim
  of een TPU-bed met uitsparingen, zodat niets rammelt.
- **Label op de deksel:** plak een label op de voorkant of de deksel, zodat je
  in de Packout meteen ziet welke cassette je moet pakken.

## Nog niet getest

Het model is gerenderd en gecontroleerd op geldige (manifold) geometrie, maar
nog niet geprint. Print eerst één `klein-4x2-h3` en controleer:

1. Klikken de beugels goed? Is het te stug, maak dan `latch_t` dunner. Gaan ze
   te makkelijk open, vergroot dan `ridge_d`.
2. Zit de tong strak in de groef? Pas dit aan met `fit`.
3. Klemt de deksel je eigen bakjes vast? Pas `bin_lip` / `lid_gap` aan.
