"""Async Modbus client voor Sofar HYD. Ondersteunt zowel TCP als RTU (serial/RS485).
Wraps pymodbus en doet de scaling/signed-conversie + retry logica.

KNOWN ISSUE (2026-07-14): Direct Modbus vanuit de HA addon Docker container
werkt NIET — pymodbus opent de serial port, verzendt frames, maar ontvangt
NOOIT een response ("No response received after 3 retries").

Bewezen feiten:
  - RS485 hardware (CH9102 CDC-ACM USB adapter op /dev/ttyACM0) werkt: de
    SolaX Modbus HA-integratie (draait in HA core process, NIET in Docker)
    ontvangt wél responses van de inverter.
  - Correcte settings: 19200 baud, 8N1 parity, FC03 (holding registers).
    FC04 (input registers) wordt NIET beantwoord door Sofar HYD.
  - SolaX Modbus (plugin: sofar/sofar_old) kan het inverter-serienummer
    niet vinden → herkent het model niet → maakt geen entities aan.
  - Vermoedelijke oorzaak: Docker container serial I/O verschilt van host
    process (HA core). Mogelijk CDC-ACM driver/buffering issue.

Workaround: gebruik HaSensorReader + HaBatteryController (leest HA sensors,
stuurt via HA service calls). Direct Modbus is disabled tot de container-
issue is opgelost.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Iterable

from pymodbus.client import AsyncModbusTcpClient, AsyncModbusSerialClient

from .registers import Register, SOFAR_HYD_REGISTERS

_LOG = logging.getLogger(__name__)

_ModbusClient = AsyncModbusTcpClient | AsyncModbusSerialClient


@dataclass
class Reading:
    name: str
    value: float | int
    unit: str
    description: str


def _decode(raw: list[int], reg: Register) -> int:
    """Convert pymodbus register-array → signed/unsigned int op basis van word_count."""
    if reg.word_count == 1:
        v = raw[0]
        if reg.signed and v & 0x8000:
            v -= 0x10000
        return v
    # 32-bit: Sofar HYD gebruikt big-endian word order (high word eerst).
    # raw[0] = high word, raw[1] = low word.
    hi, lo = raw[0], raw[1]
    v = (hi << 16) | lo
    if reg.signed and v & 0x80000000:
        v -= 0x100000000
    return v


class SofarModbusClient:
    """Async client. Hou één persistente verbinding open (TCP of Serial RTU)
    en herconnect bij failure."""

    def __init__(
        self,
        *,
        connection_type: str = "tcp",
        # TCP params
        host: str = "192.168.1.50",
        port: int = 502,
        # Serial RTU params
        serial_port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        # Common
        unit_id: int = 1,
        timeout: float = 5.0,
    ):
        self._connection_type = connection_type
        self._host = host
        self._port = port
        self._serial_port = serial_port
        self._baudrate = baudrate
        self._parity = parity
        self._stopbits = stopbits
        self._unit_id = unit_id
        self._timeout = timeout
        self._client: _ModbusClient | None = None
        self._lock = asyncio.Lock()

    def _make_client(self) -> _ModbusClient:
        if self._connection_type == "serial":
            return AsyncModbusSerialClient(
                port=self._serial_port,
                baudrate=self._baudrate,
                bytesize=8,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=self._timeout,
            )
        return AsyncModbusTcpClient(
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        )

    async def connect(self) -> None:
        async with self._lock:
            if self._client and self._client.connected:
                return
            self._client = self._make_client()
            # pymodbus 3.x: zet slave/unit ID op het client-object zelf.
            # Dit werkt in alle 3.x versies ongeacht keyword API changes.
            self._client.slave = self._unit_id
            ok = await self._client.connect()
            if not ok:
                if self._connection_type == "serial":
                    raise ConnectionError(
                        f"Modbus RTU connect faalde naar {self._serial_port}"
                    )
                raise ConnectionError(
                    f"Modbus TCP connect faalde naar {self._host}:{self._port}"
                )
            if self._connection_type == "serial":
                _LOG.info(
                    "Modbus connected (RTU) → %s @ %d baud (unit %s)",
                    self._serial_port, self._baudrate, self._unit_id,
                )
            else:
                _LOG.info(
                    "Modbus connected (TCP) → %s:%s (unit %s)",
                    self._host, self._port, self._unit_id,
                )

    async def close(self) -> None:
        async with self._lock:
            if self._client:
                self._client.close()
                self._client = None

    async def read_all(self, registers: Iterable[Register] = SOFAR_HYD_REGISTERS) -> list[Reading]:
        """Lees alle opgegeven registers. Errors per register worden gelogd maar
        stoppen de batch niet — partieel resultaat is beter dan helemaal niets."""
        await self.connect()
        out: list[Reading] = []
        assert self._client is not None
        for reg in registers:
            try:
                if reg.fc == "input":
                    resp = await self._client.read_input_registers(
                        reg.address, count=reg.word_count
                    )
                else:
                    resp = await self._client.read_holding_registers(
                        reg.address, count=reg.word_count
                    )
                if resp.isError():
                    _LOG.warning("Modbus error voor %s (0x%04X): %s", reg.name, reg.address, resp)
                    continue
                raw_int = _decode(resp.registers, reg)
                # Negatieve scale (bijv. -10) = multiply by |scale| en keer teken om.
                # Sofar conventie: battery charge = negatief, maar wij willen + = laden.
                if reg.scale < 0:
                    value = raw_int * abs(reg.scale) * -1
                elif reg.scale != 1.0:
                    value = raw_int * reg.scale
                else:
                    value = raw_int
                # Render integers als int wanneer schaal geheel is.
                if abs(reg.scale) in (1.0, 10.0, 100.0) and isinstance(value, float):
                    value = int(value)
                out.append(Reading(name=reg.name, value=value, unit=reg.unit, description=reg.description))
            except Exception as ex:  # noqa: BLE001
                _LOG.warning("Read faalde voor %s (0x%04X): %s", reg.name, reg.address, ex)
        return out

    async def write_holding(self, reg: Register, value: int) -> None:
        """Schrijf één holding-register (FC06). Voor 32-bit writes splitsen we
        in twee 16-bit words (big-endian word order: high word eerst)."""
        if reg.fc != "holding":
            raise ValueError(f"{reg.name} is geen writable holding-register")
        await self.connect()
        assert self._client is not None
        if reg.word_count == 1:
            resp = await self._client.write_register(reg.address, value=value & 0xFFFF)
        else:
            hi = (value >> 16) & 0xFFFF
            lo = value & 0xFFFF
            resp = await self._client.write_registers(reg.address, values=[hi, lo])
        if resp.isError():
            raise RuntimeError(f"Modbus write faalde voor {reg.name}: {resp}")
        _LOG.info("Modbus wrote %s = %s (raw)", reg.name, value)
