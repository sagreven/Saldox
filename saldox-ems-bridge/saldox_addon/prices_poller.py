"""Saldox API day-ahead prijzen voor Home Assistant.

Haalt uurprijzen op via de Saldox API en publiceert ze als HA sensors.
Vandaag's prijzen zijn altijd beschikbaar; morgen's prijzen worden typisch
na ~13:00 CET gepubliceerd (na de EPEX day-ahead-veiling).

Gepubliceerde entities (slug standaard `saldox_price`):
  sensor.{slug}_now                 — actuele EUR/kWh (huidige uur)
  sensor.{slug}_today_avg           — gemiddelde van vandaag
  sensor.{slug}_today_min           — laagste van vandaag
  sensor.{slug}_today_max           — hoogste van vandaag
  sensor.{slug}_tomorrow_avg        — idem voor morgen (na ~13:00 CET)
  sensor.{slug}_tomorrow_min        — idem
  sensor.{slug}_tomorrow_max        — idem
  sensor.{slug}_rank_now            — 1..24 (1 = goedkoopste uur van vandaag)
  sensor.{slug}_negative_hours_today — aantal uren met prijs < 0

De _now sensor draagt als attributes `today_prices` en `tomorrow_prices`
arrays van {hour, price} objecten zodat HA-cards het profiel kunnen plotten.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import aiohttp

from .ha_api import HomeAssistantClient

_LOG = logging.getLogger(__name__)


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
    """Pollt de Saldox API (vandaag + morgen) en pusht prijzen naar HA."""

    def __init__(
        self,
        ha: HomeAssistantClient,
        saldox_api_url: str,
        saldox_api_token: str,
        slug: str = "saldox_price",
        friendly: str = "Saldox prijs",
        poll_minutes: int = 15,
        on_update: Callable[[dict[str, dict]], None] | None = None,
    ):
        self._ha = ha
        self._api_url = saldox_api_url.rstrip("/")
        self._api_token = saldox_api_token
        self._slug = slug
        self._friendly = friendly
        self._poll_seconds = max(60, poll_minutes * 60)
        self._session: aiohttp.ClientSession | None = None
        self._on_update = on_update

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_token}"}
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch_hours(self, from_utc: str, to_utc: str) -> list[dict[str, Any]]:
        """Fetch hourly prices from Saldox API for the given UTC range.

        Returns list of {hour: int, price: float} dicts, or empty list on error.
        Expected API response: [{"hourUtc":"2026-07-08T14:00:00Z","priceEurKwh":0.08}, ...]
        """
        session = await self._get_session()
        url = f"{self._api_url}/api/prices/hourly"
        params = {"from": from_utc, "to": to_utc}
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    _LOG.warning("Saldox API %s -> HTTP %s", url, resp.status)
                    return []
                data = await resp.json()
        except aiohttp.ClientError as ex:
            _LOG.warning("Saldox API fetch failed: %s", ex)
            return []

        if not isinstance(data, list):
            _LOG.warning("Saldox API unexpected response type: %s", type(data).__name__)
            return []

        now_utc = datetime.now(timezone.utc)
        offset = _nl_offset_for(now_utc)
        result = []
        for entry in data:
            hour_utc_str = entry.get("hourUtc", "")
            try:
                dt_utc = datetime.fromisoformat(hour_utc_str.replace("Z", "+00:00"))
                dt_local = dt_utc + offset
                h = dt_local.hour
            except (ValueError, AttributeError):
                h = int(entry.get("hour", 0))
            result.append({
                "hour": h,
                "price": float(entry.get("priceEurKwh", entry.get("pricePerKwh", 0.0))),
            })
        return result

    @staticmethod
    def _stats(hourly: list[dict[str, Any]]) -> dict[str, Any]:
        if not hourly:
            return {"avg": None, "min": None, "max": None, "negative": 0}
        prices = [h["price"] for h in hourly]
        return {
            "avg": round(sum(prices) / len(prices), 4),
            "min": round(min(prices), 4),
            "max": round(max(prices), 4),
            "negative": sum(1 for p in prices if p < 0),
        }

    async def tick(self) -> None:
        now_utc = datetime.now(timezone.utc)
        offset = _nl_offset_for(now_utc)

        # Local midnight today, expressed in UTC.
        local_now = now_utc + offset
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_utc = local_midnight - offset
        tomorrow_start_utc = today_start_utc + timedelta(days=1)
        day_after_start_utc = today_start_utc + timedelta(days=2)

        today_from = today_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        today_to = tomorrow_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        tomorrow_from = tomorrow_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        tomorrow_to = day_after_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        today_hours = await self._fetch_hours(today_from, today_to)
        tomorrow_hours = await self._fetch_hours(tomorrow_from, tomorrow_to)

        # Current hour (local) -> find matching price.
        hour_idx = local_now.hour
        price_now: float | None = None
        rank_now: int | None = None

        if today_hours:
            # Find current hour's price.
            for h in today_hours:
                if h["hour"] == hour_idx:
                    price_now = round(h["price"], 4)
                    break

            # Rank: sort all hours by price ascending, find position of current hour.
            sorted_hours = sorted(today_hours, key=lambda h: h["price"])
            for i, h in enumerate(sorted_hours):
                if h["hour"] == hour_idx:
                    rank_now = i + 1
                    break

        s_today = self._stats(today_hours)
        s_tomorrow = self._stats(tomorrow_hours)

        fetched_at = now_utc.isoformat()

        async def push(
            suffix: str,
            value: Any,
            extra: dict[str, Any] | None = None,
            unit: str = "EUR/kWh",
            device_class: str | None = "monetary",
            state_class: str | None = "measurement",
        ) -> None:
            entity = f"sensor.{self._slug}_{suffix}"
            await self._ha.post_state(
                entity_id=entity,
                state=value if value is not None else "unknown",
                unit=unit if value is not None else None,
                friendly_name=f"{self._friendly} {suffix.replace('_', ' ')}",
                device_class=device_class if value is not None else None,
                state_class=state_class,
                extra_attrs=extra,
            )

        # _now sensor carries the full hourly arrays as attributes.
        now_attrs = {
            "today_prices": today_hours,
            "tomorrow_prices": tomorrow_hours,
            "hour_of_day_local": hour_idx,
            "source": "saldox-api",
            "fetched_at_utc": fetched_at,
        }

        common_attrs = {"source": "saldox-api", "fetched_at_utc": fetched_at}

        await push("now", price_now, extra=now_attrs)
        await push("today_avg", s_today["avg"], extra=common_attrs)
        await push("today_min", s_today["min"], extra=common_attrs)
        await push("today_max", s_today["max"], extra=common_attrs)
        await push("tomorrow_avg", s_tomorrow["avg"], extra=common_attrs)
        await push("tomorrow_min", s_tomorrow["min"], extra=common_attrs)
        await push("tomorrow_max", s_tomorrow["max"], extra=common_attrs)
        await push(
            "rank_now", rank_now,
            unit="",
            device_class=None,
            state_class=None,
            extra={"description": "1 = goedkoopste uur van vandaag, 24 = duurste", **common_attrs},
        )
        await push(
            "negative_hours_today", s_today["negative"],
            unit="h",
            device_class=None,
            state_class="measurement",
            extra=common_attrs,
        )

        _LOG.info(
            "Prices update: now=%s EUR/kWh (rank %s/%d), today_avg=%s, tomorrow_avg=%s, neg-hours=%s",
            price_now, rank_now, len(today_hours) or 0, s_today["avg"], s_tomorrow["avg"], s_today["negative"],
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
                "prices_today":         {"value": today_hours, "unit": ""},
                "prices_tomorrow":      {"value": tomorrow_hours, "unit": ""},
            })

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as ex:  # noqa: BLE001
                _LOG.error("Prices poll failed: %s\n%s", ex, traceback.format_exc())
            await asyncio.sleep(self._poll_seconds)
