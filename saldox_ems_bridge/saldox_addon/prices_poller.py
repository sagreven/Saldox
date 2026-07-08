"""EPEX day-ahead prijzen voor Home Assistant.

Haalt NL-prijzen via EnergyZero (dezelfde bron die Saldox zelf gebruikt) en
publiceert ze als HA sensors. EnergyZero levert all-in tarieven (incl. BTW +
energiebelasting) wanneer `inclBtw=true` & `usageType=1`. Voor pure groothandel
zet je `inclBtw=false`.

EnergyZero levert vandaag's prijzen vanaf 00:00 lokaal, en morgen's prijzen
typisch tussen 13:00-14:00 CET (na de EPEX day-ahead-publicatie). De poller is
defensief: missen morgen-prijzen, dan blijven die sensors stale.

Gepubliceerde entities (slug standaard `saldox_price`):
  sensor.{slug}_now                — actuele €/kWh (huidige uur)
  sensor.{slug}_today_avg          — gemiddelde van vandaag
  sensor.{slug}_today_min          — laagste van vandaag
  sensor.{slug}_today_max          — hoogste van vandaag
  sensor.{slug}_tomorrow_avg       — idem voor morgen (na 13:00)
  sensor.{slug}_tomorrow_min       — idem
  sensor.{slug}_tomorrow_max       — idem
  sensor.{slug}_rank_now           — 1..24 (1 = goedkoopste uur van vandaag)
  sensor.{slug}_negative_hours_today — aantal uren met prijs < 0

Elke sensor heeft als attribute `prices_today: [...]` (24 floats) en
`prices_tomorrow: [...]` (0 of 24 floats) zodat HA-cards (zoals apexcharts-card)
het volledige profiel kunnen plotten.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import aiohttp

from .ha_api import HomeAssistantClient

_LOG = logging.getLogger(__name__)

# Lokale tijdzone voor "vandaag" / "morgen" — Saldox-context is altijd NL.
NL_TZ_OFFSET = timedelta(hours=1)  # CET. DST-correctie: gebruiken UTC offset = 2u tussen mar-okt.
# Bij gebrek aan tzdata in de add-on container vertrouwen we op een grove
# CET/CEST-heuristiek: tussen laatste-zondag-maart en laatste-zondag-oktober is
# het UTC+2. Voor dagprijzen-doeleinden is dat goed genoeg.


def _nl_offset_for(now_utc: datetime) -> timedelta:
    """Best-effort CET/CEST detectie zonder zoneinfo dependency."""
    y = now_utc.year

    def _last_sunday(year: int, month: int) -> datetime:
        d = datetime(year, month, 31, tzinfo=timezone.utc)
        while d.weekday() != 6:
            d -= timedelta(days=1)
        return d

    dst_start = _last_sunday(y, 3).replace(hour=1)
    dst_end = _last_sunday(y, 10).replace(hour=1)
    return timedelta(hours=2) if dst_start <= now_utc < dst_end else timedelta(hours=1)


class PricesPoller:
    """Pollt EnergyZero (vandaag + morgen) en pusht aggregates naar HA."""

    BASE = "https://api.energyzero.nl/v1/energyprices"

    def __init__(
        self,
        ha: HomeAssistantClient,
        slug: str = "saldox_price",
        friendly: str = "Saldox prijs",
        vat_inclusive: bool = True,
        poll_minutes: int = 15,
        on_update: "Callable[[dict[str, dict]], None] | None" = None,
    ):
        self._ha = ha
        self._slug = slug
        self._friendly = friendly
        self._vat = vat_inclusive
        self._poll_seconds = max(60, poll_minutes * 60)
        self._session: aiohttp.ClientSession | None = None
        self._on_update = on_update

    async def _session_get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch_day(self, day_local_midnight_utc: datetime) -> list[float]:
        """Haalt 24 uur prijzen op vanaf `day_local_midnight_utc`. Lege lijst
        wanneer EnergyZero nog geen data heeft (typisch morgen vóór 13:00)."""
        session = await self._session_get()
        from_iso = day_local_midnight_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        till = (day_local_midnight_utc + timedelta(days=1, seconds=-1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        params = {
            "fromDate": from_iso,
            "tillDate": till,
            "interval": 4,                # 1 = 15-min, 4 = uurlijks
            "usageType": 1,               # 1 = elektriciteit, 3 = gas
            "inclBtw": "true" if self._vat else "false",
        }
        try:
            async with session.get(self.BASE, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    _LOG.warning("EnergyZero %s → HTTP %s", from_iso, resp.status)
                    return []
                data = await resp.json()
        except aiohttp.ClientError as ex:
            _LOG.warning("EnergyZero fetch faalde: %s", ex)
            return []

        # Response shape: { "Prices": [ { "price": 0.234, "readingDate": "..." }, ... ] }
        prices = data.get("Prices") or []
        out = [float(p.get("price", 0.0)) for p in prices]
        if len(out) not in (0, 23, 24, 25):
            _LOG.info("EnergyZero gaf %d punten voor %s (verwacht 24)", len(out), from_iso)
        return out

    @staticmethod
    def _stats(prices: list[float]) -> dict[str, Any]:
        if not prices:
            return {"avg": None, "min": None, "max": None, "negative": 0}
        return {
            "avg": round(sum(prices) / len(prices), 4),
            "min": round(min(prices), 4),
            "max": round(max(prices), 4),
            "negative": sum(1 for p in prices if p < 0),
        }

    async def tick(self) -> None:
        now_utc = datetime.now(timezone.utc)
        offset = _nl_offset_for(now_utc)
        # Lokale middernacht vandaag, in UTC uitgedrukt.
        local_now = now_utc + offset
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_utc = local_midnight - offset
        tomorrow_start_utc = today_start_utc + timedelta(days=1)

        today = await self._fetch_day(today_start_utc.replace(tzinfo=None).replace(tzinfo=timezone.utc))
        tomorrow = await self._fetch_day(tomorrow_start_utc.replace(tzinfo=None).replace(tzinfo=timezone.utc))

        # Huidig uur (lokaal)
        hour_idx = local_now.hour
        price_now: float | None = None
        rank_now: int | None = None
        if 0 <= hour_idx < len(today):
            price_now = round(today[hour_idx], 4)
            ranks = sorted(range(len(today)), key=lambda i: today[i])  # cheapest first
            rank_now = ranks.index(hour_idx) + 1

        s_today = self._stats(today)
        s_tomorrow = self._stats(tomorrow)

        attrs_today = {"prices": today, "vat_inclusive": self._vat, "source": "energyzero", "fetched_at_utc": now_utc.isoformat()}
        attrs_tomorrow = {"prices": tomorrow, "vat_inclusive": self._vat, "source": "energyzero", "fetched_at_utc": now_utc.isoformat()}

        async def push(suffix: str, value: Any, extra: dict[str, Any] | None = None, unit: str = "EUR/kWh", state_class: str | None = "measurement") -> None:
            entity = f"sensor.{self._slug}_{suffix}"
            await self._ha.post_state(
                entity_id=entity,
                state=value if value is not None else "unknown",
                unit=unit if value is not None else None,
                friendly_name=f"{self._friendly} {suffix.replace('_', ' ')}",
                device_class="monetary" if unit == "EUR/kWh" else None,
                state_class=state_class,
                extra_attrs=extra,
            )

        await push("now", price_now, extra={**attrs_today, "hour_of_day_local": hour_idx})
        await push("today_avg", s_today["avg"], extra=attrs_today)
        await push("today_min", s_today["min"], extra=attrs_today)
        await push("today_max", s_today["max"], extra=attrs_today)
        await push("tomorrow_avg", s_tomorrow["avg"], extra=attrs_tomorrow)
        await push("tomorrow_min", s_tomorrow["min"], extra=attrs_tomorrow)
        await push("tomorrow_max", s_tomorrow["max"], extra=attrs_tomorrow)
        await push("rank_now", rank_now, unit="", state_class=None,
                   extra={"description": "1 = goedkoopste uur van vandaag, 24 = duurste", **attrs_today})
        await push("negative_hours_today", s_today["negative"], unit="h", state_class="measurement",
                   extra=attrs_today)

        _LOG.info(
            "Prices update: now=%s €/kWh (rank %s/%d), today_avg=%s, tomorrow_avg=%s, neg-hours=%s",
            price_now, rank_now, len(today) or 0, s_today["avg"], s_tomorrow["avg"], s_today["negative"],
        )

        # Share snapshot with webhook /status endpoint.
        if self._on_update:
            self._on_update({
                "now":                  {"value": price_now, "unit": "EUR/kWh"},
                "today_avg":            {"value": s_today["avg"], "unit": "EUR/kWh"},
                "today_min":            {"value": s_today["min"], "unit": "EUR/kWh"},
                "today_max":            {"value": s_today["max"], "unit": "EUR/kWh"},
                "tomorrow_avg":         {"value": s_tomorrow["avg"], "unit": "EUR/kWh"},
                "tomorrow_min":         {"value": s_tomorrow["min"], "unit": "EUR/kWh"},
                "tomorrow_max":         {"value": s_tomorrow["max"], "unit": "EUR/kWh"},
                "rank_now":             {"value": rank_now, "unit": ""},
                "negative_hours_today": {"value": s_today["negative"], "unit": "h"},
                "prices_today":         {"value": today, "unit": ""},
                "prices_tomorrow":      {"value": tomorrow, "unit": ""},
            })

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as ex:  # noqa: BLE001
                _LOG.error("Prices poll faalde: %s", ex)
            await asyncio.sleep(self._poll_seconds)
