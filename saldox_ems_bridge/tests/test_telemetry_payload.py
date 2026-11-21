"""Tests voor build_telemetry_payload — met nadruk op de per-pack (bat1/bat2) mapping.

Casus gebaseerd op de live /status-sample van 21-11-2026 (hh.imming, 2-BDU):
  battery_power_w=340, battery_soc_percent=19  → BAT1
  battery2_power_w=430, battery2_soc_percent=22 → BAT2
  load=800, pv=0 → grid ≈ load − pv − bat1 = 460 (bekende beperking: mist bat2).
"""
from saldox_addon.plan_poller import build_telemetry_payload


def _r(**kv):
    return {k: {"value": v} for k, v in kv.items()}


def test_per_pack_velden_worden_gepusht():
    readings = _r(
        battery_power_w=340, battery_soc_percent=19,
        battery2_power_w=430, battery2_soc_percent=22,
        load_power_w=800, pv_total_power_w=0,
    )
    p = build_telemetry_payload(readings)
    # bat1 = basisblok (zelfde bron als het aggregaat-veld)
    assert p["bat1PowerW"] == 340
    assert p["bat1SoCPercent"] == 19
    assert p["batteryPowerW"] == 340  # aggregaat-veld ongemoeid
    # bat2 = +7-offsetblok
    assert p["bat2PowerW"] == 430
    assert p["bat2SoCPercent"] == 22


def test_geen_bat2_geen_bat2_velden():
    readings = _r(battery_power_w=340, battery_soc_percent=19, load_power_w=800, pv_total_power_w=0)
    p = build_telemetry_payload(readings)
    assert "bat2PowerW" not in p and "bat2SoCPercent" not in p
    assert p["bat1PowerW"] == 340 and p["bat1SoCPercent"] == 19


def test_grid_afgeleid_uit_balans():
    readings = _r(battery_power_w=340, load_power_w=800, pv_total_power_w=0)
    p = build_telemetry_payload(readings)
    assert p["gridPowerW"] == 460  # 800 − 0 − 340 (bekende beperking: alleen bat1)


def test_ontbrekende_waarden_worden_overgeslagen():
    readings = {"battery_power_w": {"value": None}, "battery2_soc_percent": {"value": 22}}
    p = build_telemetry_payload(readings)
    assert "bat1PowerW" not in p and "batteryPowerW" not in p
    assert p["bat2SoCPercent"] == 22
