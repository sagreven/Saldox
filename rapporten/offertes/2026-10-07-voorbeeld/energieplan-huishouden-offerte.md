# Energieplan Voorbeeld

7 oktober 2026 · Saldox · offerte voor Voorbeeld · klein huishouden (1 tot 2 personen), plug-in hybride, dagelijks geladen, plat dak, 10 panelen

## Samenvatting

Het pakket kost €5.701,62 incl. btw en levert na de jaarlijkse kosten netto €1.280 tot €1.840 per jaar op; normaal is het in ca. 3,6 jaar terugverdiend (3,1 tot 4,5 jaar).

- **Zonnestroom:** 10 panelen van 460 Wp (4,6 kWp), ca. 4.220 kWh per jaar. Zonder batterij gebruikt u 21% zelf, met batterij 35%.
- **Thuisbatterij:** Marstek Venus E 3.0 (4,6 kWh bruikbaar, 2,5 kW); de panelen hebben APsystems-micro-omvormers. Laadt goedkoop van het net en met zonnestroom, en levert op dure uren.
- **Stroomcontract:** dynamisch voor afname en teruglevering; het EMS van Saldox stuurt batterij en laadpaal op de uurprijs.
- **Laadpaal:** Zaptec Go 2 voor eigen gebruik, slim laden op goedkope uren. Thuis laden kost ca. €0,17 per kWh tegen ca. €0,60 op benzine, plus ERE-vergoeding.
- **Zonnepanelen** verdienen zich het snelst terug (ca. 6,6 jaar); de batterij vooral via de prijsverschillen op een dynamisch contract.
- **Btw:** 0% op zonnepanelen, omvormer en montage; 21% op de batterij en de laadpaal.

## Begroting

Het pakket kost €5.124,85 excl. btw en €5.701,62 incl. btw. Op zonnepanelen geldt het nultarief; de batterijset valt onder 21%.

| Post | Excl. btw | Btw | Incl. btw | Status |
| --- | --- | --- | --- | --- |
| 10 zonnepanelen A Solar 460 Wp, glas-glas (10 × €69,46) | €694,60 | 0% | €694,60 | Inkoopprijs |
| 5 micro-omvormers APsystems DS3, 880 VA (5 × €110,74) | €553,70 | 0% | €553,70 | Inkoopprijs |
| 10 Y3 AC-buskabels en 10 eindkappen (APsystems) | €233,02 | 0% | €233,02 | Inkoopprijs |
| Monitoring APsystems ECU-B | €67,00 | 0% | €67,00 | Stelpost |
| Transport | €30,00 | 0% | €30,00 | Tarief |
| Montage zonnepanelen op plat dak (vast) | €250,00 | 0% | €250,00 | Tarief |
| Plat-dak-opstelling met ballast en bekabeling | €550,00 | 0% | €550,00 | Stelpost |
| Thuisbatterij Marstek Venus E 3.0, 5,12 kWh, incl. P1-meter | €990,91 | 21% | €1.199,00 | Marktprijs |
| Eigen groep voor de batterij (2.500 W) en aansluiten | €250,00 | 21% | €302,50 | Stelpost |
| EMS-koppeling Saldox (Modbus TCP) | €100,00 | 21% | €121,00 | Stelpost |
| Zaptec Go 2 laadpaal (22 kW, MID-meter) | €825,62 | 21% | €999,00 | Opgegeven |
| Installatie laadpaal incl. groep en bekabeling | €580,00 | 21% | €701,80 | Stelpost |
| **Totaal** | **€5.124,85** | | **€5.701,62** | |

<!-- FIG:begroting -->

- **Nultarief:** de Belastingdienst rekent 0% btw op levering en installatie van zonnepanelen op of bij een woning, inclusief omvormer, bekabeling, montagemateriaal en aanpassingen in de meterkast voor de panelen.
- **Batterij 21%:** levering en installatie van een thuisbatterij vallen onder 21%. Panelen, micro-omvormers, bekabeling en montage vallen onder het nultarief.

- **Stelposten** zijn inschattingen voor een standaard woning. Vervang ze door de offerte van de installateur.
- **Aansluiting:** de micro-omvormers en de Venus E zijn 1-fase; een gewone aansluiting volstaat. De Venus E krijgt een eigen groep, zodat hij met 2.500 W kan laden en ontladen. Op een gewoon stopcontact is het maximaal 800 W. Het dak is plat: de panelen komen op een opstelling met ballast.

## Wat het per jaar oplevert

Normaal levert het pakket €1.620 per jaar op; na het stand-byverbruik van de batterij en een kleine reservering blijft €1.580 over.

| Per jaar | Pessimistisch | Normaal | Optimistisch |
| --- | --- | --- | --- |
| Zon (minder stroom inkopen, teruglevering) | €340 | €360 | €390 |
| Batterij (slim laden en ontladen) | €130 | €180 | €250 |
| Thuis laden in plaats van op benzine | €650 | €850 | €980 |
| ERE-vergoeding laadpaal | €200 | €230 | €260 |
| **Bruto per jaar** | **€1.320** | **€1.620** | **€1.880** |
| Stand-by batterij en reservering | −€40 | −€40 | −€40 |
| **Netto per jaar** | **€1.280** | **€1.580** | **€1.840** |

<!-- FIG:waterval -->

**Hoe dit is berekend.** Saldox simuleert elk uur van een jaar met de echte uurprijzen van 2025 (EPEX day-ahead Nederland) en het echte zonneprofiel van Nederland. Het EMS zet de batterij in zoals in de praktijk: met de day-ahead prijzen, die een dag vooruit bekend zijn.

- **Pessimistisch / normaal / optimistisch:** opbrengst 861 / 917 / 1.032 kWh per kWp (PVGIS: oost-west, gemiddeld, zuid); batterij ×0,7 / ×1 / ×1,3 (in 2026 waren de prijsverschillen binnen een dag ca. 33% groter dan in 2025); benzine omgerekend €0,50 / €0,60 / €0,66 per kWh; ERE €0,10 / €0,115 / €0,13 per kWh.
- **Stroomprijs:** uurprijs plus opslag van de leverancier (ca. €0,02 per kWh incl. btw), plus btw en energiebelasting (€0,1108 per kWh incl. btw in 2026). Teruglevering tegen de uurprijs, zonder terugleverkosten; bij een negatieve prijs zet het EMS de teruglevering stop.
- **Verbruik:** 2.000 kWh per jaar (Milieu Centraal: gemiddeld 2.430 kWh, 2 personen ca. 2.550 kWh) met een standaard dagprofiel: ochtend- en avondpiek, in de winter hoger.
- **Plug-in hybride:** 2.000 kWh per jaar thuis geladen (dagelijks geladen: ca. 40 km per werkdag elektrisch, 20 kWh per 100 km).

## Terugverdientijd

Het pakket van €5.701,62 is normaal in ca. 3,6 jaar terugverdiend; pessimistisch in 4,5 jaar en optimistisch in 3,1 jaar.

<!-- FIG:kasstroom -->

| Onderdeel | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd (normaal) |
| --- | --- | --- | --- |
| Zonnepanelen (panelen, micro-omvormers, montage) | €2.378,32 | €360 | 6,6 jaar |
| Batterij (Venus E, eigen groep, EMS) | €1.622,50 | €140 | 11,6 jaar |
| Laadpaal (Zaptec Go 2 en installatie) | €1.700,80 | €1.080 | 1,6 jaar |
| **Totaal** | **€5.701,62** | **€1.580** | **3,6 jaar** |

<!-- FIG:payback -->

- **Zonnepanelen** verdienen zich snel terug, ook zonder saldering: het grootste deel van de waarde zit in de stroom die u zelf gebruikt.
- **De batterij** verdient minder dan de panelen: een batterij van 5 kWh past bij een verbruik van 2.000 kWh, maar het rendement van 85% en het stand-byverbruik drukken de winst. Hij verdient sneller bij een groter verbruik (warmtepomp) en bij grotere prijsverschillen. Het stand-byverbruik en de reservering staan bij de batterij.
- **De laadpaal** verdient zich het snelst terug, omdat thuis laden veel goedkoper is dan dezelfde kilometers op benzine rijden. Laadt u nu al thuis aan een gewone laadpaal, dan is de winst kleiner: dan bespaart slim laden ca. €96 per jaar, plus de ERE-vergoeding.

## Waarom dit pakket

Voor dit huishouden levert Marstek Venus E (5,12 kWh) met micro-omvormers over 15 jaar het meeste op: na aftrek van de investering ca. €17.998.

| Pakket | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd | Opbrengst na 15 jaar |
| --- | --- | --- | --- | --- |
| **Marstek Venus E (5,12 kWh) met micro-omvormers (advies)** | €5.701,62 | €1.580 | 3,6 jaar | €17.998 |
| 2× Marstek Venus E (10,24 kWh) met micro-omvormers | €7.082,12 | €1.670 | 4,2 jaar | €17.968 |
| Sofar BTS 10 kWh met ESI 10 kW hybride omvormer | €7.810,09 | €1.685 | 4,6 jaar | €17.465 |
| Alleen zonnepanelen en laadpaal, zonder batterij (ter vergelijking) | €4.079,12 | €1.440 | 2,8 jaar | €17.521 |

- **Profiel:** klein huishouden (1 tot 2 personen), plug-in hybride, dagelijks geladen, plat dak, 10 panelen; verbruik ca. 2.000 kWh per jaar; plug-in hybride ca. 2.000 kWh per jaar thuis geladen.
- **Keuze:** Saldox rekent elk passend pakket door met dezelfde uurprijzen en kiest het pakket met de hoogste opbrengst na 15 jaar, de levensduur van de batterij en de omvormers.
- **De batterij** voegt over 15 jaar ca. €478 toe ten opzichte van alleen zonnepanelen.

## Zonnestroom zelf gebruiken

Overdag is er weinig verbruik in huis, dus een groot deel van de zonnestroom gaat zonder batterij terug het net op. Met de batterij gebruikt u 35% van de zonnestroom zelf in plaats van 21%.

| | Zonder batterij | Met batterij |
| --- | --- | --- |
| Opwek per jaar | 4.220 kWh | 4.220 kWh |
| Zelf gebruikt | 21% | 35% |
| Teruggeleverd | 3.320 kWh | 2.760 kWh |
| Ingekocht van het net | 1.100 kWh | 760 kWh |

- **Teruglevering is weinig waard:** zonder saldering krijgt u bij een dynamisch contract de uurprijs, en die is laag als de zon schijnt (in 2025 gemiddeld ca. €0,05 per kWh tijdens zonne-uren).
- **De batterij laadt ook van het net:** op goedkope uren 's nachts of midden op de dag, en levert op dure uren in de ochtend en avond. Daardoor stijgt de inkoop van het net soms, terwijl de kosten dalen.
- **Een tweede Venus E** (tot 3 op één fase) levert bij dit verbruik weinig extra op. Een warmtepomp verandert dat.

## Laden met de Zaptec Go 2

Thuis slim laden kost ca. €0,17 per kWh, tegen ca. €0,60 als u dezelfde kilometers op benzine rijdt. Bij 2.000 kWh per jaar scheelt dat ca. €850, plus ca. €230 ERE-vergoeding.

| | Per kWh | Per jaar (2.000 kWh) |
| --- | --- | --- |
| Dezelfde kilometers op benzine | €0,60 | €1.200 |
| Thuis laden, direct vanaf 18:00 | €0,22 | €442 |
| Thuis laden, slim op goedkope uren | €0,17 | €346 |
| ERE-vergoeding (netto) | −€0,115 | −€230 |

- **Zaptec Go 2:** tot 22 kW (3-fase, 32 A) of 7,4 kW (1-fase), met ingebouwde MID-gecertificeerde meter, 4G, OCPP en dynamische load balancing via de P1-meter. Bidirectioneel voorbereid (V2G).
- **Slim laden:** het EMS van Saldox laadt de auto op de goedkoopste uren dat hij thuis is, en in het weekend zoveel mogelijk met zonnestroom.
- **ERE:** sinds 1 januari 2026 levert elke thuis geladen kWh ERE's op. Voorwaarden: MID-meter in de laadpaal, gekoppeld aan uw aansluiting, en een inboekdienstverlener (één per jaar). Netto ca. €0,07 tot 0,15 per kWh, gemiddeld rond €0,12. De opbrengst kan schommelen.
- **Vergelijking met benzine:** 6 liter per 100 km à €2,00 tegenover 20 kWh per 100 km elektrisch; dat is ca. €0,60 per kWh. Laadt u nu al thuis aan het stopcontact, dan is de winst kleiner.

## Stroomcontract en prijzen

Het pakket werkt het best met een dynamisch contract: alleen dan kan de batterij goedkoop laden en duur leveren. Met een vast contract wordt het normale netto €1.310 per jaar (4,4 jaar).

| | Dynamisch (advies) | Vast |
| --- | --- | --- |
| Afname | Uurprijs plus opslag, btw en energiebelasting | Vaste prijs, ca. €0,28 per kWh incl. btw |
| Teruglevering | Uurprijs, bij veel leveranciers zonder terugleverkosten | Vergoeding ca. €0,10 min terugleverkosten €0,045 tot 0,065 |
| Zon per jaar | €360 | €420 |
| Batterij per jaar | €180 | €110 |
| Netto per jaar (normaal) | €1.580 | €1.310 |
| Terugverdientijd (normaal) | 3,6 jaar | 4,4 jaar |

- **Einde saldering per 1 januari 2027:** al verwerkt; dit plan rekent zonder saldering (zie *Met en zonder saldering*). Bij een vast contract moet de leverancier tot 2030 ten minste 50% van de kale leveringsprijs vergoeden; terugleverkosten mogen alleen de werkelijke kosten dekken en staan vanaf 2027 per kWh op de factuur.
- **Prijzen 2027:** door de oorlog met Iran ligt de groothandelsprijs voor stroom in 2027 op de termijnmarkt ca. 15% hoger dan in 2026. Dan wordt het normale netto ca. €1.430 per jaar (4,0 jaar).
- **Energiebelasting 2027:** stroom daalt naar €0,1065 per kWh incl. btw.

## Met en zonder saldering

Tot 1 januari 2027 mag u teruggeleverde stroom wegstrepen tegen stroom die u afneemt; daarna niet meer. Dit plan rekent met de situatie vanaf 2027. Met saldering zou het pakket normaal netto €1.630 per jaar opleveren, zonder €1.580.

| Dynamisch contract, normaal scenario | Met saldering (tot 2027) | Zonder saldering (vanaf 2027) |
| --- | --- | --- |
| Zon per jaar | €480 | €360 |
| Batterij per jaar | €150 | €180 |
| Thuis laden en ERE | €1.040 | €1.080 |
| Jaarlijkse kosten | −€40 | −€40 |
| **Netto per jaar** | **€1.630** | **€1.580** |
| Terugverdientijd | 3,5 jaar | 3,6 jaar |
| Netto per jaar bij een vast contract | €1.750 | €1.310 |

- **Wat saldering doet:** met saldering levert elke teruggeleverde kWh, tot uw jaarverbruik, ook de energiebelasting van €0,1108 per kWh op (bij een vast contract de volle kWh-prijs). Hier gaat het om ca. 760 kWh per jaar.
- **Zonnepanelen leveren minder op:** zonder saldering ca. €120 per jaar minder. Daarom telt zelf gebruiken vanaf 2027 zwaarder.
- **De batterij wordt belangrijker:** zonder saldering komt 33% van de opbrengst van zon en batterij uit de batterij, met saldering 24%. De batterij vangt de zonnestroom op die anders bijna niets oplevert.
- **Thuis laden:** met saldering is zonnestroom die in de auto gaat al de volle kWh-prijs waard; zonder saldering levert laden met eigen zonnestroom juist extra op.
- **Dit plan is niet afhankelijk van saldering:** de terugverdientijd van 3,6 jaar geldt voor de regels vanaf 2027.

## Installatie en veiligheid

De installatie is in één tot twee dagen klaar; de batterij hoort op een droge, vorstvrije plek met ruimte voor ventilatie.

- **A Solar 460 Wp (8×):** N-type, glas-glas, zwart; 1.762 × 1.134 mm per paneel, samen ca. 16 m² dak.
- **APsystems DS3 (4×):** micro-omvormer voor twee panelen, 880 VA, 2 MPPT's, rendement ca. 97%. Elk paneelpaar werkt apart, dus schaduw op één paneel kost weinig. Monitoring via de APsystems ECU-B.
- **Marstek Venus E 3.0:** LFP-batterij, 5,12 kWh, bruikbaar ca. 4,6 kWh, 2.500 W laden en ontladen op een eigen groep, rendement ca. 85% heen en terug, stand-by ca. 5 W. Meer dan 6.000 cycli, garantie 10 jaar. Het EMS van Saldox stuurt hem via Modbus TCP op de uurprijs.
- **Plaatsing:** op een eigen groep, nooit via een verlengsnoer of stekkerdoos; op een droge, geventileerde plek buiten de vluchtroute. De batterij schakelt zichzelf uit bij stroomuitval van het net.
- **Uitbreidbaar:** later kunnen er panelen met extra micro-omvormers bij, en tot 3 Venus E's op één fase.
- **Veiligheid:** PGS 37-1 geldt niet voor thuisbatterijen; ook de nieuwe batterijregels van 2028 zonderen thuisbatterijen uit. De installatie moet voldoen aan NEN 1010. Laat een erkende installateur installeren en meld de batterij bij de opstalverzekeraar.
- **Aanmelden:** meld de zonnepanelen en de batterij bij de netbeheerder via energieleveren.nl.

## Planning

Van akkoord tot werkend systeem duurt het ca. 4 tot 6 weken.

| Week | Wat |
| --- | --- |
| 1 | Schouw: dak, meterkast, plek batterij en laadpaal, ruimte in de groepenkast |
| 2 tot 3 | Bestellen en leveren; dynamisch contract regelen |
| 4 | Installatie panelen, micro-omvormers en batterij, laadpaal (1 tot 2 dagen) |
| 4 tot 5 | Aanmelden energieleveren.nl, EMS koppelen, ERE-inboekdienst kiezen, oplevering en uitleg |

## Aannames en te bevestigen

De cijfers gelden voor een standaard huishouden; vervang de aannames door de gegevens van de klant voordat het advies definitief is.

**Te bevestigen bij de klant**

- [ ] Jaarverbruik en verbruiksprofiel (slimme meter); aantal kilometers en huidige laadkosten van de auto
- [ ] Dak: plat of schuin (plat dak: montage vast €250), oriëntatie, hellingshoek, schaduw en ruimte voor 10 panelen (ca. 20 m²)
- [ ] Ruimte in de groepenkast voor een eigen groep voor de batterij
- [ ] Plek voor de batterij: droog, vorstvrij, bereikbaar
- [ ] Stroomcontract: dynamisch voor afname en teruglevering
- [ ] Offerte installateur voor de stelposten

**Aannames**

- Verbruik 2.000 kWh per jaar; opbrengst 917 kWh per kWp
- Uurprijzen en zonneprofiel van 2025; opslag dynamisch contract ca. €0,02 per kWh incl. btw; energiebelasting 2026
- Batterij 4,6 kWh bruikbaar, 2,5 kW, rendement 85% heen en terug, stand-by ca. 50 kWh per jaar
- Stand-by batterij en reservering €40 per jaar
- Plug-in hybride 2.000 kWh per jaar thuis; benzine omgerekend €0,60 per kWh; ERE €0,115 per kWh netto

## Begrippen

De technische termen in dit advies, in gewone taal.

| Begrip | Uitleg |
| --- | --- |
| Dynamisch contract | Stroomcontract met een prijs die elk uur verandert, voor afname en teruglevering. |
| EMS | Energiemanagementsysteem: de software van Saldox die batterij, laadpaal en omvormer op de uurprijs stuurt. |
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
