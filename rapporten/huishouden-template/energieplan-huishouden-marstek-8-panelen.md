# Energieplan huishouden: 8 panelen en Marstek

7 oktober 2026 · Saldox · template voor een standaard huishouden

## Samenvatting

Het pakket kost €4.004,55 incl. btw en levert na de jaarlijkse kosten netto €410 tot €570 per jaar op; normaal is het in ca. 8,3 jaar terugverdiend (7,0 tot 9,8 jaar).

- **Zonnestroom:** 8 panelen van 460 Wp (3,7 kWp), ca. 3.370 kWh per jaar. Zonder batterij gebruikt u 31% zelf, met batterij 47%.
- **Thuisbatterij:** Marstek Venus E 3.0 (4,6 kWh bruikbaar, 2,5 kW); de panelen hebben APsystems-micro-omvormers. Laadt goedkoop van het net en met zonnestroom, en levert op dure uren.
- **Stroomcontract:** dynamisch voor afname en teruglevering; het EMS van Saldox stuurt batterij op de uurprijs.
- **Zonnepanelen** verdienen zich het snelst terug (ca. 7,2 jaar); de batterij vooral via de prijsverschillen op een dynamisch contract.
- **Btw:** 0% op zonnepanelen, omvormer en montage; 21% op de batterij.

## Begroting

Het pakket kost €3.722,96 excl. btw en €4.004,55 incl. btw. Op zonnepanelen geldt het nultarief; de batterijset valt onder 21%.

| Post | Excl. btw | Btw | Incl. btw | Status |
| --- | --- | --- | --- | --- |
| 8 zonnepanelen A Solar 460 Wp, glas-glas (8 × €69,46) | €555,68 | 0% | €555,68 | Inkoopprijs |
| 4 micro-omvormers APsystems DS3, 880 VA (4 × €110,74) | €442,96 | 0% | €442,96 | Inkoopprijs |
| 8 Y3 AC-buskabels en 8 eindkappen (APsystems) | €186,41 | 0% | €186,41 | Inkoopprijs |
| Monitoring APsystems ECU-B | €67,00 | 0% | €67,00 | Stelpost |
| Transport | €30,00 | 0% | €30,00 | Tarief |
| Montage zonnepanelen en micro-omvormers | €700,00 | 0% | €700,00 | Stelpost |
| Dakbevestiging en bekabeling | €400,00 | 0% | €400,00 | Stelpost |
| Thuisbatterij Marstek Venus E 3.0, 5,12 kWh, incl. P1-meter | €990,91 | 21% | €1.199,00 | Marktprijs |
| Eigen groep voor de batterij (2.500 W) en aansluiten | €250,00 | 21% | €302,50 | Stelpost |
| EMS-koppeling Saldox (Modbus TCP) | €100,00 | 21% | €121,00 | Stelpost |
| **Totaal** | **€3.722,96** | | **€4.004,55** | |

<!-- FIG:begroting -->

- **Nultarief:** de Belastingdienst rekent 0% btw op levering en installatie van zonnepanelen op of bij een woning, inclusief omvormer, bekabeling, montagemateriaal en aanpassingen in de meterkast voor de panelen.
- **Batterij 21%:** levering en installatie van een thuisbatterij vallen onder 21%. Panelen, micro-omvormers, bekabeling en montage vallen onder het nultarief.
- **Optie plat dak:** de montage kost bij een plat dak vast €250,00 (0% btw) in plaats van €700,00. Het pakket kost dan €3.554,55 incl. btw en is normaal in ca. 7,4 jaar terugverdiend.
- **Stelposten** zijn inschattingen voor een standaard woning. Vervang ze door de offerte van de installateur.
- **Aansluiting:** de micro-omvormers en de Venus E zijn 1-fase; een gewone aansluiting volstaat. De Venus E krijgt een eigen groep, zodat hij met 2.500 W kan laden en ontladen. Op een gewoon stopcontact is het maximaal 800 W.

## Wat het per jaar oplevert

Normaal levert het pakket €520 per jaar op; na het stand-byverbruik van de batterij en een kleine reservering blijft €480 over.

| Per jaar | Pessimistisch | Normaal | Optimistisch |
| --- | --- | --- | --- |
| Zon (minder stroom inkopen, teruglevering) | €320 | €330 | €360 |
| Batterij (slim laden en ontladen) | €130 | €190 | €250 |
| **Bruto per jaar** | **€450** | **€520** | **€610** |
| Stand-by batterij en reservering | −€40 | −€40 | −€40 |
| **Netto per jaar** | **€410** | **€480** | **€570** |

<!-- FIG:waterval -->

**Hoe dit is berekend.** Saldox simuleert elk uur van een jaar met de echte uurprijzen van 2025 (EPEX day-ahead Nederland) en het echte zonneprofiel van Nederland. Het EMS zet de batterij in zoals in de praktijk: met de day-ahead prijzen, die een dag vooruit bekend zijn.

- **Pessimistisch / normaal / optimistisch:** opbrengst 861 / 917 / 1.032 kWh per kWp (PVGIS: oost-west, gemiddeld, zuid); batterij ×0,7 / ×1 / ×1,3 (in 2026 waren de prijsverschillen binnen een dag ca. 33% groter dan in 2025).
- **Stroomprijs:** uurprijs plus opslag van de leverancier (ca. €0,02 per kWh incl. btw), plus btw en energiebelasting (€0,1108 per kWh incl. btw in 2026). Teruglevering tegen de uurprijs, zonder terugleverkosten; bij een negatieve prijs zet het EMS de teruglevering stop.
- **Verbruik:** 2.500 kWh per jaar (Milieu Centraal: gemiddeld 2.430 kWh, 2 personen ca. 2.550 kWh) met een standaard dagprofiel: ochtend- en avondpiek, in de winter hoger.

## Terugverdientijd

Het pakket van €4.004,55 is normaal in ca. 8,3 jaar terugverdiend; pessimistisch in 9,8 jaar en optimistisch in 7,0 jaar.

<!-- FIG:kasstroom -->

| Onderdeel | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd (normaal) |
| --- | --- | --- | --- |
| Zonnepanelen (panelen, micro-omvormers, montage) | €2.382,05 | €330 | 7,2 jaar |
| Batterij (Venus E, eigen groep, EMS) | €1.622,50 | €150 | 10,8 jaar |
| **Totaal** | **€4.004,55** | **€480** | **8,3 jaar** |

<!-- FIG:payback -->

- **Zonnepanelen** verdienen zich snel terug, ook zonder saldering: het grootste deel van de waarde zit in de stroom die u zelf gebruikt.
- **De batterij** verdient minder dan de panelen: een batterij van 5 kWh past bij een verbruik van 2.500 kWh, maar het rendement van 85% en het stand-byverbruik drukken de winst. Hij verdient sneller bij een groter verbruik (warmtepomp, elektrische auto) en bij grotere prijsverschillen. Het stand-byverbruik en de reservering staan bij de batterij.

## Zonnestroom zelf gebruiken

Overdag is er weinig verbruik in huis, dus een groot deel van de zonnestroom gaat zonder batterij terug het net op. Met de batterij gebruikt u 47% van de zonnestroom zelf in plaats van 31%.

| | Zonder batterij | Met batterij |
| --- | --- | --- |
| Opwek per jaar | 3.370 kWh | 3.370 kWh |
| Zelf gebruikt | 31% | 47% |
| Teruggeleverd | 2.340 kWh | 1.780 kWh |
| Ingekocht van het net | 1.470 kWh | 1.130 kWh |

- **Teruglevering is weinig waard:** zonder saldering krijgt u bij een dynamisch contract de uurprijs, en die is laag als de zon schijnt (in 2025 gemiddeld ca. €0,05 per kWh tijdens zonne-uren).
- **De batterij laadt ook van het net:** op goedkope uren 's nachts of midden op de dag, en levert op dure uren in de ochtend en avond. Daardoor stijgt de inkoop van het net soms, terwijl de kosten dalen.
- **Een tweede Venus E** (tot 3 op één fase) levert bij dit verbruik weinig extra op. Een warmtepomp of elektrische auto verandert dat.

## Stroomcontract en prijzen

Het pakket werkt het best met een dynamisch contract: alleen dan kan de batterij goedkoop laden en duur leveren. Met een vast contract wordt het normale netto €490 per jaar (8,2 jaar).

| | Dynamisch (advies) | Vast |
| --- | --- | --- |
| Afname | Uurprijs plus opslag, btw en energiebelasting | Vaste prijs, ca. €0,28 per kWh incl. btw |
| Teruglevering | Uurprijs, bij veel leveranciers zonder terugleverkosten | Vergoeding ca. €0,10 min terugleverkosten €0,045 tot 0,065 |
| Zon per jaar | €330 | €410 |
| Batterij per jaar | €190 | €120 |
| Netto per jaar (normaal) | €480 | €490 |
| Terugverdientijd (normaal) | 8,3 jaar | 8,2 jaar |

- **Einde saldering per 1 januari 2027:** al verwerkt; dit plan rekent nergens met saldering. Bij een vast contract moet de leverancier tot 2030 ten minste 50% van de kale leveringsprijs vergoeden; terugleverkosten mogen alleen de werkelijke kosten dekken en staan vanaf 2027 per kWh op de factuur.
- **Prijzen 2027:** door de oorlog met Iran ligt de groothandelsprijs voor stroom in 2027 op de termijnmarkt ca. 15% hoger dan in 2026. Dan wordt het normale netto ca. €530 per jaar (7,6 jaar).
- **Energiebelasting 2027:** stroom daalt naar €0,1065 per kWh incl. btw.

## Installatie en veiligheid

De installatie is in één tot twee dagen klaar; de batterij hoort op een droge, vorstvrije plek met ruimte voor ventilatie.

- **A Solar 460 Wp (8×):** N-type, glas-glas, zwart; 1.762 × 1.134 mm per paneel, samen ca. 16 m² dak.
- **APsystems DS3 (4×):** micro-omvormer voor twee panelen, 880 VA, 2 MPPT's, rendement ca. 97%. Elk paneelpaar werkt apart, dus schaduw op één paneel kost weinig. Monitoring via de APsystems ECU-B.
- **Marstek Venus E 3.0:** LFP-batterij, 5,12 kWh, bruikbaar ca. 4,6 kWh, 2.500 W laden en ontladen op een eigen groep, rendement ca. 85% heen en terug, stand-by ca. 5 W. Meer dan 6.000 cycli, garantie 10 jaar. Het EMS van Saldox stuurt hem via Modbus TCP op de uurprijs.
- **Plaatsing:** op een eigen groep, nooit via een verlengsnoer of stekkerdoos; op een droge, geventileerde plek buiten de vluchtroute. De batterij schakelt zichzelf uit bij stroomuitval van het net.
- **Uitbreidbaar:** later kunnen er panelen met extra micro-omvormers of een laadpaal bij, en tot 3 Venus E's op één fase.
- **Veiligheid:** PGS 37-1 geldt niet voor thuisbatterijen; ook de nieuwe batterijregels van 2028 zonderen thuisbatterijen uit. De installatie moet voldoen aan NEN 1010. Laat een erkende installateur installeren en meld de batterij bij de opstalverzekeraar.
- **Aanmelden:** meld de zonnepanelen en de batterij bij de netbeheerder via energieleveren.nl.

## Planning

Van akkoord tot werkend systeem duurt het ca. 4 tot 6 weken.

| Week | Wat |
| --- | --- |
| 1 | Schouw: dak, meterkast, plek batterij, ruimte in de groepenkast |
| 2 tot 3 | Bestellen en leveren; dynamisch contract regelen |
| 4 | Installatie panelen, micro-omvormers en batterij (1 tot 2 dagen) |
| 4 tot 5 | Aanmelden energieleveren.nl, EMS koppelen, oplevering en uitleg |

## Aannames en te bevestigen

De cijfers gelden voor een standaard huishouden; vervang de aannames door de gegevens van de klant voordat het advies definitief is.

**Te bevestigen bij de klant**

- [ ] Jaarverbruik en verbruiksprofiel (slimme meter)
- [ ] Dak: plat of schuin (plat dak: montage vast €250), oriëntatie, hellingshoek, schaduw en ruimte voor 8 panelen (ca. 16 m²)
- [ ] Ruimte in de groepenkast voor een eigen groep voor de batterij
- [ ] Plek voor de batterij: droog, vorstvrij, bereikbaar
- [ ] Stroomcontract: dynamisch voor afname en teruglevering
- [ ] Offerte installateur voor de stelposten

**Aannames**

- Verbruik 2.500 kWh per jaar; opbrengst 917 kWh per kWp
- Uurprijzen en zonneprofiel van 2025; opslag dynamisch contract ca. €0,02 per kWh incl. btw; energiebelasting 2026
- Batterij 4,6 kWh bruikbaar, 2,5 kW, rendement 85% heen en terug, stand-by ca. 50 kWh per jaar
- Stand-by batterij en reservering €40 per jaar

## Begrippen

De technische termen in dit advies, in gewone taal.

| Begrip | Uitleg |
| --- | --- |
| Dynamisch contract | Stroomcontract met een prijs die elk uur verandert, voor afname en teruglevering. |
| EMS | Energiemanagementsysteem: de software van Saldox die batterij en omvormer op de uurprijs stuurt. |
| ERE | Emissiereductie-eenheid: vergoeding voor stroom die in een elektrische auto wordt geladen, via een inboekdienstverlener. |
| Micro-omvormer | Kleine omvormer onder de panelen; de APsystems DS3 bedient twee panelen. |
| AC-gekoppelde batterij | Batterij met een eigen omvormer die op het huisnet wordt aangesloten, los van de zonnepanelen. |
| kWh en kWp | kWh is een hoeveelheid energie; kWp is het piekvermogen van zonnepanelen. |
| LFP | Lithium-ijzerfosfaat: veilige, lang meegaande batterijchemie. |
| MID-meter | Geijkte kWh-meter; nodig voor de ERE-vergoeding. |
| Nultarief | 0% btw op zonnepanelen en hun installatie bij woningen. |
| Saldering | Wegstrepen van teruggeleverde tegen afgenomen stroom; stopt per 1 januari 2027. |
| Stelpost | Geschat bedrag voor een post waarvan de exacte prijs nog niet bekend is. |
| Zelfverbruik | Het deel van de zonnestroom dat u zelf gebruikt in plaats van terug te leveren. |
