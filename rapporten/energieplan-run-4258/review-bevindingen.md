# Review energieplan Run 4258: fouten, inconsistenties en ontbrekende punten

Alle bedragen en totalen in het rapport kloppen rekenkundig (`check.py`: begroting, btw, opties, per maatregel, scenario's, laadplan, energie per werkdag, EMS). De punten hieronder gaan over aannames, interne tegenstrijdigheden en wat er nog ontbreekt. Het rapport zelf is níet aangepast, omdat de inhoud en cijfers gelijk moesten blijven.

## A. Inconsistenties in de tekst

| # | Waar | Wat | Voorstel |
|---|---|---|---|
| A1 | Samenvatting/§03 vs §05 | Zon + batterij "ca. 2,5 tot 3 jaar" (bruto, zonder dakinspectie en brandveilige opstelling) tegenover zon 3,4–4,0 jaar en batterij 3,7 jaar/niet in §05 (netto). Twee terugverdientijden voor dezelfde onderdelen verwarren de lezer. | Zet in §03 duidelijk "bruto" in de kop, of laat §03 weg en houd §05 aan. |
| A2 | ERE-alinea vs laadplan | ERE-voorbeeld rekent met 5.000 kWh per jaar; het laadplan met 7.800 tot 10.400 kWh. | Gebruik in beide hetzelfde laadvolume. |
| A3 | Laadplan "Nog niet meegerekend" | Zegt dat de backoffice niet is meegerekend; de scenario's trekken wel €240–480 backoffice af. | Verduidelijk dat dit alleen voor het rekenmodel in dat hoofdstuk geldt. |
| A4 | Leegstand | Spreekt van minder "stroomverkoop", maar de scenario's zijn model A (geen stroomverkoop). | Splits: model A alleen laadpalen, model B ook stroom. |
| A5 | Netwerk: poorten | "Poorten" telt 15 (4 AP + 10 patch + uplink); "Bekabeling" telt 14 en vergeet de uplink. Bekabelde aansluiting én patchpoort per unit komt uit op 25 poorten. | Eén telling; bij beide diensten tegelijk is een tweede switch nodig. De uplink kan via SFP+, dan vervalt één RJ45. |
| A6 | Airco's | "ca. 12 binnenunits voor 10 units", maar de projectomschrijving noemt 5 wijzigingen (1 nieuw, 1 naar verwarmen, 3 wand→plafond). Onduidelijk wat de offerte van €23.487,80 precies dekt. | Aantal binnenunits per offerteregel vermelden. |
| A7 | Model B-rekenvoorbeeld | Teruglevering (ca. 2.475 kWh × €0,08 ≈ €200) ontbreekt in model B en zit wel in model A (€3.650). Het verschil tussen de modellen lijkt daardoor ca. €200 kleiner dan het is. | Teruglevering toevoegen of vermelden. |
| A8 | Begrippenlijst | "DC/AC-verhouding" staat erin maar komt in de tekst niet voor. Er ontbreken: EIA, KIA, PGS 37-1, BMS, F-gas, Modbus/RS485, AVG, ACM, rendement/COP, netcongestie, Energiewet. | Aanvullen. |

## B. Aannames die het resultaat sterk beïnvloeden

1. **85% direct verbruik van zonnestroom is optimistisch.** Ca. 2/7 van de opwek (≈ 4.700 kWh) valt in het weekend, terwijl kantoren leeg zijn en de koeling volledig uit staat. Een zomerse weekenddag levert ca. 90 kWh, de batterij neemt er ca. 45 op. Per 10 procentpunt minder direct verbruik gaat er ca. 1.650 kWh × (€0,25 − €0,08) ≈ **€280 per jaar** af.
2. **Verbruik 36.000 kWh: wat zit erin?** De extra airco-verwarming (ca. 5.000 kWh) en de laadpalen (7.800 tot 10.400 kWh) lijken er niet in te zitten. Voor de zon is dat gunstig (meer eigen verbruik), maar voor de 3x25 A en de energieprijs niet. Bevestig het verbruik met meetdata (slimme meter, 15-minutenwaarden).
3. **Terugleverkosten.** Na het einde van de saldering rekenen veel leveranciers terugleverkosten. Dan kan €0,08 per teruggeleverde kWh netto ook €0 of minder worden.
4. **Stroomprijs vast op €0,25, geen indexatie of disconto.** Het gaat om een eenvoudige terugverdientijd. Voor een investeringsbeslissing is een NCW/IRR over 15 jaar met degradatie van de panelen (ca. 0,5% per jaar) beter verdedigbaar.
5. **Batterij €50 per kWh.** Al gemarkeerd in het rapport. Dit is de grootste hefboom: tegen marktprijs (€500 per kWh) wordt het normale scenario ca. 10,6 jaar (€71.488 / €6.762).

## C. Ontbrekend in begroting of planning

- **Post onvoorzien.** Ca. €13.200 bestaat uit stelposten en er is geen onvoorzien. Gebruikelijk is 10% (ca. €4.900); bij de normale opbrengst wordt de terugverdientijd dan ca. 8,0 jaar.
- **Elektra rond omvormer en batterij:** AC-kabel, groepenkast/aardlek, overspanningsbeveiliging. Nu is alleen de verdeelkast voor de units genoemd.
- **Engineering en projectbegeleiding**, plus de aanmelding bij Enexis en het energieloket.
- **Overstap naar een dynamisch contract**, de voorwaarde voor de batterijbesparing, en de looptijd van het huidige contract.
- **Zonenregeling kelder** en **zwaardere aansluiting**: al genoemd als "nog niet meegerekend", maar zonder bandbreedte.
- **Planning zonder speling:** levertijd van een F-gas-gecertificeerde installateur, PGS 37-1-goedkeuring van de batterijruimte vóór week 9 en de testperiode van EMS/app (1 week) zitten krap in 14 weken.
- **Weekend zonder koeling, ook niet handmatig:** dit botst met huurders die in het weekend werken. Leg het vast in het huurcontract of maak een uitzondering op verzoek.
- **Energiewet (2026):** zelf stroom leveren aan huurders in model B kan onder de nieuwe leveringsregels vallen. Het rapport noemt dit al als juridisch controlepunt; zet het als blokkerend punt vóór de keuze A/B.
- **EIA/KIA** zijn niet meegerekend. Dat is voordeel voor de verhuurder, maar de 3-maandentermijn voor de EIA maakt het een harde planningsmijlpaal.

## D. Stijl

- De opdracht noemt themakleur `#0f7a3e`. De site gebruikt in de CSS `#0b3d2e`, `#1f6f4a` en `#2fa56b` (die kleur komt alleen uit het manifest). Het rapport volgt de CSS-tokens van de site.
- Saldox spreekt de lezer aan met "u". De drie keer "jullie" in de bron zijn in de HTML/PDF omgezet naar "u" (zie `TONE` in `build.py`); verder is de tekst letterlijk.
