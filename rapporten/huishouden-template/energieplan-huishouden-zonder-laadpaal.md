# Energieplan huishouden: zon en batterij

7 oktober 2026 · Saldox · template voor een standaard huishouden

## Samenvatting

Het pakket kost €6.604,69 incl. btw en levert na de jaarlijkse kosten netto €495 tot €745 per jaar op; normaal is het in ca. 10,9 jaar terugverdiend (8,9 tot 13,3 jaar).

- **Zonnestroom:** 10 panelen van 450 Wp (4,5 kWp), ca. 4.130 kWh per jaar. Zonder batterij gebruikt u 26% zelf, met batterij 38%.
- **Thuisbatterij:** Sofar BTS 10 kWh (9,2 kWh bruikbaar) met een 3-fase ESI 10 kW hybride omvormer. Laadt goedkoop van het net en met zonnestroom, en levert op dure uren.
- **Stroomcontract:** dynamisch voor afname en teruglevering; het EMS van Saldox stuurt batterij op de uurprijs.
- **Zonnepanelen** verdienen zich het snelst terug (ca. 5,3 jaar); de batterij vooral via de prijsverschillen op een dynamisch contract.
- **Btw:** 0% op zonnepanelen, omvormer en montage; 21% op de batterij.

## Begroting

Het pakket kost €5.809,00 excl. btw en €6.604,69 incl. btw. Op zonnepanelen geldt het nultarief; de batterijset valt onder 21%.

| Post | Excl. btw | Btw | Incl. btw | Status |
| --- | --- | --- | --- | --- |
| 10 zonnepanelen à 450 Wp (10 × €77) | €770,00 | 0% | €770,00 | Inkoopprijs |
| Montage zonnepanelen | €800,00 | 0% | €800,00 | Stelpost |
| Dakbevestiging en bekabeling | €450,00 | 0% | €450,00 | Stelpost |
| Batterijset Sofar BTS 10 kWh (2× BTS 5K) met 3-fase ESI 10 kW hybride omvormer | €2.889,00 | 21% | €3.495,69 | Offerte |
| Installatie batterij en omvormer | €450,00 | 21% | €544,50 | Stelpost |
| Groepenkast: groepen voor zonnepanelen en batterij, aardlek | €300,00 | 21% | €363,00 | Stelpost |
| EMS-koppeling Saldox (P1-meter en gateway) | €150,00 | 21% | €181,50 | Stelpost |
| **Totaal** | **€5.809,00** | | **€6.604,69** | |

<!-- FIG:begroting -->

- **Nultarief:** de Belastingdienst rekent 0% btw op levering en installatie van zonnepanelen op of bij een woning, inclusief omvormer, bekabeling, montagemateriaal en aanpassingen in de meterkast voor de panelen.
- **Batterij 21%:** levering en installatie van een thuisbatterij vallen expliciet onder 21%. De batterijset wordt als één prijs geleverd en staat daarom volledig op 21%. Vraag de leverancier het omvormerdeel apart te factureren: dat deel kan onder het nultarief vallen.
- **Optie plat dak:** de montage kost bij een plat dak vast €250,00 (0% btw) in plaats van €800,00. Het pakket kost dan €6.054,69 incl. btw en is normaal in ca. 10,0 jaar terugverdiend.
- **Stelposten** zijn inschattingen voor een standaard woning. Vervang ze door de offerte van de installateur.
- **Aanname:** de woning heeft een 3-fase aansluiting (3x25 A). Is die 1-fase, dan is een verzwaring nodig of een 1-fase omvormer.

## Wat het per jaar oplevert

Normaal levert het pakket €680 per jaar op; na de reservering voor vervanging van de omvormer blijft €605 over.

| Per jaar | Pessimistisch | Normaal | Optimistisch |
| --- | --- | --- | --- |
| Zon (minder stroom inkopen, teruglevering) | €360 | €380 | €410 |
| Batterij (slim laden en ontladen) | €210 | €300 | €410 |
| **Bruto per jaar** | **€570** | **€680** | **€820** |
| Reservering vervanging omvormer | −€75 | −€75 | −€75 |
| **Netto per jaar** | **€495** | **€605** | **€745** |

<!-- FIG:waterval -->

**Hoe dit is berekend.** Saldox simuleert elk uur van een jaar met de echte uurprijzen van 2025 (EPEX day-ahead Nederland) en het echte zonneprofiel van Nederland. Het EMS zet de batterij in zoals in de praktijk: met de day-ahead prijzen, die een dag vooruit bekend zijn.

- **Pessimistisch / normaal / optimistisch:** opbrengst 861 / 917 / 1.032 kWh per kWp (PVGIS: oost-west, gemiddeld, zuid); batterij ×0,7 / ×1 / ×1,3 (in 2026 waren de prijsverschillen binnen een dag ca. 33% groter dan in 2025).
- **Stroomprijs:** uurprijs plus opslag van de leverancier (ca. €0,02 per kWh incl. btw), plus btw en energiebelasting (€0,1108 per kWh incl. btw in 2026). Teruglevering tegen de uurprijs, zonder terugleverkosten; bij een negatieve prijs zet het EMS de teruglevering stop.
- **Verbruik:** 2.500 kWh per jaar (Milieu Centraal: gemiddeld 2.430 kWh, 2 personen ca. 2.550 kWh) met een standaard dagprofiel: ochtend- en avondpiek, in de winter hoger.

## Terugverdientijd

Het pakket van €6.604,69 is normaal in ca. 10,9 jaar terugverdiend; pessimistisch in 13,3 jaar en optimistisch in 8,9 jaar.

<!-- FIG:kasstroom -->

| Onderdeel | Investering incl. btw | Netto per jaar (normaal) | Terugverdientijd (normaal) |
| --- | --- | --- | --- |
| Zonnepanelen (panelen, montage, bevestiging) | €2.020,00 | €380 | 5,3 jaar |
| Batterij (set met omvormer, installatie, groepenkast, EMS) | €4.584,69 | €225 | 20,4 jaar |
| **Totaal** | **€6.604,69** | **€605** | **10,9 jaar** |

<!-- FIG:payback -->

- **Zonnepanelen** verdienen zich snel terug, ook zonder saldering: het grootste deel van de waarde zit in de stroom die u zelf gebruikt.
- **De batterij** verdient minder dan de panelen: bij een verbruik van 2.500 kWh is 10 kWh ruim bemeten. Hij verdient sneller bij een groter verbruik (warmtepomp, elektrische auto) en bij grotere prijsverschillen. De reservering voor de omvormer staat bij de batterij.

## Zonnestroom zelf gebruiken

Overdag is er weinig verbruik in huis, dus een groot deel van de zonnestroom gaat zonder batterij terug het net op. Met de batterij gebruikt u 38% van de zonnestroom zelf in plaats van 26%.

| | Zonder batterij | Met batterij |
| --- | --- | --- |
| Opwek per jaar | 4.130 kWh | 4.130 kWh |
| Zelf gebruikt | 26% | 38% |
| Teruggeleverd | 3.050 kWh | 2.550 kWh |
| Ingekocht van het net | 1.430 kWh | 1.180 kWh |

- **Teruglevering is weinig waard:** zonder saldering krijgt u bij een dynamisch contract de uurprijs, en die is laag als de zon schijnt (in 2025 gemiddeld ca. €0,05 per kWh tijdens zonne-uren).
- **De batterij laadt ook van het net:** op goedkope uren 's nachts of midden op de dag, en levert op dure uren in de ochtend en avond. Daardoor stijgt de inkoop van het net soms, terwijl de kosten dalen.
- **Een tweede batterijmodule** levert bij dit verbruik weinig extra op. Een warmtepomp of elektrische auto verandert dat.

## Stroomcontract en prijzen

Het pakket werkt het best met een dynamisch contract: alleen dan kan de batterij goedkoop laden en duur leveren. Met een vast contract wordt het normale netto €535 per jaar (12,3 jaar).

| | Dynamisch (advies) | Vast |
| --- | --- | --- |
| Afname | Uurprijs plus opslag, btw en energiebelasting | Vaste prijs, ca. €0,28 per kWh incl. btw |
| Teruglevering | Uurprijs, bij veel leveranciers zonder terugleverkosten | Vergoeding ca. €0,10 min terugleverkosten €0,045 tot 0,065 |
| Zon per jaar | €380 | €450 |
| Batterij per jaar | €300 | €160 |
| Netto per jaar (normaal) | €605 | €535 |
| Terugverdientijd (normaal) | 10,9 jaar | 12,3 jaar |

- **Einde saldering per 1 januari 2027:** al verwerkt; dit plan rekent zonder saldering (zie *Met en zonder saldering*). Bij een vast contract moet de leverancier tot 2030 ten minste 50% van de kale leveringsprijs vergoeden; terugleverkosten mogen alleen de werkelijke kosten dekken en staan vanaf 2027 per kWh op de factuur.
- **Prijzen 2027:** door de oorlog met Iran ligt de groothandelsprijs voor stroom in 2027 op de termijnmarkt ca. 15% hoger dan in 2026. Dan wordt het normale netto ca. €685 per jaar (9,6 jaar).
- **Energiebelasting 2027:** stroom daalt naar €0,1065 per kWh incl. btw.

## Met en zonder saldering

Tot 1 januari 2027 mag u teruggeleverde stroom wegstrepen tegen stroom die u afneemt; daarna niet meer. Dit plan rekent met de situatie vanaf 2027. Met saldering zou het pakket normaal netto €735 per jaar opleveren, zonder €605.

| Dynamisch contract, normaal scenario | Met saldering (tot 2027) | Zonder saldering (vanaf 2027) |
| --- | --- | --- |
| Zon per jaar | €540 | €380 |
| Batterij per jaar | €270 | €300 |
| Jaarlijkse kosten | −€75 | −€75 |
| **Netto per jaar** | **€735** | **€605** |
| Terugverdientijd | 9,0 jaar | 10,9 jaar |
| Netto per jaar bij een vast contract | €695 | €535 |

- **Wat saldering doet:** met saldering levert elke teruggeleverde kWh, tot uw jaarverbruik, ook de energiebelasting van €0,1108 per kWh op (bij een vast contract de volle kWh-prijs). Hier gaat het om ca. 1.180 kWh per jaar.
- **Zonnepanelen leveren minder op:** zonder saldering ca. €160 per jaar minder. Daarom telt zelf gebruiken vanaf 2027 zwaarder.
- **De batterij wordt belangrijker:** zonder saldering komt 44% van de opbrengst van zon en batterij uit de batterij, met saldering 33%. De batterij vangt de zonnestroom op die anders bijna niets oplevert.
- **Dit plan is niet afhankelijk van saldering:** de terugverdientijd van 10,9 jaar geldt voor de regels vanaf 2027.

## Installatie en veiligheid

De installatie is in één tot twee dagen klaar; de batterij hoort op een droge, vorstvrije plek met ruimte voor ventilatie.

- **Sofar ESI 10K-T1:** 3-fase hybride omvormer, 10 kW, tot 20 kWp zonnepanelen op 3 MPPT's, noodstroom (EPS) op alle drie de fasen, rendement tot 98,2%. Communicatie via RS485, CAN en wifi; het EMS van Saldox leest en stuurt hem uit.
- **Sofar BTS 5K (2×):** LFP-batterij, 5,12 kWh per module, samen 10,24 kWh, bruikbaar ca. 9,2 kWh (90%). Laden en ontladen tot 5 kW. Garantie 10 jaar: 70% capaciteit na 10 jaar of 11,3 MWh doorvoer per module.
- **Uitbreidbaar:** de omvormer kan tot 20 kWp panelen aan; er kunnen later panelen of een laadpaal bij.
- **Veiligheid:** PGS 37-1 geldt niet voor thuisbatterijen; ook de nieuwe batterijregels van 2028 zonderen thuisbatterijen uit. De installatie moet voldoen aan NEN 1010. Laat een erkende installateur installeren en meld de batterij bij de opstalverzekeraar.
- **Aanmelden:** meld de zonnepanelen en de batterij bij de netbeheerder via energieleveren.nl.

## Planning

Van akkoord tot werkend systeem duurt het ca. 4 tot 6 weken.

| Week | Wat |
| --- | --- |
| 1 | Schouw: dak, meterkast, plek batterij, 3-fase aansluiting |
| 2 tot 3 | Bestellen en leveren; dynamisch contract regelen |
| 4 | Installatie panelen, omvormer en batterij (1 tot 2 dagen) |
| 4 tot 5 | Aanmelden energieleveren.nl, EMS koppelen, oplevering en uitleg |

## Aannames en te bevestigen

De cijfers gelden voor een standaard huishouden; vervang de aannames door de gegevens van de klant voordat het advies definitief is.

**Te bevestigen bij de klant**

- [ ] Jaarverbruik en verbruiksprofiel (slimme meter)
- [ ] Dak: plat of schuin (plat dak: montage vast €250), oriëntatie, hellingshoek, schaduw en ruimte voor 10 panelen (ca. 20 m²)
- [ ] 3-fase aansluiting (3x25 A) en ruimte in de meterkast
- [ ] Plek voor de batterij: droog, vorstvrij, bereikbaar
- [ ] Stroomcontract: dynamisch voor afname en teruglevering
- [ ] Offerte installateur voor de stelposten

**Aannames**

- Verbruik 2.500 kWh per jaar; opbrengst 917 kWh per kWp
- Uurprijzen en zonneprofiel van 2025; opslag dynamisch contract ca. €0,02 per kWh incl. btw; energiebelasting 2026
- Batterij 9,2 kWh bruikbaar, 5 kW, rendement 90% heen en terug
- Reservering vervanging omvormer €75 per jaar

## Begrippen

De technische termen in dit advies, in gewone taal.

| Begrip | Uitleg |
| --- | --- |
| Dynamisch contract | Stroomcontract met een prijs die elk uur verandert, voor afname en teruglevering. |
| EMS | Energiemanagementsysteem: de software van Saldox die batterij en omvormer op de uurprijs stuurt. |
| ERE | Emissiereductie-eenheid: vergoeding voor stroom die in een elektrische auto wordt geladen, via een inboekdienstverlener. |
| Hybride omvormer | Omvormer die zonnepanelen én batterij aansluit en bij stroomuitval noodstroom kan leveren. |
| kWh en kWp | kWh is een hoeveelheid energie; kWp is het piekvermogen van zonnepanelen. |
| LFP | Lithium-ijzerfosfaat: veilige, lang meegaande batterijchemie. |
| MID-meter | Geijkte kWh-meter; nodig voor de ERE-vergoeding. |
| Nultarief | 0% btw op zonnepanelen en hun installatie bij woningen. |
| Saldering | Wegstrepen van teruggeleverde tegen afgenomen stroom; stopt per 1 januari 2027. |
| Stelpost | Geschat bedrag voor een post waarvan de exacte prijs nog niet bekend is. |
| Zelfverbruik | Het deel van de zonnestroom dat u zelf gebruikt in plaats van terug te leveren. |
