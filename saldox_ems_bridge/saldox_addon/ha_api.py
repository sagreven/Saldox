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
