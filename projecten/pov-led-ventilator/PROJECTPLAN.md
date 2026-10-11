# Projectplan: POV LED-ventilator (plaatjes tonen met een draaiende ledstrip)

## 1. Idee in één zin

Een ledstrip draait razendsnel rond, zoals het blad van een ventilator. Door de
leds op precies het goede moment aan en uit te zetten, ziet je oog een
stilstaand plaatje of een animatie in de lucht zweven. Dit heet een
**POV-display** (*Persistence of Vision*: nawerking van het oog).

## 2. Hoe het werkt

```
            ↻ draairichting
        ●●●●●●●●●●●●●●●●  ← ledstrip (de "wiek")
              ┃
          [motor + as]
              ┃
   hallsensor ◉   ← magneet op het frame: 1 puls per omwenteling
```

1. Een **hallsensor** op de draaiende arm ziet één keer per omwenteling een
   vaste magneet langskomen. Zo weet de microcontroller waar "boven" is en
   hoe lang één omwenteling duurt.
2. De omwenteling wordt verdeeld in bijvoorbeeld **120 hoekstappen**
   (3° per stap).
3. Per hoekstap zet de microcontroller de leds op de kleuren van de
   bijbehorende "spaak" van het plaatje.
4. Het plaatje is dus niet in rijen en kolommen (x,y) opgeslagen, maar in
   **poolcoördinaten** (hoek, afstand tot het midden).

## 3. Doelen en eisen

| # | Eis | Doel |
|---|-----|------|
| E1 | Beelddiameter | ± 30–40 cm |
| E2 | Resolutie | 36 leds per armhelft × 120 hoekstappen |
| E3 | Beeldfrequentie | ≥ 25 beelden/s (geen flikkering) |
| E4 | Kleur | Volledige RGB |
| E5 | Beelden wisselen | Via wifi uploaden vanaf telefoon/pc |
| E6 | Animaties | Minimaal een eenvoudige animatie (bv. klok, draaiend logo) |
| E7 | Veiligheid | Draaiend deel volledig afgeschermd, uitbalanceerd |

## 4. De kernberekening (waarom de onderdeelkeuze belangrijk is)

- Toerental: **1200 rpm = 20 omwentelingen/s** → 50 ms per omwenteling.
- Met een **dubbele arm** (leds aan beide kanten van de as) wordt elk punt
  2× per omwenteling getekend → **40 beelden/s**. ✔ (E3)
- Tijd per hoekstap: 50 ms / 120 = **± 417 µs**.
- Tijd om 36 leds bij te werken:
  - **APA102 / SK9822** (SPI, 10–20 MHz): ± 0,1 ms ✔ ruim op tijd
  - **WS2812B / NeoPixel**: ± 1,1 ms ✘ te traag → uitgesmeerd beeld

**Conclusie:** gebruik **APA102- of SK9822-leds** (ze hebben een aparte klok-
en datalijn), géén WS2812B.

## 5. Onderdelenlijst (indicatie)

| Onderdeel | Keuze | Prijs (±) |
|-----------|-------|-----------|
| Microcontroller | ESP32 (wifi + snelle SPI, 2 cores) | € 8 |
| Leds | APA102/SK9822-strip, 144 leds/m, ± 0,5 m | € 15 |
| Positiesensor | Hallsensor A3144 (of US5881) + kleine neodymiummagneet | € 3 |
| Motor | 12 V DC-motor of BLDC + ESC, 1000–1500 rpm, of een omgebouwde tafelventilator (wieken verwijderd) | € 15–30 |
| Stroomoverdracht naar het draaiende deel | Optie A: sleepring (slip ring) met 2+ contacten · Optie B: draadloze inductieve module (5 V, 2 A) | € 10–20 |
| Spanningsregelaar | 5 V step-down (buck), min. 3 A | € 5 |
| Condensator | 1000 µF over de 5 V van de leds | € 1 |
| Arm/rotor | Stuk printplaat, aluminium strip of 3D-geprint | € 5 |
| Behuizing/afscherming | Ronde kap van plexiglas/polycarbonaat, of de kooi van de ventilator | € 10–20 |
| Overig | Draad, schroeven, contragewichten, 12 V-adapter | € 15 |
| **Totaal** | | **± € 90–130** |

### Keuze: stroomoverdracht

| | Sleepring | Draadloos (inductief) |
|---|---|---|
| Eenvoud | ✔ simpel | ± spoelen uitlijnen |
| Slijtage / ruis | ✘ borstels slijten, kan storen | ✔ geen contact |
| Vermogen | ✔ ruim | ± beperkt (houd helderheid laag) |
| **Advies** | Prototype | Eindversie |

*Alternatief:* een kleine Li-ion-accu op de arm. Simpel, maar maakt de arm
zwaarder en moet regelmatig geladen worden.

## 6. Elektrisch schema (vereenvoudigd)

```
 [12 V adapter] ── motor (stilstaand deel)
       │
  sleepring / draadloze spoel
       │                     (draaiend deel)
   [buck 5 V] ──┬── ESP32 (5V/VIN)
                ├── ledstrip 5V  (+1000 µF)
                │
 ESP32 GPIO18 (SCK)  ── led CLK
 ESP32 GPIO23 (MOSI) ── led DATA
 ESP32 GPIO4         ── hallsensor OUT (pull-up 10 kΩ)
 GND gemeenschappelijk voor alles
```

## 7. Software-architectuur

**Op de ESP32 (Arduino/PlatformIO, C++):**

1. **Interrupt op de hallsensor** → meet tijd per omwenteling (`micros()`).
2. **Hardwaretimer** → vuurt elke `omwentelingstijd / 120` af en schuift de
   volgende kolom naar de leds (core 1, zo min mogelijk vertraging).
3. **Beeldbuffer** in RAM: `120 hoeken × 72 leds × 3 bytes ≈ 26 kB` per
   beeld; meerdere beelden voor animatie.
4. **Wifi-webserver** (core 0): webpagina om een plaatje te uploaden,
   helderheid in te stellen en een animatie/klok te kiezen.
5. Opslag van beelden in **LittleFS** (flash) zodat ze na herstart blijven.
6. Bibliotheek: `FastLED` of direct SPI-DMA voor maximale snelheid.

**Op de pc (Python-script `convert.py`):**

- Laadt een gewoon plaatje (PNG/JPG), knipt het rond bij, en zet het om naar
  poolcoördinaten (voor elke hoek en elke led: welke pixel hoort daarbij?).
- Corrigeert voor de grootte: buitenste leds beslaan een groter oppervlak dan
  binnenste → helderheid binnenin wat terugschalen.
- Exporteert een binair bestand dat de ESP32 direct in zijn buffer kan laden.
- (Later kan deze omzetting ook in de browser/op de ESP32 zelf gebeuren.)

## 8. Fasering en planning

| Fase | Wat | Resultaat ("klaar als…") | Duur |
|------|-----|--------------------------|------|
| 0 | Onderzoek & bestellen | Onderdelen besteld, schema op papier | 1 week (+ levertijd) |
| 1 | Stilstaande test | ESP32 stuurt APA102-strip aan; testpatronen werken | 1 weekend |
| 2 | Sensor & timing | Hallsensor meet toerental (met de hand draaien); waarde op seriële monitor | 1 avond |
| 3 | Mechanica | Arm op motor, **gebalanceerd**, stroomoverdracht werkt, afscherming erop | 1–2 weekenden |
| 4 | Eerste beeld | Statisch patroon (bv. een ster of tekst) staat stil in de lucht | 1 weekend |
| 5 | Plaatjes | `convert.py` werkt; eigen foto/logo zichtbaar | 1 weekend |
| 6 | Wifi & upload | Plaatje uploaden via telefoon, helderheid instelbaar | 1–2 weekenden |
| 7 | Extra's | Klok, animaties, tekst die rondloopt, afwerking | doorlopend |

**Totaal:** ± 6–8 weken in de vrije tijd.

## 9. Risico's en maatregelen

| Risico | Gevolg | Maatregel |
|--------|--------|-----------|
| Onbalans | Trillen, lawaai, onderdelen vliegen los | Arm symmetrisch bouwen, contragewicht tegenover ESP32/buck, eerst op laag toerental testen |
| Losschietende onderdelen | **Letsel** | Alles vastlijmen/schroeven, kabelbinders, altijd achter een kap, veiligheidsbril bij testen |
| Beeld "drijft" of trilt | Onrustig beeld | Toerental elke omwenteling opnieuw meten; timer bijstellen; stabiele motorvoeding |
| Leds te traag | Uitgesmeerd beeld | APA102/SK9822 gebruiken (zie §4) |
| Te veel stroom | Buck/sleepring wordt heet, ESP32 reset | Helderheid begrenzen (bv. max 30 %), dikke 5 V-draden, condensator |
| Sleepring stoort | Haperende leds, resets | Condensatoren, eventueel overstappen op draadloze stroom |
| Wifi traag tijdens draaien | Uploaden hapert | Wifi op core 0, ledtiming op core 1 |

## 10. Veiligheid (niet overslaan!)

- Draai **nooit** zonder afscherming; de rand van de arm gaat ± 75 km/u.
- Begin elke test op laag toerental en verhoog langzaam.
- Werk met lage spanning (12 V / 5 V). Gebruik een gecertificeerde adapter,
  geen zelfgebouwde netspanningsvoeding.
- Bouw een makkelijk bereikbare aan/uit-schakelaar voor de motor.

## 11. Uitbreidingsideeën

- Analoge/digitale **klok** met datum via internettijd (NTP).
- **Tekst** die rondloopt (bijv. meldingen of de zonnepaneelopbrengst uit
  Home Assistant via MQTT).
- Animaties (GIF → reeks poolbeelden).
- Meer arms (3 of 4) voor hogere resolutie of minder toerental.
- Afstandsbediening via een webapp of Home Assistant-integratie.

## 12. Eerste concrete stappen

1. [ ] Kies motor: tafelventilator ombouwen of losse DC/BLDC-motor.
2. [ ] Kies stroomoverdracht: sleepring (prototype) of draadloos.
3. [ ] Bestel ESP32, APA102/SK9822-strip, hallsensor + magneet, buck-converter.
4. [ ] Fase 1 starten: testpatroon op een stilstaande strip.
