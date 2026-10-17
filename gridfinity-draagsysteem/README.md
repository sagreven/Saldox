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
 bakje, half: 2,2 cm hoog      cassette                       Packout / rugzak
┌──────────────┐  schuif-    ┌──────────────────────┐
│ ▭▭▭▭▭▭▭▭▭▭▭▭ │◄─ deksel   │ [bakje][bakje]       │ ──► Large Tool Box
│  │    │    │ │             │ [bakje][bakje]       │ ──► rugzak
└──┴────┴────┴─┘             └──────────────────────┘ ──► low-profile organizer
   Gridfinity-voeten          binnen: Gridfinity 4,2 cm     (losse bakjes)
```

1. **Basis is het halve bakje:** 2,2 cm hoog, gestapeld telt het 1,75 cm.
   Twee halve zijn even hoog als één heel bakje (3,9 cm). Een heel bakje past
   precies in de **Packout low-profile organizer** (binnen ca. 4,6 cm), en
   twee halve dus ook.
2. **Schuifdeksel per bakje.** De deksel loopt in een groef vlak onder de
   stapelrand en rust op de tussenwanden, zodat elk vakje apart dicht is.
   Er zit geen klik op: de deksel schuift, en blijft door wrijving zitten. In de
   cassette houdt de wand ernaast hem op zijn plek. De groef is een
   zwaluwstaart met een plafond van 45°, zodat hij zonder support print.
3. **Stapelbaar.** De deksel zit onder de stapelrand, dus het bakje erboven valt
   gewoon met zijn Gridfinity-voeten in de rand. Halve en hele bakjes kun je
   mengen.
4. **Cassettes** hebben binnen een Gridfinity-raster (vakken van 4,2 cm). De
   binnenhoogte kies je in halve bakjes (een heel bakje telt als 2). De deksel
   van de cassette klemt de bovenste laag vast.

## Maten

Alle maten zijn buitenmaten. Een bakje is per vak 4,2 cm (precies 4,15 cm).

**Bakjes**

| Bestand | Vakken | Breed × diep × hoog |
|---|---|---|
| `bakje-1x1-half` / `-heel` | 1 | 4,2 × 4,2 × 2,2 / 3,9 cm |
| `bakje-2x1-vakjes-half` / `-heel` | 2 | 8,4 × 4,2 × 2,2 / 3,9 cm |
| `bakje-2x1-open-half` | 1 | 8,4 × 4,2 × 2,2 cm |
| `bakje-2x2-vakjes-half` | 4 | 8,4 × 8,4 × 2,2 cm |
| `bakje-2x2-open-half` | 1 | 8,4 × 8,4 × 2,2 cm |
| `bakje-4x1-open-half` | 1 | 16,8 × 4,2 × 2,2 cm |

Een half bakje is binnen ca. 0,9 cm diep, een heel bakje ca. 2,6 cm.

Bij elk formaat hoort `schuifdeksel-<formaat>.stl`. Die past op het halve en
het hele bakje, met losse vakjes of open. Naast de greepsleuf zit een
uitsparing van 0,4 mm diep voor een sticker:

| Deksel | Stickervlak |
|---|---|
| 1×1 | 2,5 × 3,4 cm |
| 2×1 | 6,7 × 3,4 cm |
| 2×2 | 6,7 × 7,6 cm |
| 4×1 | 15,1 × 3,4 cm |

**Cassettes** (diepte inclusief scharnier en klikbeugels)

| Bestand | Binnen | Breed × diep × hoog (dicht) |
|---|---|---|
| `cassette-4x2-4.3cm` | 4 × 2 vakken, 2 halve bakjes (= 1 heel) hoog | 17,3 × 10,2 × 4,3 cm |
| `cassette-4x2-7.8cm` | 4 × 2 vakken, 4 halve bakjes (= 2 hele) hoog | 17,3 × 10,2 × 7,8 cm |
| `cassette-5x2-4.3cm-schroevendraaiers` | vlakke bodem voor een inleg | 21,5 × 10,2 × 4,3 cm |

Elk bestand bestaat uit een `-onderbak` en een `-deksel`.

**Maximaal op een printbed van 35 cm**

| Onderdeel | Max. vakken | Maat |
|---|---|---|
| Bakje of schuifdeksel | 8 × 8 | 33,6 × 33,6 cm |
| Cassette (onderbak of deksel) | 8 breed × 7 diep | 34,1 × 31,2 cm |
| Bakje + deksel op één plaat | 8 × 4 | 33,6 × 34,3 cm |

De generator rekent dit zelf uit voor de bedmaat die je instelt, en stopt met
een melding als iets niet past.

**In de Packout** (winkelopgaven, niet officieel; meet je eigen koffer na)

| Koffer | Binnenmaat (ca.) | Wat past |
|---|---|---|
| Large Tool Box 48-22-8425 | 478–500 × 335–340 × 216–229 mm | per laag 6 cassettes 4×2 (2 naast, 3 achter elkaar); in de hoogte bijvoorbeeld 2× 7,8 cm + 1× 4,3 cm (19,9 cm) |
| Low-profile organizer 48-22-8431 | 457 × 305 × 46 mm | Gridfinity-bodem van 10 × 7 vakken, losse hele bakjes (3,9 cm) of twee halve op elkaar |

Voor de low-profile organizer haal je de originele bakjes eruit en leg je een
Gridfinity-baseplate in de bodem (bijvoorbeeld
[deze op MakerWorld](https://makerworld.com/en/models/1534482-gridfinity-base-for-packout-low-profile-organizer)).

## Printen

Kant-en-klare STL's staan in [`stl/`](stl/).

- **Materiaal:** PETG (aanbevolen voor de klikbeugels en het scharnier van de
  cassette; PLA wordt na een tijdje bros en kan in een warme koffer vervormen).
- **Bakjes** rechtop, **schuifdeksels** plat, **cassette-onderbak** rechtop,
  **cassette-deksel** met de bovenkant op het bed (de STL's zijn al zo
  georiënteerd). Geen support nodig.
- 3 wanden, 15–20 % infill.
- **Steuntjes in de sleuf:** in de sleuf aan de voorkant van elk bakje staan
  twee hele dunne steuntjes, zodat de brug erboven kort blijft. Die drukt de
  deksel er de eerste keer uit; eventuele restjes haal je weg met een mesje.
- **Scharnierpen cassette:** schuif een stuk 1,75 mm filament door de knokkels
  en smelt of knip de uiteinden iets dikker.

## Zelf genereren

Alles komt uit één bestand: [`generator.scad`](generator.scad). Je kiest wat je
wilt printen en hoe groot, en krijgt een STL.

**In de browser, zonder installatie:** open op MakerWorld de *Parametric
Model Maker* (onder MakerLab) en laad `generator.scad`. Je krijgt dezelfde
keuzelijsten en schuifjes en downloadt een printklare 3MF. Het bestand is één
los bestand en werkt met OpenSCAD 2021, de versie die MakerWorld gebruikt.

**Op je pc met OpenSCAD** (gratis, [openscad.org](https://openscad.org)):

1. Open `generator.scad`.
2. Zet de Customizer aan: *Window → Customizer* (of *Venster → Customizer*).
3. Kies onder *Wat wil je printen?* het onderdeel en stel de maat in.
4. Druk **F6** (renderen) en daarna **F7** (STL exporteren).

**Instellingen**

| Groep | Instelling | Betekenis |
|---|---|---|
| Wat wil je printen? | `onderdeel` | bakje, schuifdeksel, bakje + deksel, cassette-onderbak, cassette-deksel, beide, of een voorbeeld |
| Maat | `gx`, `gy` | breedte en diepte in vakken, met de maat in cm erbij; geldt voor bakje én cassette |
| Bakje | `hu` | half (2,2 cm, standaard) of heel (3,9 cm); twee halve = één heel |
| | `vakken` | elk vak apart of één open ruimte |
| | `deksel` | uit = open bakje zonder groef |
| Schuifdeksel | `lid_fit` | speling in de groef, per kant (0,1 getest: strak, schuift goed) |
| | `label_d` | diepte van de stickeruitsparing (0 = geen) |
| | `steunen` | breekbare steuntjes in de sleuf aan de voorkant (0 = geen) |
| | `klik` | klein nokje tegen vanzelf openschuiven (standaard uit) |
| Cassette | `lagen` | binnenhoogte in halve bakjes (1–6), met de hoogte van de dichte cassette in cm erbij |
| | `baseplate` | uit = vlakke bodem voor een schuim- of TPU-inleg |
| | `lid_gap` | speling tussen bovenste bakje en deksel (kleiner = vaster) |
| Printer | `bed` | maat van je printbed in mm (standaard 350) |

De schuifdeksel past op elk bakje met dezelfde `gx` × `gy`, heel of half.
De deksel schuift er aan de rechterkant (+x) uit. Bij een bakje van 4×1 is dat
de korte kant.

**Vanaf de commandoregel:**

```sh
openscad -D 'onderdeel="bakje"'        -D gx=3 -D gy=1 -o bakje-3x1.stl  generator.scad
openscad -D 'onderdeel="schuifdeksel"' -D gx=3 -D gy=1 -o deksel-3x1.stl generator.scad
openscad -D 'onderdeel="cassette_onderbak"' -D gx=3 -D gy=2 -D lagen=4 -o onderbak.stl generator.scad
```

[`maak_stls.sh`](maak_stls.sh) maakt de complete standaardset in `stl/` opnieuw.

## Nog niet getest

De modellen zijn gerenderd, gecontroleerd op geldige geometrie en in
doorsnede nagemeten (stapelen, deksel in de groef, scharnier, klikbeugels),
en de schuifdeksel van een 1×1-bakje is geprint en getest (speling 0,1 mm is
goed). Print nog één `cassette-4x2-4.3cm` en een paar bakjes, en controleer:

1. Valt een bakje goed op een ander bakje en in de cassette?
2. Klikken de beugels van de cassette goed? Te stug: maak `latch_t` dunner.
   Te los: vergroot `ridge_d`.
3. Passen twee halve bakjes (of één heel) in jouw low-profile organizer met de
   Gridfinity-bodem erin?
