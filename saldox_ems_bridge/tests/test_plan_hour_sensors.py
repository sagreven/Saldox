"""Test: PlanPoller publiceert de plan-waarden van het LOPENDE uur als HA-sensors.

Doel: plan-vs-gemeten kunnen terugkijken. De add-on schrijft per uur de geplande
consumption/pv/soc/grid/price/action naar HA (recorder bewaart de historie):
  - LIVE sensors (sensor.{slug}_<metric>): elke tick overschreven (last-write-wins).
  - COMMITTED sensors (sensor.{slug}_<metric>_committed): één keer per uur (op :00) als
    vaste referentie — binnen dat uur NIET meer herzien, ook al herberekent de planner.
Elke sensor draagt for_hour_utc + plan_recomputed_at.

DRAAIEN (geen systeem-Python; uv haalt er een):
    PYTHONPATH=. uv run --no-project --python 3.12 \\
        --with pytest --with-requirements requirements.txt \\
        -- python -m pytest tests/test_plan_hour_sensors.py -v
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest


class _FakeHa:
    """HA-client die post_state-aanroepen vastlegt."""

    def __init__(self):
        self.calls: list[dict] = []

    async def post_state(self, entity_id, state, unit=None, friendly_name=None,
                         device_class=None, state_class=None, extra_attrs=None):
        self.calls.append({
            "entity_id": entity_id, "state": state, "unit": unit,
            "device_class": device_class, "state_class": state_class,
            "attrs": extra_attrs or {},
        })
        return True


def _poller(ha):
    pp = pytest.importorskip("saldox_addon.plan_poller", reason="aiohttp (addon-container / uv)")
    return pp.PlanPoller(ha, "http://saldox.local", "tok", slug="saldox_plan")


# Timeline-slot voor 13:00 UTC + een laad-actie die dat uur dekt.
_NOW = datetime(2026, 11, 10, 13, 20, 0, tzinfo=timezone.utc)
_TIMELINE = [
    {"startUtc": "2026-11-10T12:00:00Z", "consumptionWatts": 800, "pvWatts": 1000, "socPercent": 18, "gridWatts": -200, "priceEurKwh": 0.44},
    {"startUtc": "2026-11-10T13:00:00Z", "consumptionWatts": 900, "pvWatts": 3000, "socPercent": 22, "gridWatts": -900, "priceEurKwh": 0.44},
    {"startUtc": "2026-11-10T14:00:00Z", "consumptionWatts": 900, "pvWatts": 2600, "socPercent": 25, "gridWatts": -500, "priceEurKwh": 0.46},
]
_ACTIONS = [{"kind": "ChargeBattery", "startUtc": "2026-11-10T13:00:00Z", "endUtc": "2026-11-10T15:00:00Z"}]


def _by_entity(calls):
    return {c["entity_id"]: c for c in calls}


def test_live_sensors_van_huidige_uur():
    ha = _FakeHa()
    asyncio.run(_poller(ha)._publish_hour_sensors(_TIMELINE, _ACTIONS, _NOW, "2026-11-10T13:20:00+00:00"))
    e = _by_entity(ha.calls)
    # waarden uit de 13:00-slot (niet 12:00/14:00)
    assert e["sensor.saldox_plan_consumption"]["state"] == 900
    assert e["sensor.saldox_plan_pv"]["state"] == 3000
    assert e["sensor.saldox_plan_soc"]["state"] == 22
    assert e["sensor.saldox_plan_grid"]["state"] == -900
    assert e["sensor.saldox_plan_price"]["state"] == 0.44
    assert e["sensor.saldox_plan_action"]["state"] == "Batterij laden"
    # attributes aanwezig
    attrs = e["sensor.saldox_plan_consumption"]["attrs"]
    assert attrs["for_hour_utc"] == "2026-11-10T13:00:00+00:00"
    assert attrs["plan_recomputed_at"] == "2026-11-10T13:20:00+00:00"


def test_committed_eerste_tick_wel_tweede_tick_niet():
    ha = _FakeHa()
    p = _poller(ha)
    # eerste tick in dit uur → committed geschreven
    asyncio.run(p._publish_hour_sensors(_TIMELINE, _ACTIONS, _NOW, "t1"))
    committed = [c for c in ha.calls if c["entity_id"].endswith("_committed")]
    assert len(committed) == 6  # consumption/pv/soc/grid/price/action

    # tweede tick, zelfde uur, plan herzien (andere SoC) → LIVE update, GEEN nieuwe committed
    ha.calls.clear()
    tl2 = [dict(s) for s in _TIMELINE]
    tl2[1]["socPercent"] = 30  # herziening binnen het uur
    asyncio.run(p._publish_hour_sensors(tl2, _ACTIONS, _NOW.replace(minute=50), "t2"))
    assert any(c["entity_id"] == "sensor.saldox_plan_soc" and c["state"] == 30 for c in ha.calls)  # live herzien
    assert not any(c["entity_id"].endswith("_committed") for c in ha.calls)  # committed NIET herzien


def test_committed_opnieuw_in_nieuw_uur():
    ha = _FakeHa()
    p = _poller(ha)
    asyncio.run(p._publish_hour_sensors(_TIMELINE, _ACTIONS, _NOW, "t1"))
    ha.calls.clear()
    # nieuw uur (14:00) → nieuwe committed-snapshot
    now2 = datetime(2026, 11, 10, 14, 5, 0, tzinfo=timezone.utc)
    asyncio.run(p._publish_hour_sensors(_TIMELINE, _ACTIONS, now2, "t3"))
    committed = [c for c in ha.calls if c["entity_id"].endswith("_committed")]
    assert len(committed) == 6
    assert _by_entity(ha.calls)["sensor.saldox_plan_soc_committed"]["state"] == 25  # 14:00-slot


def test_idle_als_geen_actie_loopt():
    ha = _FakeHa()
    # actie eindigt vóór nu → idle
    acts = [{"kind": "ChargeBattery", "startUtc": "2026-11-10T01:00:00Z", "endUtc": "2026-11-10T02:00:00Z"}]
    asyncio.run(_poller(ha)._publish_hour_sensors(_TIMELINE, acts, _NOW, "t"))
    assert _by_entity(ha.calls)["sensor.saldox_plan_action"]["state"] == "idle"


def test_geen_slot_voor_dit_uur_publiceert_niets():
    ha = _FakeHa()
    # now op 20:00 UTC — geen slot in de timeline
    now = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)
    asyncio.run(_poller(ha)._publish_hour_sensors(_TIMELINE, _ACTIONS, now, "t"))
    assert ha.calls == []
