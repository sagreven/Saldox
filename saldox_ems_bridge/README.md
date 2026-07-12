# Saldox EMS Bridge — Home Assistant add-on

Bridge tussen [Saldox](https://saldox.nl) en je hardware. Pollt een **Sofar Solar
HYD** hybride inverter via Modbus-TCP, publiceert de waardes als Home Assistant
sensors, en accepteert commando's vanuit Saldox (PV-curtailment, batterij-mode,
laad/ontlaadvermogen).

## Wat de add-on doet

1. **Poll** — elke `poll_interval_seconds` (default 10s) leest de add-on de
   belangrijkste Modbus-registers van de inverter (PV-power, AC-power, batterij
   SOC + power, energy counters, status).
2. **Push naar HA** — elke uitlezing wordt via de Supervisor API geschreven naar
   `sensor.{slug}_power`, `sensor.{slug}_today_kwh`, `sensor.{slug}_total_kwh`,
   etc. Saldox's `SofarDeviceDriver` (mode `modbus-ha`) leest deze sensors via
   de standaard HA REST states-API.
3. **Webhook server** — luistert op port 8765 voor Saldox-commands en schrijft
   ze als Modbus holding-registers terug naar de inverter:
   - `POST /commands/active-power-limit { "percent": 0..100 }` — PV-curtailment
     (bv. bij negatieve EPEX-prijzen).
   - `POST /commands/battery-mode { "mode": "auto|force-charge|force-discharge|standby" }`
   - `POST /commands/battery-charge-power { "watts": 3000 }` — doel-laadvermogen
     wanneer mode = force-charge.
   - `POST /commands/battery-discharge-power { "watts": 3000 }`
   - `GET /healthz` — voor monitoring.

## Installeren in Home Assistant

1. Voeg `https://swdevtfs.fan2customer.com/Ublion/AI%20EnergyAdvisor/_git/saldox-ha-addons` toe als
   **Add-on Repository** in Supervisor → Add-ons → ⋮ → Repositories.
2. Installeer "Saldox EMS Bridge" uit de lijst.
3. Configureer onder de Options-tab:
   ```yaml
   modbus:
     host: 192.168.1.50              # IP van je Sofar inverter
     port: 502
     unit_id: 1
     poll_interval_seconds: 10
   ha:
     device_slug: sofar_hyd
     friendly_name: Sofar HYD
   ```
4. Start de add-on. In de Logs zie je `Poll OK — N readings naar HA`.
5. Open HA → Developer Tools → States → filter `sensor.sofar_hyd`. Je hoort
   `*_power`, `*_today_kwh`, `*_total_kwh`, `*_battery_soc`, etc. te zien.

## EPEX day-ahead prijzen als HA-sensors

Naast de Modbus-data publisht de add-on (default aan, configureerbaar onder
`prices.enabled`) de NL-energieprijzen als HA sensors. Bron: EnergyZero
(`api.energyzero.nl`), dezelfde feed die Saldox zelf gebruikt. Pakt vandaag's
prijzen direct na middernacht en morgen's prijzen vanaf ~13:00 CET wanneer
EPEX gepubliceerd heeft.

Default-slug `saldox_price`, verstelbaar in config. Entities:

| Entity                                       | Wat                                       |
|----------------------------------------------|-------------------------------------------|
| `sensor.saldox_price_now`                    | actuele €/kWh (huidige uur)               |
| `sensor.saldox_price_today_avg`              | gemiddelde van vandaag                    |
| `sensor.saldox_price_today_min`              | laagste uur van vandaag                   |
| `sensor.saldox_price_today_max`              | hoogste uur van vandaag                   |
| `sensor.saldox_price_tomorrow_avg/min/max`   | idem voor morgen (na ~13:00 CET)          |
| `sensor.saldox_price_rank_now`               | 1..24 — 1 = goedkoopste uur van vandaag   |
| `sensor.saldox_price_negative_hours_today`   | aantal uren met prijs < 0                 |

Elke sensor heeft een attribute `prices` met 24 floats (= het volledige
prijsprofiel) zodat je met [apexcharts-card](https://github.com/RomRider/apexcharts-card)
of ApexCharts een prijscurve in je dashboard kunt plotten:

```yaml
type: custom:apexcharts-card
series:
  - entity: sensor.saldox_price_today_avg
    data_generator: |
      return entity.attributes.prices.map((p, i) => [
        new Date().setHours(i, 0, 0, 0), p
      ]);
```

### Automation-voorbeelden

**Vaatwasser starten in de 4 goedkoopste uren:**
```yaml
automation:
  - alias: "Vaatwasser bij goedkope stroom"
    trigger:
      - platform: state
        entity_id: sensor.saldox_price_rank_now
    condition:
      - condition: numeric_state
        entity_id: sensor.saldox_price_rank_now
        below: 5
      - condition: state
        entity_id: input_boolean.vaatwasser_klaar_te_starten
        state: "on"
    action:
      - service: switch.turn_on
        target: { entity_id: switch.vaatwasser }
```

**Notificatie bij negatieve uren morgen:**
```yaml
automation:
  - alias: "Negatieve prijzen morgen"
    trigger:
      - platform: numeric_state
        entity_id: sensor.saldox_price_tomorrow_min
        below: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Negatieve stroomprijs morgen"
          message: "Morgen is de laagste prijs {{ states('sensor.saldox_price_tomorrow_min') }} €/kWh — plan zware verbruikers in."
```

## Saldox-zijde

Op `/connect/sofar` in Saldox kies je **"Lokaal via Home Assistant"** en vul je:

- **HA URL**: bv. `http://homeassistant.local:8123`
- **Long-lived access token**: maak in HA → Profiel → Long-Lived Access Tokens
- **Device slug**: `sofar_hyd` (dezelfde als hier in de add-on options)

Saldox pollt dan periodiek de HA states-API en gebruikt de data voor jaaropwek,
EMS-planning en de 48-uurs plan. Commands gaan terug via een aparte HTTP-bridge
(Saldox roept de webhook van deze add-on aan).

## Modbus register-map (Sofar HYD 5-20KTL-3PH)

Subset, zie `saldox_addon/registers.py` voor de volledige definities. Schaling +
signed-conversie gebeuren in de Modbus-client.

| Naam                       | Adres   | Type    | Schaal       | Eenheid |
|----------------------------|---------|---------|--------------|---------|
| pv_total_power_w           | 0x05C4  | input   | × 100        | W       |
| ac_active_power_w          | 0x0485  | input   | × 100 signed | W       |
| battery_soc_percent        | 0x0608  | input   | × 1          | %       |
| battery_power_w            | 0x0606  | input   | × 100 signed | W       |
| today_production_kwh       | 0x0686  | input   | × 0.1        | kWh     |
| total_production_kwh       | 0x0684  | input   | × 0.1 (32b)  | kWh     |
| active_power_limit_pct     | 0x1004  | holding | × 1 (RW)     | %       |
| battery_mode               | 0x1110  | holding | × 1 (RW)     | enum    |

⚠ Het register-bestand is afgestemd op de **Sofar HYD 3PH protocol V1.x**. Verifieer
met de Sofar Modbus-PDF wanneer je naar nieuwere firmware updatet.

## Status

**v0.1.0** — eerste werkende versie. Mogelijke uitbreidingen:
- MQTT auto-discovery als alternatief voor Supervisor state-push
- Zaptec-bridge via dezelfde add-on (zelfde architectuur, andere driver)
- Bidirectional event-stream: Saldox → HA "EMS event" (curtailment actief, etc.)
- Web-UI tab voor add-on (Modbus-register browser + write-knoppen)

## Bouwen / testen

```bash
# Lokaal builden voor amd64
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base-alpine:3.18 -t saldox-ems-bridge .

# Smoke-test (zonder HA — webhook werkt, Modbus geeft connect-error
# wanneer je geen Sofar op je netwerk hebt)
docker run --rm -it \
  -e MODBUS_HOST=192.168.1.50 \
  -e HA_DEVICE_SLUG=sofar_hyd \
  -p 8765:8765 \
  saldox-ems-bridge
```
