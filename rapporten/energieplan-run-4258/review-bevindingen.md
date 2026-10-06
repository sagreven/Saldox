# Review energieplan Run 4258: validatie en correcties

Stand 5 oktober 2026. Alle uitspraken in het rapport zijn gecontroleerd: rekenkundig met `check.py` en `model.py`, inhoudelijk met bronnen. De prijzen van airco's, zonnepanelen, batterij en omvormer zijn gegeven door de opdrachtgever en zijn niet gecontroleerd.

## 1. Herberekend (rekenmodel)

`model.py` reproduceert met de oorspronkelijke aannames exact de oude getallen en rekent daarna met de actuele aannames.

| Aanname | Was | Nu | Bron |
|---|---|---|---|
| Stroomprijs excl. btw | €0,25 | €0,21 | CBS 85592NED (variabel leveringstarief augustus 2026 ca. €0,12) + energiebelasting 2026 (€0,0916 tot 10.000 kWh, €0,0667 daarboven) |
| ERE per geladen kWh (netto) | €0,07–0,10 | €0,10–0,13 | Uitbetalingen inboekdienstverleners juli 2026 ca. €0,12–0,13 (keuze.nl: Joulo, Laadloon, Zeres) |

| Gevolg | Was | Nu |
|---|---|---|
| Netto per jaar (pess. / normaal / opt.) | €3.809 / €6.762 / €9.732 | €3.751 / €6.663 / €9.743 |
| Terugverdientijd | 12,9 / 7,2 / 5,0 jaar | 13,1 / 7,4 / 5,0 jaar |
| Zon per jaar | €3.500–3.800 | €2.970–3.220 |
| Laadpalen per jaar (scenario's) | €1.474–3.182 | €1.966–3.838 |
| Airco stroom + gas (normaal) | €1.650 | €1.710 (goedkopere stroom maakt verwarmen met de airco gunstiger) |
| EMS + sensoren | €665–1.490 | €605–1.355 |

De lagere stroomprijs en de hogere ERE-opbrengst heffen elkaar grotendeels op.

**Correctie teruglevering:** het model rekende met een dynamisch contract voor de batterij, maar met een vaste terugleververgoeding van €0,08. Bij een dynamisch contract krijgt u voor teruglevering de uurprijs. De gemiddelde prijs tijdens zonne-opwek was €53 per MWh in 2025 en €65 in 2026 (EPEX NL via energy-charts, eigen berekening); na de opslag van de leverancier blijft €0,03–0,05 per kWh over. Gevolg: zon €2.850–3.150 per jaar, netto €3.631 / €6.563 / €9.673, terugverdientijd **13,5 / 7,5 / 5,1 jaar** (hoofdscenario).

**Stroomcontract nu → straks** (nieuwe sectie): de klant heeft nu dynamisch en houdt dat; daarop is het hoofdscenario gebaseerd. Ter vergelijking: vast → vast geeft 14,8 / 8,4 / 5,8 jaar. De batterij verdient zich met een vast contract niet terug (−€440 tot −€185 per jaar), maar blijft nodig voor 3x25 A. Vast → dynamisch levert voor de investering hetzelfde op als dynamisch → dynamisch; het overstapeffect telt niet mee.

**Prijsscenario 2027** (nieuwe sectie): door de oorlog met Iran (vanaf 28-2-2026, Straat van Hormuz dicht) steeg TTF van ca. €31 naar €74 per MWh; Cal-2027 gas ca. €55, stroom ca. €125 per MWh. Met stroom €0,23 en gas €1,40 excl. btw: netto €4.405 / €7.697 / €11.125, terugverdientijd **11,1 / 6,4 / 4,4 jaar**. De airco's winnen het meest; de laadpalen leveren iets minder op zolang het laadtarief niet meestijgt. Energiebelasting 2027: gas €0,6163 per m³, stroom €0,0880 per kWh. Het einde van de saldering zat al in het model.

**Optie 5 jaar** (nieuwe sectie, `model.vijf_jaar()`): met de airco's buiten de business case (energiedeel €25.500) normaal 4,2 jaar, met EIA/KIA (19% vpb, voordeel ca. €2.480) 3,8 jaar, met ook de prijzen van 2027 3,6 jaar. Minder stroomverbruik mag: bij 20.000 kWh 4,3 jaar, bij 15.000 kWh 4,6 jaar. Pessimistisch haalt 5 jaar niet (5,4–6,4). Het volledige pakket inclusief airco's haalt 5 jaar alleen optimistisch; met EIA/KIA en de prijzen van 2027 normaal 5,6 jaar.

**Airco-offerte** (7 Toshiba-sets RAV-HM401MUTP-E + RAV-GM402ATP-E): subtotalen ongewijzigd, €9.942,20 + €13.545,60 = €23.487,80. Herverdeeld: apparatuur €2.569,60 per set (boven €7.708,80, beneden €10.278,40), hoogwerker €650, overige posten naar rato (boven ×0,43, beneden ×0,53). Boven leidingwerk vervangen in plaats van spoelen, beneden infrarood afstandsbediening RBC-AXU31UM-E in plaats van wandbediening (past op de 4-wegcassette 600x600). Specificaties volgens Intercool: 3,6 kW koelen, 4,0 kW verwarmen, SCOP 4,46, R32 0,9 kg, 1-fase. Gevolgen: geen EIA op de airco's (4 kW per set, grens 12 kW); geen verplichte lekcontrole (0,6 ton CO₂-eq per set); EMS-gateway per set ca. €1.900 voor 7 sets; 7 sets voor 10 units; EMS-grenzen moeten ook gelden bij gebruik van de afstandsbediening.

## 2. Gecorrigeerd of aangevuld in de tekst

- **Inkoopprijzen:** via een relatie, geen marge voor Saldox. Margetabel en "verkoop aan derden" geschrapt.
- **Saldering:** stopt per 1-1-2027 (klopt). Toegevoegd: tot 2030 minimaal 50% van de kale leveringsprijs als terugleververgoeding; terugleverkosten blijven toegestaan (Rijksoverheid, ACM).
- **ERE:** vervangt de HBE; NEa-register open sinds augustus 2026, inboeken over 2026 vóór 26-2-2027. Eigen zonnestroom telt alleen als 100% hernieuwbaar bij directe koppeling, zonder SDE++ en met garanties van oorsprong. Voorbeeld met 5.000 kWh vervangen door 7.800–10.400 kWh, gelijk aan het laadplan.
- **Zaptec Pro:** MID-uitvoering bestaat sinds augustus 2023; die moet expliciet besteld worden. Begrenzen via Zaptec API of OCPP.
- **Sofar HYD 15KTL-3PH:** hybride, batterij max. 15 kW, alleen hoogspanningsbatterij (180–800 V), max. 22,5 kWp PV (DC/AC 1,2 is in orde). Nieuw open punt: met de Sofar BTS-batterij gaat één omvormer tot ca. 38 kWh bruikbaar, dus 50 kWh op één omvormer moet bevestigd worden.
- **EIA 2026:** 40%. Wel op de Energielijst: zonnepanelen (251102), batterij (251118), lucht-luchtwarmtepomp boven 12 kW thermisch met SCOP ≥ 4,0 (211108). Niet: laadpalen, algemeen EMS, tussenmeters. KIA 2026: 28% bij €2.901–71.683.
- **Btw:** belaste verhuur vereist ≥90% btw-belast gebruik door de huurder. Apart afgerekende stroom is een zelfstandige levering met 21% btw.
- **Netcongestie:** aansluitpauze van Enexis sinds 1-7-2026 rond Eindhoven-West en Helmond-Zuid, ook voor delen van Veldhoven; verzwaren is daar niet mogelijk. 3x35 A kost aan netbeheer ca. €1.240 per jaar meer dan 3x25 A. Dat versterkt de rol van de batterij.
- **Windturbine:** KNMI Eindhoven gemiddeld 3,8 m/s op 10 m, dus ca. 4,3–4,5 m/s op 20 m; onder de drempel. De "Windviewer van RVO" bestaat niet meer. Hoogtebeperkingen: Luchthavenbesluit Eindhoven, toets via de Luchtvaartbeperkingenkaart, verklaring van geen bezwaar van Defensie. Opbrengst €840–1.260 per jaar, terugverdientijd 20–30 jaar.
- **Airco:** SCOP in de praktijk 3,5–4,5; de berekening houdt voorzichtig 3,5 aan.
- **Gas:** €1,00 per m³ is voorzichtig (CBS + energiebelasting: ca. €1,10). 10 m³ per m² is aan de lage kant (CBS: 11–17 voor kleinere kantoren).
- **Zon:** PVGIS Veldhoven: 861 kWh/kWp oost-west, 1.032 kWh/kWp zuid; 917 kWh/kWp (16.500 kWh) is een redelijk gemiddelde. Winterdag 10 kWh geldt voor oost-west; zuid geeft 17–21 kWh. Dakruimte 120–150 m² geldt voor zuid; oost-west ca. 90–100 m².
- **UniFi:** U7 Pro €160, switch €359, gateway €180–250; switch heeft 2 SFP+-uplinks, dus 14 van 16 poorten in gebruik (de oude tekst telde 14 en 15). PPSK werkt alleen met WPA2. Netwerk totaal ca. €1.180–1.250.
- **ACM:** internet alleen voor eigen huurders is in de regel geen openbare dienst; registratie dan niet nodig.
- **PGS 37-1:2023:** geldt vanaf 20 kWh per ruimte; nog niet wettelijk verplicht.
- **F-gassen:** gecertificeerde monteur bij een gecertificeerd bedrijf (verordening (EU) 2024/573).
- **Weekenden** (`weekend.py`, simulatie per uur): weekendopwek ca. 3.900 kWh (24%), weekendverbruik ca. 700–2.000 kWh. Direct verbruik zonder batterij 75–83%, met batterij 90–95% bij een basislast van 0,5–1,5 kW. Het eerdere reviewpunt dat 85% optimistisch was, klopt niet: met batterij is 85% voorzichtig.
- **Rekenfouten in de tekst:** laadpalen "1,5 tot 4 jaar" was 1,4; 3-fase meters "€1.200–2.000 extra" was €800–1.400; model B miste de teruglevering (ca. €200).
- **Begrippenlijst:** BMS, EIA, F-gassen, KIA, Modbus, PGS 37-1 en SCOP toegevoegd; DC/AC-verhouding staat nu ook in de tekst.

## 3. Nog open (niet uit te zoeken zonder de opdrachtgever)

- Toshiba-interface: €1.500 past bij één centrale gateway; met een gateway per set (7 stuks) ca. €1.900.
- Bewegingssensoren: €600 past bij Aqara-klasse; met Philips Hue ca. €1.000.
- Jaarverbruik: 36.000 kWh is waarschijnlijk te hoog. CBS-kentallen (83374NED, kantoren 250–1.000 m²: 51–55 kWh/m²) geven voor 400 m² ca. 21.000 kWh; met kelder en nieuwe airco-verwarming ca. 25.000–30.000 kWh. De werkdagtabel gaat uit van gemiddeld 13–14 kW in kantoortijd, bijna het piekvermogen. Gevoeligheid (`weekend.py`): 30.000 kWh → ca. 7,5 jaar, 25.000 → ca. 7,7, 20.000 → ca. 8,0. Bevestigen met de meetdata van de slimme meter.
- Geen post onvoorzien op ca. €13.200 aan stelposten.
- Energiewet: doorlevering aan huurders in model B juridisch laten toetsen.
- Laadtarief: meestijgen met de stroomprijs (bijv. €0,41 / €0,51) als de prijzen van 2027 uitkomen.

## 4. Stijl

- Het rapport volgt de CSS-tokens van saldox.nl (`#0b3d2e`, `#1f6f4a`, `#2fa56b`); `#0f7a3e` komt alleen uit het manifest.
- "Jullie" is omgezet naar "u", zoals op saldox.nl (`TONE` in `build.py`).
