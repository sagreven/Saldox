# Gridfinity-draagsysteem: overpakken zonder ompakken

**Het probleem:** schroevendraaiers en schroeven liggen los in een grote
Packout-koffer. Ga je met de motor, dan moet alles één voor één de rugzak in, en
daarna weer terug.

**Het idee:** de kleinste eenheid is een **stapelbaar bakje met schuifdeksel**.
Bakjes staan in **cassettes** (dichte doosjes met scharnier en klikbeugels,
binnenin een Gridfinity-raster). Je pakt de cassette over, of alleen de bakjes
die je nodig hebt: elk bakje is zelf al dicht.

![bakje met schuifdeksel](img/bakje.png)
![cassette met twee lagen bakjes, doorgesneden](img/stapel.png)
![cassette open](img/open.png)
![cassette dicht](img/dicht.png)

## Opbouw

```
 bakje (5u, 39,4 mm)          cassette, 1 of 2 lagen          Packout / rugzak
┌──────────────┐  schuif-    ┌──────────────────────┐
│ ▭▭▭▭▭▭▭▭▭▭▭▭ │◄─ deksel   │ [bakje][bakje] laag 2 │ ──► Large Tool Box
│  │    │    │ │             │ [bakje][bakje] laag 1 │ ──► rugzak
└──┴────┴────┴─┘             └──────────────────────┘ ──► low-profile organizer
   Gridfinity-voeten          binnen: Gridfinity 42 mm      (losse bakjes)
```

1. **Bakjes**, 5 hoogte-eenheden (39,4 mm). Die hoogte is gekozen op de
   **Packout low-profile organizer** (binnen ca. 46 mm), zodat dezelfde bakjes
   ook daarin passen.
2. **Schuifdeksel per bakje.** De deksel loopt in een groef vlak onder de
   stapelrand en rust op de tussenwanden, zodat elk vakje apart dicht is.
   Er zit geen klik op: de deksel schuift, en blijft door wrijving zitten. In de
   cassette houdt de wand ernaast hem op zijn plek. De groef is een
   zwaluwstaart met een plafond van 45°, zodat hij zonder support print.
3. **Stapelbaar.** De deksel zit onder de stapelrand, dus het bakje erboven valt
   gewoon met zijn Gridfinity-voeten in de rand. Gestapeld telt elk bakje 35 mm.
4. **Cassettes** hebben binnen een Gridfinity-raster (`gx` × `gy` vakken van
   42 mm) en zijn 1 of 2 lagen bakjes hoog. De deksel van de cassette klemt de
   bovenste laag vast.

## Maten

**Bakjes** (allemaal 5u, 39,4 mm hoog)

| Bestand | Vakken | Buitenmaat |
|---|---|---|
| `bakje-1x1` | 1 | 41,5 × 41,5 mm |
| `bakje-2x1-vakjes` / `-open` | 2 / 1 | 83,5 × 41,5 mm |
| `bakje-2x2-vakjes` / `-open` | 4 / 1 | 83,5 × 83,5 mm |
| `bakje-4x1-open` | 1 | 167,5 × 41,5 mm |

Bij elk formaat hoort `schuifdeksel-<formaat>.stl` (vakjes en open gebruiken
dezelfde deksel).

**Cassettes** (diepte inclusief scharnier en klikbeugels)

| Bestand | Binnen | Buitenmaat (b × d × h) |
|---|---|---|
| `cassette-4x2-1laag` | 4 × 2 vakken, 1 laag | 173 × 102 × 43 mm |
| `cassette-4x2-2lagen` | 4 × 2 vakken, 2 lagen | 173 × 102 × 78 mm |
| `cassette-5x2-schroevendraaiers` | vlakke bodem, 1 laag hoog | 215 × 102 × 43 mm |

**In de Packout** (winkelopgaven, niet officieel; meet je eigen koffer na)

| Koffer | Binnenmaat (ca.) | Wat past |
|---|---|---|
| Large Tool Box 48-22-8425 | 478–500 × 335–340 × 216–229 mm | per laag 6 cassettes 4×2 (2 naast, 3 achter elkaar); in de hoogte 2× 2-lagen + 1× 1-laag (199 mm) |
| Low-profile organizer 48-22-8431 | 457 × 305 × 46 mm | Gridfinity-bodem van 10 × 7 vakken, losse bakjes van 5u (39,4 mm) |

Voor de low-profile organizer haal je de originele bakjes eruit en leg je een
Gridfinity-baseplate in de bodem (bijvoorbeeld
[deze op MakerWorld](https://makerworld.com/en/models/1534482-gridfinity-base-for-packout-low-profile-organizer)).

## Printen

Kant-en-klare STL's staan in [`stl/`](stl/).

- **Materiaal:** PETG (aanbevolen voor de klikbeugels en het scharnier van de
  cassette; PLA wordt na een tijdje bros en kan in een warme koffer vervormen).
- **Bakjes** rechtop, **schuifdeksels** plat, **cassette-body** rechtop,
  **cassette-deksel** met de bovenkant op het bed (de STL's zijn al zo
  georiënteerd). Geen support nodig.
- 3 wanden, 15–20 % infill.
- **Steuntjes in de sleuf:** in de sleuf aan de voorkant van elk bakje staan
  twee hele dunne steuntjes, zodat de brug erboven kort blijft. Die drukt de
  deksel er de eerste keer uit; eventuele restjes haal je weg met een mesje.
- **Scharnierpen cassette:** schuif een stuk 1,75 mm filament door de knokkels
  en smelt of knip de uiteinden iets dikker.

## Zelf aanpassen

Alles is parametrisch (OpenSCAD). Gedeelde Gridfinity-vormen staan in
[`gridfinity.scad`](gridfinity.scad).

```sh
# bakje 3x1 met losse vakjes, en de bijbehorende deksel
openscad -D gx=3 -D gy=1 -D 'part="bakje"'  -o bakje-3x1.stl     bakje.scad
openscad -D gx=3 -D gy=1 -D 'part="deksel"' -o deksel-3x1.stl    bakje.scad
# cassette 3x2, twee lagen
openscad -D gx=3 -D gy=2 -D levels=2 -D 'part="body"' -o body.stl cassette.scad
openscad -D gx=3 -D gy=2 -D levels=2 -D 'part="lid"'  -o lid.stl  cassette.scad
```

**[`bakje.scad`](bakje.scad)**

| Parameter | Betekenis |
|---|---|
| `gx`, `gy` | grootte in vakken van 42 mm |
| `hu` | hoogte in eenheden van 7 mm (standaard 5, past in de low-profile organizer) |
| `vakken` | `per_vak` (elk 42 mm-vak apart) of `open` (één grote ruimte) |
| `deksel` | `false` = open bakje zonder groef |
| `lid_fit` | speling van de schuifdeksel in de groef, per kant (standaard 0,1: getest, strak) |
| `steunen` | aantal breekbare steuntjes in de sleuf aan de voorkant (0 = geen) |
| `klik` | `true` = klein nokje tegen vanzelf openschuiven (standaard uit) |
| `part` | `bakje`, `deksel`, `both` of `dicht` (preview) |

De deksel schuift er aan de rechterkant (+x) uit. Bij een bakje van 4×1 is dat
de korte kant.

**[`cassette.scad`](cassette.scad)**

| Parameter | Betekenis |
|---|---|
| `gx`, `gy` | binnenmaat in Gridfinity-vakken |
| `levels` | aantal lagen bakjes (1 of 2) |
| `bin_hu` | hoogte van één bakje (moet gelijk zijn aan `hu` in `bakje.scad`) |
| `lid_gap` | speling tussen bovenste bakje en deksel: kleiner = vaster |
| `baseplate` | `false` = vlakke bodem voor een schuim- of TPU-inleg |
| `part` | `body`, `lid`, `both` (printlay-out) of `assembled` (preview) |

## Nog niet getest

De modellen zijn gerenderd, gecontroleerd op geldige geometrie en in
doorsnede nagemeten (stapelen, deksel in de groef, scharnier, klikbeugels),
en de schuifdeksel van een 1×1-bakje is geprint en getest (speling 0,1 mm is
goed). Print nog één `cassette-4x2-1laag` en een paar bakjes, en controleer:

1. Valt een bakje goed op een ander bakje en in de cassette?
2. Klikken de beugels van de cassette goed? Te stug: maak `latch_t` dunner.
   Te los: vergroot `ridge_d`.
3. Past een bakje van 39,4 mm in jouw low-profile organizer met de
   Gridfinity-bodem erin?
