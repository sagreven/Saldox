# Verstelbare scharnieren voor de dubbele opdekdeuren van het tuinhuis

3D-printbaar scharnier dat de oude paumelles vervangt. Het gebruikt de
bestaande paumelle-gaten in de deurkant en is met een stelmoer in hoogte te
stellen. Staal draagt de deur; het plastic klemt alleen.

![overzicht](render/overzicht_deuren.png)
![gemonteerd](render/scharnier_gemonteerd.png)
![exploded](render/scharnier_exploded.png)
![deurkant](render/scharnier_achterkant.png)
![printstand](render/printstand.png)

## Wat er veranderd is ten opzichte van de eerste versie

| Eerste versie (brak) | Nu |
|---|---|
| Rechtop geprint: de dunne flenzen bogen dwars op de lagen. | **Plat geprint** op de flens die tegen het hout komt. |
| Flenzen 5 mm, knokkels Ø22. | Flenzen **8 mm**, knokkels **Ø28**, brug over de volle breedte. Kozijndeel met **schoor en afschuining** op de laagnaad. |
| De deur hing op de punt van een bout in een blind gat. | **M8-bout als vaste pen** door beide knokkels; de deur **rust op een stalen stelmoer**. |
| Geprinte pennen in de paumelle-gaten. | **Stalen verzonken schroeven** in de paumelle-gaten. |

## Hoe het werkt
- **Deurdeel (oranje):** flens op de deurkant, met 2 verzonken schroeven 8 mm in de paumelle-gaten plus 2 schroeven 5×50. Bovenste knokkel.
- **Kozijndeel (blauw):** plaat op de voorkant van kozijn/gevel naast de deur, met 6 sleufgaten (±4 mm grof). Onderste knokkel met schoor en afschuining.
- **Pen:** een M8×120-bout zit van onderen door het kozijndeel, met de kop onder. Een moer die verzonken in de bovenkant van de knokkel zit, klemt hem vast. De bout steekt omhoog als vaste pen, net als bij een paumelle.
- **Hoogte:** tussen de knokkels zit op de pen een **stelmoer met ring**, en daarop **rust** de deurknokkel. Met de contramoer eronder zet je hem vast. Draai je de stelmoer met een sleutel 13, dan gaat de deur omhoog of omlaag (ongeveer −4 tot +8 mm).
- De deur is uit te tillen en draait vrij van 0 tot 180°. Ik heb dat doorgerekend op botsingen, ook over het hele stelbereik.

## Sterkte en printrichting (grove handberekening)
Aanname: deur 25 kg, 80 cm breed, scharnieren 130 cm uit elkaar, en iemand die met 50 kg op de open deur leunt. In het ergste geval vangt één scharnier dan ongeveer 750 N verticaal en 380 N horizontaal op.

De deur hangt 23 mm vóór de gevel. Daardoor wil de kozijnknokkel aan de bovenkant van de plaat **loskomen**. In de printstand trekt die kracht precies **dwars door de laagnaad** tussen plaat en knokkel. Dat is de zwakste richting van een print, en dat valt bij deze vorm niet te vermijden. Print je hem rechtop, dan zit hetzelfde probleem in de dunne plaat, en dat is erger.

Daarom heeft het kozijndeel:
- een **schoor van 45°** naast de knokkel, waardoor de naad 41 mm breed wordt in plaats van 28 mm;
- een **afschuining** aan de bovenkant, zodat er geen scherpe binnenhoek op de naad zit waar een scheur kan beginnen.

Bij het deurdeel speelt dit niet. Daar staat de knokkel met de brug direct op het bed.

| Plek | Spanning (ergste geval) | PETG/ASA kan |
|---|---|---|
| Laagnaad kozijnknokkel ↔ plaat (trek dwars op de lagen) | ~0,7 MPa (normaal gebruik ~0,1) | laaghechting ~10–20 MPa |
| M8-bout op buiging over de spleet | ~140 MPa | staal 8.8: 640 MPa |
| Stuik van de bout op de boring | ~1 MPa | ~50 MPa |
| Ring DIN 9021 Ø24 onder de deurknokkel | ~2 MPa | ~50 MPa |

Dit is een schatting, geen test. Print er eerst één en probeer hem uit.

## Stuklijst voor 2 deuren × 2 scharnieren

| Wat | Aantal |
|---|---|
| `stl/deurdeel_linkerdeur.stl` + `stl/kozijndeel_linkerdeur.stl` | 2 + 2 |
| `stl/deurdeel_rechterdeur.stl` + `stl/kozijndeel_rechterdeur.stl` | 2 + 2 |
| Zeskantbout **M8×120 DIN 933** (volledig draad, verzinkt of RVS) | 4 |
| Moer M8 (klemmoer, stelmoer, contramoer) | 12 |
| Carrosseriering M8 DIN 9021 (Ø24) | 8 |
| Verzonken constructieschroef 8 mm (bijv. 8×60) **die in de paumelle-gaten bijt** | 8 |
| Verzonken houtschroef 5×50 (deurdeel) | 8 |
| Houtschroef 5×50 met platte kop of ring (kozijndeel) | 24 |

Links en rechts zijn **van buiten gezien met de deuren dicht**: de linkerdeur scharniert aan de linkerkant.

## Monteren
1. Steek de bout met een ring van onderen door het kozijndeel. Leg een moer in de zeskant aan de bovenkant en draai de bout vast. De bout staat nu als pen omhoog.
2. Draai de contramoer en daarna de stelmoer op de pen en leg er een ring op.
3. Schroef de deurdelen op de deur **voordat je de deur ophangt**: de 8 mm schroeven in de paumelle-gaten, de 5 mm schroeven ernaast.
4. Zet de kozijndelen met de sleufgaten op de gevel en laat de deur met de knokkels over de pennen zakken.
5. Stel grof in met de sleufgaten en draai de schroeven vast. Stel daarna fijn af met de stelmoeren en zet de contramoeren vast. Een beetje vet op de ring en de pen helpt.

## Printen
- De STL's liggen al in printstand (plat), zonder support. Niet draaien in de slicer.
- **PETG of ASA**, 0,2 mm laag, **6 perimeters, 50 % gyroid infill**, 5 boven- en onderlagen.
- Voor een sterke laaghechting print je wat **heter** (PETG ~245 °C), met de koelventilator laag (30–40 %).
- Het boutgat ligt horizontaal en wordt vaak licht ovaal. Boor het na met 8,5 mm.
- Elk deurdeel is ~62 cm³, elk kozijndeel ~106 cm³. Voor alle 8 onderdelen heb je ongeveer 0,9 kg filament nodig.

## Maten aanpassen
Bovenin `scharnier.py`: `DOOR_T` (deurdikte), `HOLE_PITCH` (hart-op-hart van de paumelle-gaten),
`HOLE_Y` (hart gat tot achterkant deur), `HOLE_TOP_Z` en `HOLE_SCREW_D`.
```
pip install manifold3d trimesh pillow numpy
python3 scharnier.py   # STL's -> stl/
python3 render.py      # PNG's -> render/
```
