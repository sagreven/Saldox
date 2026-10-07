"""Tests voor de afgeleide net-vermogen-berekening (plan_poller.derive_grid_power_w).

WAAROM. De Sofar HYD PCC-register (ac_active_power_w, 0x0488) blaast tijdens Passive-mode
geforceerd laden op met ~het laadvermogen. Op 2026-10-06 las het register ~13,3 kW terwijl de
energiebalans (load/pv/battery) sloot op een echte netimport van ~5 kW. We leiden grid daarom af
uit de balans i.p.v. 0x0488 te vertrouwen:  grid = load − pv − battery  (battery − = laden).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from saldox_addon.plan_poller import derive_grid_power_w


def test_force_charge_casus_2026_10_06():
    # De exacte casus: load 120 W, pv 2600 W, accu laadt 7490 W (battery_power −7490).
    # Register 0x0488 las hier 13280 W; de balans geeft de echte import.
    assert derive_grid_power_w(120.0, 2600.0, -7490.0) == 5010.0


def test_ontladen_naar_net_is_export_negatief():
    # Avond: geen pv, accu ontlaadt 4000 W (positief), huis vraagt 1000 W.
    # grid = 1000 − 0 − 4000 = −3000 → export.
    assert derive_grid_power_w(1000.0, 0.0, 4000.0) == -3000.0


def test_pv_overschot_zonder_accu_is_export():
    # Middag: pv 4000 W, load 1000 W, accu idle. grid = 1000 − 4000 − 0 = −3000 (export).
    assert derive_grid_power_w(1000.0, 4000.0, 0.0) == -3000.0


def test_zelfvoorzienend_is_nul():
    # pv dekt precies de last, accu idle. grid = 0.
    assert derive_grid_power_w(1500.0, 1500.0, 0.0) == 0.0


def test_import_bij_tekort_zonder_pv():
    # Nacht: geen pv, geen accu-actie, huis vraagt 700 W → 700 W import.
    assert derive_grid_power_w(700.0, 0.0, 0.0) == 700.0


def test_ontbrekende_component_geeft_none():
    # Valt een van de drie weg, dan None zodat de aanroeper op de ruwe register terugvalt.
    assert derive_grid_power_w(None, 2600.0, -7490.0) is None
    assert derive_grid_power_w(120.0, None, -7490.0) is None
    assert derive_grid_power_w(120.0, 2600.0, None) is None
