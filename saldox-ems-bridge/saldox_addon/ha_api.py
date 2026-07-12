"""Home Assistant Supervisor API client.

Schrijft sensor-states via POST /core/api/states/<entity_id>. SUPERVISOR_TOKEN
is automatisch gezet door de add-on runtime wanneer hassio_api: true /
homeassistant_api: true in config.yaml staat.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp

_LOG = logging.getLogger(__name__)


class HomeAssistantClient:
    """Minimaal: state-write per sensor."""

    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or os.environ.get("HA_SUPERVISOR_URL") or "http://supervisor/core").rstrip("/")
        self.token = token or os.environ.get("SUPERVISOR_TOKEN") or ""
        if not self.token:
            _LOG.warning("Geen SUPERVISOR_TOKEN gevonden — HA state-push zal 401 geven buiten een Supervisor-context.")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def post_state(
        self,
        entity_id: str,
        state: Any,
        unit: str | None = None,
        friendly_name: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        extra_attrs: dict[str, Any] | None = None,
    ) -> bool:
        """POST /api/states/<entity_id> met de gegeven state + attribute-set."""
        session = await self._get_session()
        attrs: dict[str, Any] = dict(extra_attrs or {})
        if unit:
            attrs["unit_of_measurement"] = unit
        if friendly_name:
            attrs["friendly_name"] = friendly_name
        if device_class:
            attrs["device_class"] = device_class
        if state_class:
            attrs["state_class"] = state_class

        payload = {"state": str(state), "attributes": attrs}
        url = f"{self.base_url}/api/states/{entity_id}"
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status in (200, 201):
                    return True
                body = await resp.text()
                _LOG.warning("HA state-post %s → HTTP %s: %s", entity_id, resp.status, body[:200])
                return False
        except aiohttp.ClientError as ex:
            _LOG.warning("HA state-post network error voor %s: %s", entity_id, ex)
            return False

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        """GET /api/states/<entity_id> — returns full state object or None."""
        session = await self._get_session()
        url = f"{self.base_url}/api/states/{entity_id}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except aiohttp.ClientError:
            return None

    async def get_states(self, entity_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Batch-read multiple entity states. Returns {entity_id: state_obj}."""
        results: dict[str, dict[str, Any]] = {}
        for eid in entity_ids:
            s = await self.get_state(eid)
            if s is not None:
                results[eid] = s
        return results

    async def get_history(
        self, entity_id: str, start: str, end: str | None = None
    ) -> list[dict[str, Any]]:
        """GET /api/history/period/{start}?filter_entity_id={eid}&end_time={end}
        Returns list of state-change dicts [{state, last_changed, ...}, ...]."""
        session = await self._get_session()
        params = f"filter_entity_id={entity_id}&minimal_response&significant_changes_only"
        if end:
            params += f"&end_time={end}"
        url = f"{self.base_url}/api/history/period/{start}?{params}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # HA returns [[{state changes}]] — one list per entity
                    return data[0] if data and len(data) > 0 else []
                _LOG.warning("HA history %s → HTTP %s", entity_id, resp.status)
                return []
        except aiohttp.ClientError as ex:
            _LOG.warning("HA history error for %s: %s", entity_id, ex)
            return []

    async def call_service(
        self, domain: str, service: str, data: dict[str, Any] | None = None
    ) -> bool:
        """POST /api/services/<domain>/<service>."""
        session = await self._get_session()
        url = f"{self.base_url}/api/services/{domain}/{service}"
        try:
            async with session.post(url, json=data or {}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return True
                body = await resp.text()
                _LOG.warning("HA service %s.%s → HTTP %s: %s", domain, service, resp.status, body[:200])
                return False
        except aiohttp.ClientError as ex:
            _LOG.warning("HA service %s.%s error: %s", domain, service, ex)
            return False
