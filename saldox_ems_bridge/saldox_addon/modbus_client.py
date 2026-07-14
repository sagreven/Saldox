"""Async Modbus client voor Sofar HYD. Ondersteunt zowel TCP als RTU (serial/RS485).
Wraps pymodbus en doet de scaling/signed-conversie + retry logica."""
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
    # 32-bit: high word eerst (Sofar gebruikt big-endian word order).
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
            self._host,
            port=self._port,
            timeout=self._timeout,
        )

    async def connect(self) -> None:
        async with self._lock:
            if self._client and self._client.connected:
                return
            self._client = self._make_client()
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
                        reg.address, reg.word_count, self._unit_id
                    )
                else:
                    resp = await self._client.read_holding_registers(
                        reg.address, reg.word_count, self._unit_id
                    )
                if resp.isError():
                    _LOG.warning("Modbus error voor %s (0x%04X): %s", reg.name, reg.address, resp)
                    continue
                raw_int = _decode(resp.registers, reg)
                value: float | int = raw_int * reg.scale if reg.scale != 1.0 else raw_int
                # Render integers als int wanneer schaal=1.0 voor cleaner JSON.
                if reg.scale == 1.0:
                    value = int(raw_int)
                out.append(Reading(name=reg.name, value=value, unit=reg.unit, description=reg.description))
            except Exception as ex:  # noqa: BLE001
                _LOG.warning("Read faalde voor %s (0x%04X): %s", reg.name, reg.address, ex)
        return out

    async def write_holding(self, reg: Register, value: int) -> None:
        """Schrijf één holding-register (FC06). Voor 32-bit writes splitsen we
        in twee 16-bit words (big-endian)."""
        if reg.fc != "holding":
            raise ValueError(f"{reg.name} is geen writable holding-register")
        await self.connect()
        assert self._client is not None
        # pymodbus 3.7: write_register(address, value, slave) — positional args
        # voor compat met verschillende pymodbus versies.
        if reg.word_count == 1:
            resp = await self._client.write_register(reg.address, value & 0xFFFF, self._unit_id)
        else:
            hi = (value >> 16) & 0xFFFF
            lo = value & 0xFFFF
            resp = await self._client.write_registers(reg.address, [hi, lo], self._unit_id)
        if resp.isError():
            raise RuntimeError(f"Modbus write faalde voor {reg.name}: {resp}")
        _LOG.info("Modbus wrote %s = %s (raw)", reg.name, value)
