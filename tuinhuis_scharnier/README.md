# Verstelbaar scharnier voor de opdekdeuren van het tuinhuisje

3D-printbaar scharnier dat de oude inboor-paumelles vervangt. Het gebruikt het
bestaande paumelle-gat in de deurkant en is met schroeven in hoogte te stellen.

![gemonteerd](render/scharnier_gemonteerd.png)
![exploded](render/scharnier_exploded.png)

## Opbouw

| Onderdeel | Functie |
|---|---|
| **Deurdeel** (oranje, `stl/deurdeel_*.stl`) | Flens op de deurkant. Een pen Ø9,6 mm valt in het bestaande paumelle-gat (Ø10). Vast met 2 verzonken houtschroeven 4×40. Bovenste knokkel met blinde boring: de deur **hangt op de punt van de bout**. |
| **Kozijndeel** (blauw, `stl/kozijndeel_*.stl`) | Flens op de zijkant van het kozijn met 5 **sleufgaten** (±4,6 mm grove hoogte-instelling, schroeven 4×40 met platte kop/ring). Onderste knokkel met ingesloten M8-moer. |
| M8×80 inbusbout (DIN 912) + 2× M8-moer | Scharnieras. Draai de bout van onderen met een inbussleutel (6 mm) in/uit: de deur gaat omhoog/omlaag (**fijninstelling ±4 mm**). Borgen met de contramoer onder de knokkel. |

De deur is net als bij een paumelle **uit te tillen**.

## Instellen
1. Moer van boven in de zeskant van het kozijndeel drukken, bout van onderen erdoor (contramoer eerst op de bout).
2. Kozijndeel met schroeven in de sleufgaten op het kozijn — nog niet vastdraaien.
3. Deurdeel met de pen in het paumelle-gat steken, vastschroeven, deur op de bouten hangen.
4. Grof op hoogte zetten met de sleufgaten, schroeven vast.
5. Fijn: bout in/uit draaien tot de deur goed sluit, contramoer vastzetten. Een druppel vet in de boring helpt.

## Printen
- STL's staan al in printstand (geen support nodig): deurdeel op de bovenkant, kozijndeel op de onderkant.
- PETG of ASA (buiten!), 4 perimeters, 40 % infill.
- Per deur: 2× deurdeel + 2× kozijndeel van dezelfde hand. `_rechts` = scharnieren aan de rechterkant (van buiten gezien met de deur dicht),
  `_links` = gespiegeld. Controleer even met de render welke je nodig hebt.

## Aanpassen
Alle maten staan bovenaan `scharnier.py` (deurdikte `DOOR_T`, gatdiameter `HOLE_D`, gatdiepte, pen-hoogte, …).
```
pip install manifold3d trimesh pillow numpy
python3 scharnier.py   # STL's -> stl/
python3 render.py      # PNG's -> render/
```
