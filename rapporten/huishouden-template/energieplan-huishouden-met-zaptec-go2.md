# Energieplan huishouden: met laadpaal

7 oktober 2026 · Saldox · huishouden met 5.000 kWh per jaar en een plug-in hybride

## Samenvatting

Het pakket kost €9.514,11 incl. btw en levert na de jaarlijkse kosten netto €1.125 tot €1.695 per jaar op; normaal is het in ca. 6,7 jaar terugverdiend (5,6 tot 8,5 jaar).

- **Zonnestroom:** 10 panelen van 450 Wp (4,5 kWp), ca. 4.130 kWh per jaar. Zonder batterij gebruikt u 37% zelf, met batterij 53%.
- **Thuisbatterij:** Sofar BTS 20 kWh (4× BTS 5K, 18,4 kWh bruikbaar) met een 3-fase ESI 10 kW hybride omvormer. Laadt goedkoop van het net en met zonnestroom, en levert op dure uren.
- **Stroomcontract:** dynamisch voor afname en teruglevering; het EMS van Saldox stuurt batterij en laadpaal op de uurprijs.
- **Laadpaal:** Zaptec Go 2 voor eigen gebruik, slim laden op goedkope uren. Thuis laden kost ca. €0,17 per kWh tegen ca. €0,60 op benzine, plus ERE-vergoeding.
- **Zonnepanelen** verdienen zich het snelst terug (ca. 4,4 jaar); de batterij vooral via de prijsverschillen op een dynamisch contract.
- **Btw:** 0% op zonnepanelen, omvormer en montage; 21% op de batterij en de laadpaal.

## Begroting

Het pakket kost €8.201,33 excl. btw en €9.514,11 incl. btw. Op zonnepanelen geldt het nultarief; de batterijset valt onder 21%.

| Post | Excl. btw | Btw | Incl. btw | Status |
| --- | --- | --- | --- | --- |
| 10 zonnepanelen à 450 Wp (10 × €70) | €700,00 | 0% | €700,00 | Inkoopprijs |
| Montage zonnepanelen | €800,00 | 0% | €800,00 | Stelpost |
| Dakbevestiging en bekabeling | €450,00 | 0% | €450,00 | Stelpost |
| Batterijset Sofar BTS 10 kWh (2× BTS 5K) met 3-fase ESI 10 kW hybride omvormer | €2.889,00 | 21% | €3.495,69 | Offerte |
| 2 extra batterijmodules Sofar BTS 5K (2 × €600), samen 20,48 kWh | €1.200,00 | 21% | €1.452,00 | Inkoopprijs |
| Installatie batterij en omvormer | €450,00 | 21% | €544,50 | Stelpost |
| Groepenkast: groepen voor zonnepanelen en batterij, aardlek | €300,00 | 21% | €363,00 | Stelpost |
| EMS-koppeling Saldox (P1-meter en gateway) | €150,00 | 21% | €181,50 | Stelpost |
| Zaptec Go 2 laadpaal (22 kW, MID-meter) | €682,33 | 21% | €825,62 | Opgegeven |
| Installatie laadpaal incl. groep en bekabeling | €580,00 | 21% | €701,80 | Stelpost |
| **Totaal** | **€8.201,33** | | **€9.514,11** | |

<!-- FIG:begroting -->

- **Nultarief:** de Belastingdienst rekent 0% btw op levering en installatie van zonnepanelen op of bij een woning, inclusief omvormer, bekabeling, montagemateriaal en aanpassingen in de meterkast voor de panelen.
- **Batterij 21%:** levering en installatie van een thuisbatterij vallen expliciet onder 21%. De batterijset wordt als één prijs geleverd en staat daarom volledig op 21%. Vraag de leverancier het omvormerdeel apart te factureren: dat deel kan onder het nultarief vallen.
- **Optie plat dak:** de montage kost bij een plat dak vast €250,00 (0% btw) in plaats van €800,00. Het pakket kost dan €8.964,11 incl. btw en is normaal in ca. 6,3 jaar terugverdiend.
- **Stelposten** zijn inschattingen voor een standaard woning. Vervang ze door de offerte van de installateur.
- **Aanname:** de woning heeft een 3-fase aansluiting (3x25 A). Is die 1-fase, dan is een verzwaring nodig of een 1-fase omvormer.

## Wat het per jaar oplevert

Normaal levert het pakket €1.490 per jaar op; na de reservering voor vervanging van de omvormer blijft €1.415 over.

| Per jaar | Pessimistisch | Normaal | Optimistisch |
| --- | --- | --- | --- |
| Zon (minder stroom inkopen, teruglevering) | €420 | €440 | €480 |
| Batterij (slim laden en ontladen) | €300 | €440 | €610 |
| Thuis laden in plaats van op benzine | €370 | €480 | €540 |
| ERE-vergoeding laadpaal | €110 | €130 | €140 |
| **Bruto per jaar** | **€1.200** | **€1.490** | **€1.770** |
| Reservering vervanging omvormer | −€75 | −€75 | −€75 |
| **Netto per jaar** | **€1.125** | **€1.415** | **€1.695** |

<!-- FIG:waterval -->

**Hoe dit is berekend.** Saldox simuleert elk uur van een jaar met de echte uurprijzen van 2025 (EPEX day-ahead Nederland) en het echte zonneprofiel van Nederland. Het EMS zet de batterij in zoals in de praktijk: met de day-ahead prijzen, die een dag vooruit bekend zijn.

- **Pessimistisch / normaal / optimistisch:** opbrengst 861 / 917 / 1.032 kWh per kWp (PVGIS: oost-west, gemiddeld, zuid); batterij ×0,7 / ×1 / ×1,3 (in 2026 waren de prijsverschillen binnen een dag ca. 33% groter dan in 2025); benzine omgerekend €0,50 / €0,60 / €0,66 per kWh; ERE €0,10 / €0,115 / €0,13 per kWh.
- **Stroomprijs:** uurprijs plus opslag van de leverancier (ca. €0,02 per kWh incl. btw), plus btw en energiebelasting (€0,1108 per kWh incl. btw in 2026). Teruglevering tegen de uurprijs, zonder terugleverkosten; bij een negatieve prijs zet het EMS de teruglevering stop.
- **Verbruik:** 3.900 kWh per jaar (opgegeven: 5.000 kWh per jaar in totaal, waarvan ca. 1.100 kWh voor de plug-in hybride; het huis zelf ca. 3.900 kWh) met een standaard dagprofiel: ochtend- en avondpiek, in de winter hoger.
- **Plug-in hybride:** 1.100 kWh per jaar thuis geladen (ca. 5.500 km per jaar elektrisch à 20 kWh per 100 km).

## Terugverdientijd

Het pakket van €9.514,11 is normaal in ca. 6,7 jaar terugverdiend; pessimistisch in 8,5 jaar en optimistisch in 5,6 jaar.

<!-- FIG:kasstroom -->

| Onderdeel | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd (normaal) |
| --- | --- | --- | --- |
| Zonnepanelen (panelen, montage, bevestiging) | €1.950,00 | €440 | 4,4 jaar |
| Batterij (set met omvormer, installatie, groepenkast, EMS) | €6.036,69 | €365 | 16,5 jaar |
| Laadpaal (Zaptec Go 2 en installatie) | €1.527,42 | €610 | 2,5 jaar |
| **Totaal** | **€9.514,11** | **€1.415** | **6,7 jaar** |

<!-- FIG:payback -->

- **Zonnepanelen** verdienen zich snel terug, ook zonder saldering: het grootste deel van de waarde zit in de stroom die u zelf gebruikt.
- **De batterij** verdient minder dan de panelen: 20 kWh is ruim voor een verbruik van 3.900 kWh; de twee extra modules leveren vooral extra op bij het laden van de auto. Hij verdient sneller bij een groter verbruik (warmtepomp) en bij grotere prijsverschillen. De reservering voor de omvormer staat bij de batterij.
- **De laadpaal** verdient zich het snelst terug, omdat thuis laden veel goedkoper is dan dezelfde kilometers op benzine rijden. Laadt u nu al thuis aan een gewone laadpaal, dan is de winst kleiner: dan bespaart slim laden ca. €24 per jaar, plus de ERE-vergoeding.

## Batterijgrootte en verwarming

Een grotere batterij spaart meer, maar elke extra kWh levert minder op dan de vorige. Met een warmtepomp verbruikt u meer stroom, vooral in de winter; dan verdient een grotere batterij meer. Per batterijgrootte: de netto besparing van het hele pakket per jaar (normaal scenario) en de terugverdientijd.

| Batterij | Pakket incl. btw | Gewoon gas | Minimaal op gas | Van het gas af |
| --- | --- | --- | --- | --- |
| 10 kWh | €8.062,11 | €1.305 · 6,2 jaar | €1.355 · 5,9 jaar | €1.425 · 5,7 jaar |
| **20 kWh (dit pakket)** | €9.514,11 | €1.415 · 6,7 jaar | €1.465 · 6,5 jaar | €1.565 · 6,1 jaar |
| 30 kWh | €11.329,11 | €1.465 · 7,7 jaar | €1.515 · 7,5 jaar | €1.625 · 7,0 jaar |
| 40 kWh | €15.369,30 | €1.460 · 10,5 jaar | €1.520 · 10,1 jaar | €1.630 · 9,4 jaar |
| 50 kWh | €17.547,30 | €1.490 · 11,8 jaar | €1.570 · 11,2 jaar | €1.670 · 10,5 jaar |

- **Advies:** in alle drie de situaties is 10 kWh het snelst terugverdiend. 50 kWh spaart het meest, maar €185 tot €245 per jaar meer dan 10 kWh weegt niet op tegen €9.485,19 extra investering.
- **Warmtepomp:** bij dit pakket levert de batterij met gewoon gas €440 per jaar op, en zonder gas €570. De warmtepomp zelf zit niet in de investering, en de besparing op gas telt hier niet mee.
- **Verwarming, aannames:** gewoon gas: cv-ketel; minimaal op gas: hybride warmtepomp, ca. 1.500 kWh per jaar; van het gas af: volledige warmtepomp met tapwater, ca. 3.500 kWh per jaar. Het warmtepompverbruik volgt de buitentemperatuur per uur (KNMI Eindhoven 2025).
- **Techniek:** 10 kWh is 2 BTS 5K-modules (laden tot 5 kW), 20 kWh 4, 30 kWh 6 (tot 10 kW). Tot 30 kWh volstaat één Sofar ESI 10K (maximaal 6 modules; vanaf 5 modules een tweede toren met uitbreidingskit, stelpost €300,00). Voor 40 en 50 kWh (8 en 10 modules) is een tweede omvormerset nodig; samen laden en ontladen ze met ca. 17 kW, de grens van een 3x25 A-aansluiting.
- **Prijzen:** extra modules à €600,00 excl. btw; een tweede set kost €2.889,00 plus €750,00 installatie en groep (stelpost), en €75 per jaar extra reservering voor de omvormer.

## Zonnestroom zelf gebruiken

Overdag is er weinig verbruik in huis, dus een groot deel van de zonnestroom gaat zonder batterij terug het net op. Met de batterij gebruikt u 53% van de zonnestroom zelf in plaats van 37%.

| | Zonder batterij | Met batterij |
| --- | --- | --- |
| Opwek per jaar | 4.130 kWh | 4.130 kWh |
| Zelf gebruikt | 37% | 53% |
| Teruggeleverd | 2.610 kWh | 2.380 kWh |
| Ingekocht van het net | 2.390 kWh | 2.560 kWh |

- **Teruglevering is weinig waard:** zonder saldering krijgt u bij een dynamisch contract de uurprijs, en die is laag als de zon schijnt (in 2025 gemiddeld ca. €0,05 per kWh tijdens zonne-uren).
- **De batterij laadt ook van het net:** op goedkope uren 's nachts of midden op de dag, en levert op dure uren in de ochtend en avond. Daardoor stijgt de inkoop van het net soms, terwijl de kosten dalen.
- **Batterij op maximum:** met 4 modules is één BDU vol. Meer opslag vraagt een tweede batterijtoren.

## Laden met de Zaptec Go 2

Thuis slim laden kost ca. €0,17 per kWh, tegen ca. €0,60 als u dezelfde kilometers op benzine rijdt. Bij 1.100 kWh per jaar scheelt dat ca. €480, plus ca. €130 ERE-vergoeding.

| | Per kWh | Per jaar (1.100 kWh) |
| --- | --- | --- |
| Dezelfde kilometers op benzine | €0,60 | €660 |
| Thuis laden, direct vanaf 18:00 | €0,19 | €208 |
| Thuis laden, slim op goedkope uren | €0,17 | €184 |
| ERE-vergoeding (netto) | −€0,115 | −€130 |

- **Zaptec Go 2:** tot 22 kW (3-fase, 32 A) of 7,4 kW (1-fase), met ingebouwde MID-gecertificeerde meter, 4G, OCPP en dynamische load balancing via de P1-meter. Bidirectioneel voorbereid (V2G).
- **Slim laden:** het EMS van Saldox laadt de auto op de goedkoopste uren dat hij thuis is, en in het weekend zoveel mogelijk met zonnestroom.
- **ERE:** sinds 1 januari 2026 levert elke thuis geladen kWh ERE's op. Voorwaarden: MID-meter in de laadpaal, gekoppeld aan uw aansluiting, en een inboekdienstverlener (één per jaar). Netto ca. €0,07 tot 0,15 per kWh, gemiddeld rond €0,12. De opbrengst kan schommelen.
- **Vergelijking met benzine:** 6 liter per 100 km à €2,00 tegenover 20 kWh per 100 km elektrisch; dat is ca. €0,60 per kWh. Laadt u nu al thuis aan het stopcontact, dan is de winst kleiner.

## Elektrisch rijden met een plug-in hybride

Hoe meer kilometers u elektrisch rijdt, hoe meer u bespaart. Voor een plug-in hybride met 60 km elektrisch bereik: de besparing per jaar ten opzichte van dezelfde kilometers op benzine, na de kosten van thuis laden en inclusief de ERE-vergoeding.

| Kilometers per jaar | 20% elektrisch | 40% elektrisch | 60% elektrisch | 80% elektrisch | 100% elektrisch |
| --- | --- | --- | --- | --- | --- |
| 15.000 km | €330 | €660 | €980 | €1.310 | €1.630 |
| 20.000 km | €440 | €870 | €1.310 | €1.740 | €2.160* |
| 25.000 km | €550 | €1.090 | €1.630 | €2.160* | €2.690* |

- **Per elektrische kilometer** bespaart u ca. €0,11: benzine kost ca. €0,12 per km, thuis laden met zon en batterij ca. €0,03, en de ERE-vergoeding levert ca. €0,02 op.
- **Voorbeeld:** bij 15.000 km per jaar en 60% elektrisch laadt u ca. 1.800 kWh per jaar thuis en bespaart u €980.
- **\* Alleen met extra laden:** met 60 km bereik en één keer per dag thuis laden rijdt u op 300 ritdagen hooguit ca. 18.000 km per jaar elektrisch. Meer kan alleen als u ook op het werk of onderweg laadt.
- **Aannames:** 20 kWh per 100 km elektrisch (incl. laadverlies), 6 liter per 100 km op benzine à €2,00, laden met 7,4 kW op de goedkoopste uren. De ERE-vergoeding is €0,115 per kWh (normaal).

## Stroomcontract en prijzen

Het pakket werkt het best met een dynamisch contract: alleen dan kan de batterij goedkoop laden en duur leveren. Met een vast contract wordt het normale netto €1.185 per jaar (8,0 jaar).

| | Dynamisch (advies) | Vast |
| --- | --- | --- |
| Afname | Uurprijs plus opslag, btw en energiebelasting | Vaste prijs, ca. €0,28 per kWh incl. btw |
| Teruglevering | Uurprijs, bij veel leveranciers zonder terugleverkosten | Vergoeding ca. €0,10 min terugleverkosten €0,045 tot 0,065 |
| Zon per jaar | €440 | €550 |
| Batterij per jaar | €440 | €230 |
| Netto per jaar (normaal) | €1.415 | €1.185 |
| Terugverdientijd (normaal) | 6,7 jaar | 8,0 jaar |

- **Einde saldering per 1 januari 2027:** al verwerkt; dit plan rekent zonder saldering (zie *Met en zonder saldering*). Bij een vast contract moet de leverancier tot 2030 ten minste 50% van de kale leveringsprijs vergoeden; terugleverkosten mogen alleen de werkelijke kosten dekken en staan vanaf 2027 per kWh op de factuur.
- **Prijzen 2027:** door de oorlog met Iran ligt de groothandelsprijs voor stroom in 2027 op de termijnmarkt ca. 15% hoger dan in 2026. Dan wordt het normale netto ca. €1.405 per jaar (6,8 jaar).
- **Energiebelasting 2027:** stroom daalt naar €0,1065 per kWh incl. btw.

## Met en zonder saldering

Tot 1 januari 2027 mag u teruggeleverde stroom wegstrepen tegen stroom die u afneemt; daarna niet meer. Dit plan rekent met de situatie vanaf 2027. Met saldering zou het pakket normaal netto €1.525 per jaar opleveren, zonder €1.415.

| Dynamisch contract, normaal scenario | Met saldering (tot 2027) | Zonder saldering (vanaf 2027) |
| --- | --- | --- |
| Zon per jaar | €710 | €440 |
| Batterij per jaar | €440 | €440 |
| Thuis laden en ERE | €450 | €610 |
| Jaarlijkse kosten | −€75 | −€75 |
| **Netto per jaar** | **€1.525** | **€1.415** |
| Terugverdientijd | 6,2 jaar | 6,7 jaar |
| Netto per jaar bij een vast contract | €1.385 | €1.185 |

- **Wat saldering doet:** met saldering levert elke teruggeleverde kWh, tot uw jaarverbruik, ook de energiebelasting van €0,1108 per kWh op (bij een vast contract de volle kWh-prijs). Hier gaat het om ca. 2.380 kWh per jaar.
- **Zonnepanelen leveren minder op:** zonder saldering ca. €270 per jaar minder. Daarom telt zelf gebruiken vanaf 2027 zwaarder.
- **De batterij wordt belangrijker:** zonder saldering komt 50% van de opbrengst van zon en batterij uit de batterij, met saldering 38%. De batterij vangt de zonnestroom op die anders bijna niets oplevert.
- **Thuis laden:** met saldering is zonnestroom die in de auto gaat al de volle kWh-prijs waard; zonder saldering levert laden met eigen zonnestroom juist extra op.
- **Dit plan is niet afhankelijk van saldering:** de terugverdientijd van 6,7 jaar geldt voor de regels vanaf 2027.

## Installatie en veiligheid

De installatie is in één tot twee dagen klaar; de batterij hoort op een droge, vorstvrije plek met ruimte voor ventilatie.

- **Sofar ESI 10K-T1:** 3-fase hybride omvormer, 10 kW, tot 20 kWp zonnepanelen op 3 MPPT's, noodstroom (EPS) op alle drie de fasen, rendement tot 98,2%. Communicatie via RS485, CAN en wifi; het EMS van Saldox leest en stuurt hem uit.
- **Sofar BTS 5K (4×):** LFP-batterij, 5,12 kWh per module, samen 20,48 kWh, bruikbaar ca. 18,4 kWh (90%). Laden en ontladen tot 10 kW, het maximum van de omvormer. Garantie 10 jaar: 70% capaciteit na 10 jaar of 11,3 MWh doorvoer per module.
- **Uitbreidbaar:** de omvormer kan tot 20 kWp panelen aan; er kunnen later panelen bij.
- **Veiligheid:** PGS 37-1 geldt niet voor thuisbatterijen; ook de nieuwe batterijregels van 2028 zonderen thuisbatterijen uit. De installatie moet voldoen aan NEN 1010. Laat een erkende installateur installeren en meld de batterij bij de opstalverzekeraar.
- **Aanmelden:** meld de zonnepanelen en de batterij bij de netbeheerder via energieleveren.nl.

## Planning

Van akkoord tot werkend systeem duurt het ca. 4 tot 6 weken.

| Week | Wat |
| --- | --- |
| 1 | Schouw: dak, meterkast, plek batterij en laadpaal, 3-fase aansluiting |
| 2 tot 3 | Bestellen en leveren; dynamisch contract regelen |
| 4 | Installatie panelen, omvormer en batterij, laadpaal (1 tot 2 dagen) |
| 4 tot 5 | Aanmelden energieleveren.nl, EMS koppelen, ERE-inboekdienst kiezen, oplevering en uitleg |

## Aannames en te bevestigen

De cijfers gelden voor een standaard huishouden; vervang de aannames door de gegevens van de klant voordat het advies definitief is.

**Te bevestigen bij de klant**

- [ ] Jaarverbruik en verbruiksprofiel (slimme meter); aantal kilometers en huidige laadkosten van de auto
- [ ] Dak: plat of schuin (plat dak: montage vast €250), oriëntatie, hellingshoek, schaduw en ruimte voor 10 panelen (ca. 20 m²)
- [ ] 3-fase aansluiting (3x25 A) en ruimte in de meterkast
- [ ] Plek voor de batterij: droog, vorstvrij, bereikbaar
- [ ] Stroomcontract: dynamisch voor afname en teruglevering
- [ ] Offerte installateur voor de stelposten

**Aannames**

- Verbruik 3.900 kWh per jaar; opbrengst 917 kWh per kWp
- Uurprijzen en zonneprofiel van 2025; opslag dynamisch contract ca. €0,02 per kWh incl. btw; energiebelasting 2026
- Batterij 18,4 kWh bruikbaar, 10 kW, rendement 90% heen en terug
- Reservering vervanging omvormer €75 per jaar
- Plug-in hybride 1.100 kWh per jaar thuis; benzine omgerekend €0,60 per kWh; ERE €0,115 per kWh netto

## Begrippen

De technische termen in dit advies, in gewone taal.

| Begrip | Uitleg |
| --- | --- |
| Dynamisch contract | Stroomcontract met een prijs die elk uur verandert, voor afname en teruglevering. |
| EMS | Energiemanagementsysteem: de software van Saldox die batterij, laadpaal en omvormer op de uurprijs stuurt. |
| ERE | Emissiereductie-eenheid: vergoeding voor stroom die in een elektrische auto wordt geladen, via een inboekdienstverlener. |
| Hybride omvormer | Omvormer die zonnepanelen én batterij aansluit en bij stroomuitval noodstroom kan leveren. |
| kWh en kWp | kWh is een hoeveelheid energie; kWp is het piekvermogen van zonnepanelen. |
| LFP | Lithium-ijzerfosfaat: veilige, lang meegaande batterijchemie. |
| MID-meter | Geijkte kWh-meter; nodig voor de ERE-vergoeding. |
| Nultarief | 0% btw op zonnepanelen en hun installatie bij woningen. |
| Saldering | Wegstrepen van teruggeleverde tegen afgenomen stroom; stopt per 1 januari 2027. |
| Stelpost | Geschat bedrag voor een post waarvan de exacte prijs nog niet bekend is. |
| Zelfverbruik | Het deel van de zonnestroom dat u zelf gebruikt in plaats van terug te leveren. |
