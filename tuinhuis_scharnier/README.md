# Verstelbare scharnieren voor de dubbele opdekdeuren van het tuinhuis

3D-printbaar scharnier dat de oude paumelles vervangt. Het gebruikt de
bestaande paumelle-gaten in de deurkant (zelfde diameter, diepte en
hart-op-hart afstand als de kant van de paumelle die normaal in de muur gaat)
en is met schroeven in hoogte te stellen. De deur is uit te tillen.

![overzicht](render/overzicht_deuren.png)
![gemonteerd](render/scharnier_gemonteerd.png)
![exploded](render/scharnier_exploded.png)
![deurkant](render/scharnier_achterkant.png)

## Opbouw

| Onderdeel | Functie |
|---|---|
| **Deurdeel** (oranje) | Flens op de deurkant met **twee pennen** die in de paumelle-gaten vallen, plus 2 verzonken houtschroeven 4×40. Bovenste knokkel met blinde boring: de deur **hangt op de punt van de bout**. |
| **Kozijndeel** (blauw) | Plaat op de **voorkant** van kozijn/gevel naast de deur, met 5 **sleufgaten** (±4,6 mm grof in hoogte; schroeven 4×40 met platte kop of ring). Onderste knokkel met ingesloten M8-moer. |
| M8×80 inbusbout (DIN 912) + 2× M8-moer | Scharnieras. Draai de bout van onderen in of uit met een 6 mm inbussleutel, dan gaat de deur omhoog of omlaag (**fijn ±4 mm**). Zet hem vast met de contramoer. |

De deur draait vrij van 0 tot 180° (gecontroleerd op botsingen).

## Stuklijst voor 2 deuren × 2 scharnieren

| Wat | Aantal |
|---|---|
| `stl/deurdeel_linkerdeur.stl` + `stl/kozijndeel_linkerdeur.stl` | 2 + 2 |
| `stl/deurdeel_rechterdeur.stl` + `stl/kozijndeel_rechterdeur.stl` | 2 + 2 |
| Inbusbout M8×80 DIN 912 | 4 |
| Moer M8 | 8 |
| Verzonken houtschroef 4×40 (deurdeel) | 8 |
| Houtschroef 4×40 met platte kop of ring (kozijndeel) | 20 |

Links en rechts zijn **van buiten gezien met de deuren dicht**: de linkerdeur scharniert aan de linkerkant.

## Monteren en instellen
1. Druk de M8-moer van boven in de zeskant van het kozijndeel. Draai de contramoer op de bout en steek de bout van onderen erdoor.
2. Schroef de deurdelen op de deur (pennen in de paumelle-gaten) **vóór** je de deur ophangt. Als de deur hangt, zit de onderste schroef achter de knokkel.
3. Zet de kozijndelen met schroeven in de sleufgaten op de gevel en hang de deur erop. Grof op hoogte zetten en de schroeven vastdraaien.
4. Fijn: draai de bouten in of uit tot de deuren goed in het midden sluiten en zet de contramoeren vast. Een beetje vet in de boring helpt.

## Printen
- De STL's liggen al in printstand, zonder support.
- PETG of ASA (UV-bestendig, het hangt buiten), 4–5 perimeters, 40 % infill.

## Maten aanpassen
**Meet de paumelle-gaten na en vul ze bovenin `scharnier.py` in:** `HOLE_D` (diameter),
`HOLE_DEPTH` (diepte), `HOLE_PITCH` (hart-op-hart afstand), `HOLE_Y` (hart gat tot
achterkant deur) en `DOOR_T` (deurdikte). Nu staan daar aannames: Ø10, 25 diep, 50 hart-op-hart, midden van een deur van 20 mm.
```
pip install manifold3d trimesh pillow numpy
python3 scharnier.py   # STL's -> stl/
python3 render.py      # PNG's -> render/
```
