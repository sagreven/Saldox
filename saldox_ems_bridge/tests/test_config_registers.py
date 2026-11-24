"""Tests voor build_config_registers — de trage configpush naar /api/ha/device-config.

Achtergrond (hh.imming, 24-11-2026): de accu hangt structureel op 9-10% SoC. Dat is niet de
planner maar de omvormer zelf: DOD/EOD = 90 betekent ontladen tot 10%. Die instellingen staan
in het configblok (0x104D/0x104E/0x1052) en waren in Saldox niet bekend, waardoor de planner
met een eigen, hogere SoC-vloer rekende.
"""
from saldox_addon.plan_poller import build_config_registers, next_config_push_at
from saldox_addon.plan_poller import PlanPoller
from saldox_addon.registers import CONFIG_REGISTER_NAMES


def test_mislukte_push_krijgt_korte_retry_geen_hele_dag():
    # De regressie: op 24-11-2026 startte de add-on vóór de server-deploy, de eerste
    # configpush kreeg 404, en omdat de tijdstempel ook bij mislukking werd opgeschoven
    # bleef DeviceConfigSnapshots 24 uur leeg.
    deadline = next_config_push_at(1000.0, ok=False, push_seconds=86400, retry_seconds=900)
    assert deadline == 1900.0


def test_geslaagde_push_gebruikt_de_volle_cadans():
    deadline = next_config_push_at(1000.0, ok=True, push_seconds=86400, retry_seconds=900)
    assert deadline == 87400.0


def test_retry_is_substantieel_korter_dan_de_cadans():
    # Guard tegen een toekomstige tweak die retry en cadans gelijktrekt.
    assert PlanPoller._CONFIG_RETRY_SECONDS < PlanPoller._CONFIG_PUSH_SECONDS / 10


def _r(**kv):
    return {k: {"value": v, "unit": "%"} for k, v in kv.items()}


def test_config_registers_worden_gepusht():
    entries = build_config_registers(_r(
        battery_dod_percent=90, battery_eod_percent=90, battery_eps_buffer_percent=5))

    by_key = {e["key"]: e["value"] for e in entries}
    assert by_key["battery_dod_percent"] == 90
    assert by_key["battery_eod_percent"] == 90
    assert by_key["battery_eps_buffer_percent"] == 5


def test_alleen_configregisters_niet_de_telemetrie():
    # Telemetrie hoort via /api/ha/telemetry te gaan, niet via de configpush.
    entries = build_config_registers(_r(
        battery_dod_percent=90, load_power_w=2400, battery_power_w=-5000))

    keys = {e["key"] for e in entries}
    assert keys == {"battery_dod_percent"}


def test_ontbrekend_register_wordt_overgeslagen_niet_nul():
    # Een register dat de firmware niet beantwoordt mag geen 0 worden: een DOD van 0%
    # betekent iets heel anders dan "onbekend".
    readings = {"battery_dod_percent": {"value": None}, "battery_eod_percent": {"value": 90}}
    entries = build_config_registers(readings)

    keys = {e["key"] for e in entries}
    assert keys == {"battery_eod_percent"}


def test_per_pack_gezondheid_gaat_mee():
    # SoH/cycles per pack zijn traag-veranderend en horen in de configsnapshot, zodat
    # per-pack-veroudering achteraf te zien is.
    entries = build_config_registers(_r(
        battery_soh_percent=100, battery_cycles=57,
        battery2_soh_percent=100, battery2_cycles=59))

    by_key = {e["key"]: e["value"] for e in entries}
    assert by_key["battery_cycles"] == 57
    assert by_key["battery2_cycles"] == 59


def test_lege_readings_geeft_lege_lijst():
    assert build_config_registers({}) == []


def test_alle_geconfigureerde_namen_bestaan_als_register():
    # Guard tegen een typefout in CONFIG_REGISTER_NAMES: elke naam moet een echt register zijn.
    from saldox_addon.registers import by_name

    for name in CONFIG_REGISTER_NAMES:
        by_name(name)  # raises KeyError bij een onbekende naam
