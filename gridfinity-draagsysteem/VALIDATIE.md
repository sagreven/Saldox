# Validatie: Gridfinity-draagsysteem

Dit document legt vast **waaraan elk onderdeel moet voldoen** en **hoe we dat
testen**. Er zijn twee soorten tests:

- **Automatisch (A–G):** `python3 valideer.py` controleert de STL-bestanden in
  `stl/` en zet ze virtueel in elkaar. Draai dit na elke wijziging aan
  `generator.scad` of `krimptang_inleg.scad`, vóór je iets print.
- **Na het printen (P):** metingen en proeven op de echte onderdelen. Vul de
  resultaten in de tabel onderaan in.

Alle hoogtes zijn gemeten vanaf de onderkant van het onderdeel (of de tafel).

## Referentiematen

| Maat | Waarde | Waar het van afhangt |
|---|---|---|
| Gridfinity-vak | 42 mm, bakje 41,5 mm per vak | standaard |
| Heel bakje, totale hoogte | 39,4 mm (stapelt per 35 mm) | `hu = 5` |
| Half bakje, totale hoogte | 21,9 mm (stapelt per 17,5 mm) | `hu = 2.5` |
| Bodem cassette met magneten 6 × 2 | 3,2 mm (gat 2,2 + 1,0 mm) | `magneet_h`, `c_skin` |
| Gridfinity-bodem in cassette | vakken open tot 3,2 mm, randjes op 7,85 mm | `gf_base = 4,65` |
| Cassette 4,5 cm: scheidingslijn onderbak/klep | 37,0 mm | `lagen = 2` |
| Cassette 4,5 cm: bovenkant opstaande rand | 40,0 mm | `tongue_h = 3` |
| Cassette 4,5 cm: plafond klep (binnen) | 44,0 mm | `deksel_extra = 1` |
| Bovenkant heel bakje in cassette | 42,6 mm → 1,4 mm ruimte | |
| Schuifdeksel bakje in cassette | 35,6 – 37,1 mm | |
| Krimptang (uit foto) | ca. 181 × 73 mm, handvatten ca. 24 mm hoog | **nameten** |

## Automatische tests (`valideer.py`)

| Eis | Wat | Geslaagd als |
|---|---|---|
| **A1** | Elk STL-bestand is een dicht model uit één stuk | geen open randen, 1 deel |
| **A2** | Bakjes hebben de juiste maat | 41,5 mm × vakken − 0,5; hoogte 39,4 / 21,9 mm (± 0,05) |
| **C1** | De vloer in elk vak van een cassette ligt op de bodem | 3,2 mm (± 0,05) |
| **C2** | Gridfinity-randjes in de cassette op de juiste hoogte | 7,85 mm, alleen in de Gridfinity-rijen |
| **C3** | Klik-nokjes in de Gridfinity-vakken van de cassette | wand van het vak op < 18,8 mm van het midden |
| **D1** | Klep sluit op de onderbak | overlap < 0,1 mm³ |
| **D2** | Hele en halve bakjes (gestapeld) passen met de klep dicht | overlap 0 met onderbak en klep |
| **D3** | Ruimte tussen bovenste bakje en klep | 0,4 – 3 mm |
| **E1** | Bakje klikt in de ingebouwde Gridfinity-bodem | geplaatst geen overlap, 0,6 mm opgetild wel (klik) |
| **E2** | Bakje klikt in de losse Gridfinity-bodem | idem |
| **E3** | Bakje klikt op een ander bakje | idem |
| **E4** | Nokjes in de stapelrand steken ver genoeg voorbij het voetvlak | 0,3 – 0,8 mm (groefje is 0,8 mm diep) |
| **E5** | Nokjes in de Gridfinity-bodem (los en ingebouwd) idem | 0,25 – 0,8 mm |
| **F1** | Schuifdeksel past dicht in de groef van het bakje | overlap 0 (zonder breekbare steuntjes) |
| **F2** | Schuifdeksel schuift er helemaal uit | overlap 0 op elke positie |
| **G1** | Krimptang-inleg past in de cassette (vlak + losse bodem, en ingebouwd) | overlap 0 met onderbak en bodem |
| **G2** | Paddenstoel blijft onder de klep | bovenkant ≤ plafond − 1 mm |
| **G3** | Boog bij de kop drukt op de tang | overlap met de tang > 0 (voorspanning) |
| **G4** | Bogen bij de handvatten drukken op de tang | overlap > 0 |
| **G5** | Pootjes van de paddenstoel raken de handvatten niet onder de klik-tanden | overlap 0 tot 20,5 mm hoogte |
| **G6** | Klik-tanden van de paddenstoel grijpen over de handvatten | overlap > 0 boven de handvatten |

| **H1** | Bakjes 2×2 (alle varianten): dicht model, juiste maat | 83,5 × 83,5 × 39,4 / 21,9 mm |
| **H2** | Bakje 2×2 past in de cassette 5×4 (halve: 2 gestapeld), klep dicht | overlap 0, ruimte ≥ 0,4 mm |
| **H3** | Bakje 2×2 klikt in de Gridfinity-bodem van de cassette | geplaatst geen overlap, opgetild wel |
| **H4** | Bakje 2×2 klikt op een gelijk bakje | idem |
| **H5** | Schuifdeksel past dicht op het bakje 2×2 | overlap 0 (zonder steuntjes) |
| **H6** | Schuifdeksel schuift er helemaal uit | overlap 0 op elke positie |
| **H7** | `schuifdeksel-2x2.stl` heeft dezelfde maat als de deksel van het bakje | ± 0,05 mm |
| **H8** | Deksel rust op de tussenschotten (elk vakje apart dicht) | bovenkant schot = onderkant deksel (± 0,05) |
| **H9** | Breekbare steuntjes in de sleuf | 2 per vak langs de sleuf = 4 |
| **I1** | Borenkokers 3-8 (3×2), 9-12 (4×2), SDS (4×1) en doppen: dicht model, juiste maat | W × D × 39,4 mm |
| **I2** | Geprinte dop (voorkant op het bed) is dezelfde als de dop in de koker | volume ± 1 mm³ |
| **I3** | Dop past dicht, voorkant gelijk met de koker | overlap 0 |
| **I4** | Dop klikt vast | 2 mm eruit: nokjes raken de wand |
| **I5** | Alle boren (lengtes uit README) passen met de dop dicht | overlap 0 met koker en dop, ≥ 0,5 mm vrij achteraan |
| **I6** | Dop met boren schuift er helemaal uit | overlap 0 op elke positie |
| **I7** | Koker klikt in de Gridfinity-bodem | geplaatst geen overlap, opgetild wel |
| **I8** | Bakje klikt bovenop de koker (stapelrand) | idem |
| **I9** | Drie kokers en een bakje 1×2 samen in de cassette 5×4, klep dicht | overlap 0, ruimte ≥ 0,4 mm |

Voor G3–G6 gebruikt het script een benadering van de tang (de omtrek uit de
foto, met de opening tussen de handvatten, als blok van `tang_h` hoog). Die
tests zeggen dus: *als de tang deze maat heeft*, dan pakt de inleg hem. De
echte maat moet uit P8 komen.

Terugblik: test **E4/E5** had gevonden dat de klik in de eerste versie te klein was (0,2 en 0,15 mm, geprint geen klik). Test **C1** had de fout in de oudere cassettes gevonden (vloer op
7,85 in plaats van 3,2 mm, zie README); op het oude bestand geeft C1 FOUT.

### Draaien

```sh
pip install trimesh manifold3d rtree numpy
./maak_stls.sh          # STL's opnieuw maken
python3 valideer.py     # alle controles; stopt met code 1 bij een fout
```

## Tests na het printen

Gebruik een schuifmaat. Noteer de waarde en of het binnen de grens valt.

| Eis | Wat meten / doen | Verwacht | Grens |
|---|---|---|---|
| **P1** | Hoogte heel bakje (voeten tot bovenkant) | 39,4 mm | ± 0,3 |
| **P2** | Hoogte half bakje | 21,9 mm | ± 0,3 |
| **P3** | Diepte binnen de onderbak: vloer tot bovenkant opstaande rand (meten in het midden van een vak) | 36,8 mm | ± 0,3 |
| **P4** | Binnendiepte klep: onderrand tot plafond | 7,0 mm | ± 0,3 |
| **P5** | Lege cassette: klep gaat dicht en klikt | geen kier | 0 mm |
| **P6** | Gevulde cassette (hele bakjes en twee halve gestapeld): klep gaat dicht | geen kier | 0 mm |
| **P7** | Bakje in cassette / op bakje: voelbare klik, valt er bij omkeren niet uit (eerst met de proefstukjes `test-klik-*`) | klikt, blijft zitten | — |
| **P8** | Krimptang meten: totale lengte, grootste breedte (handvatten in rust), hoogte handvatten als hij plat ligt | 181 / 73 / 24 mm | wijkt het > 2 mm af: invullen in `krimptang_inleg.scad` en opnieuw valideren |
| **P9** | Krimptang in de inleg: klikt onder de paddenstoel, zit klem tussen de bogen | klikt, beweegt < 1 mm | — |
| **P10** | Cassette met tang dicht, schudden en ondersteboven houden | tang en bakjes rammelen niet hoorbaar, klep blijft dicht | — |
| **P11** | Schuifdeksel bakje: schuift soepel, blijft dicht bij omkeren | soepel, blijft zitten | — |
| **P12** | Magneten: twee cassettes naast elkaar en op elkaar | trekken elkaar aan (zijkanten en bovenop) | — |

## Resultaten

| Datum | Onderdeel / versie (commit) | Eis | Gemeten | OK? | Opmerking |
|---|---|---|---|---|---|
| | | | | | |
