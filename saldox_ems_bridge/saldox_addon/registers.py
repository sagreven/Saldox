"""Sofar Solar HYD 5-20KTL-3PH Modbus register map.

Bron: SolarmanV2 sofar_g3hyd.yaml profiel (davidrapan/ha-solarman) — bewezen
correct op 2026-07-14 met 138 live entities via WiFi logger LSW3.
Cross-verified met wills106/homeassistant-solax-modbus plugin_sofar.py.

Register-typen:
  • holding (FC03) — ALLE registers. FC04 wordt NIET beantwoord door de firmware.

Seriële verbinding:
  • Baudrate: 9600 (YSP-8.5 CH343G adapter)
  • Parity: N (8N1)
  • Pad: /dev/serial/by-id/usb-1a86_USB_Single_Serial_5ACB093727-if00

Schaling: het `scale` veld converteert raw register waarde naar fysieke eenheid.
Negatieve scale (bijv. -10) betekent: raw × |scale|, maar teken is omgekeerd
(Sofar conventie: battery charge = negatief register, maar wij willen + = laden).

Signed: `signed=True` → raw waarde is tweecomplement 16-bit of 32-bit.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Register:
    name: str
    address: int
    word_count: int       # 1 = 16-bit, 2 = 32-bit
    fc: Literal["holding", "input"]
    scale: float
    unit: str
    signed: bool = False
    swap_words: bool = False  # True = little-endian word order (low word eerst)
    description: str = ""


# Register map gebaseerd op SolarmanV2 sofar_g3hyd.yaml (bewezen correct)
SOFAR_HYD_REGISTERS: list[Register] = [
    # ----- Inverter state -----
    Register("inverter_status",          0x0404, 1, "holding", 1.0,   "",        description="0=wait, 1=check, 2=normal, 3=fault, 4=permanent-fault"),
    Register("inverter_temperature_c",   0x0418, 1, "holding", 1.0,   "°C", signed=True),
    Register("inverter_fault_code",      0x0414, 1, "holding", 1.0,   "",        description="0 = geen fout"),

    # ----- PV-input (DC) -----
    # PV power is U16 × 10 W (niet U32 × 100 zoals de oude PDF zei)
    Register("pv1_voltage_v",            0x0584, 1, "holding", 0.1,   "V"),
    Register("pv1_current_a",            0x0585, 1, "holding", 0.01,  "A"),
    Register("pv1_power_w",              0x0586, 1, "holding", 10.0,  "W"),
    Register("pv2_voltage_v",            0x0588, 1, "holding", 0.1,   "V"),
    Register("pv2_current_a",            0x0589, 1, "holding", 0.01,  "A"),
    Register("pv2_power_w",              0x058A, 1, "holding", 10.0,  "W"),
    Register("pv_total_power_w",         0x05C4, 1, "holding", 100.0, "W"),

    # ----- AC output (grid-side) -----
    # Grid power: S16 × -10 W (negatief = export, positief = import in Sofar conventie)
    Register("ac_active_power_w",        0x0488, 1, "holding", -10.0, "W", signed=True,
             description="Grid PCC power. Scale -10: Sofar negatief=import, wij + = import"),
    Register("ac_frequency_hz",          0x0484, 1, "holding", 0.01,  "Hz"),
    Register("load_power_w",             0x04AF, 1, "holding", 10.0,  "W", signed=True,
             description="Home consumption"),

    # ----- Battery -----
    # Battery power: S16 × -10 W (Sofar: negatief = charge, positief = discharge)
    Register("battery_power_w",          0x0606, 1, "holding", -10.0, "W", signed=True,
             description="Battery power. Scale -10: Sofar neg=charge, wij + = laden"),
    Register("battery_voltage_v",        0x0604, 1, "holding", 0.1,   "V"),
    Register("battery_temperature_c",    0x0607, 1, "holding", 1.0,   "°C", signed=True),
    Register("battery_soc_percent",      0x0608, 1, "holding", 1.0,   "%"),
    Register("battery_soh_percent",      0x0609, 1, "holding", 1.0,   "%"),
    Register("battery_cycles",           0x060A, 1, "holding", 1.0,   ""),

    # ----- Energy counters (U32, little-endian word order) -----
    Register("today_production_kwh",     0x0684, 2, "holding", 0.01,  "kWh"),
    Register("today_consumption_kwh",    0x0688, 2, "holding", 0.01,  "kWh"),
    Register("today_import_kwh",         0x068C, 2, "holding", 0.01,  "kWh"),
    Register("today_export_kwh",         0x0690, 2, "holding", 0.01,  "kWh"),
    Register("battery_input_today_kwh",  0x0694, 2, "holding", 0.01,  "kWh"),
    Register("battery_output_today_kwh", 0x0698, 2, "holding", 0.01,  "kWh"),

    # ----- Writable controls -----
    Register("remote_switch",            0x1104, 1, "holding", 1.0, "",
             description="0=Off, 1=On"),
    Register("energy_storage_mode",      0x1110, 1, "holding", 1.0, "",
             description="0=Self Use, 1=Time of Use, 2=Optimized Revenue, 3=Passive, 4=Peak Shaving"),

    # ----- Passive Mode registers (S32, big-endian word order [hi, lo]) -----
    Register("passive_desired_grid_power_w", 0x1187, 2, "holding", 1.0, "W", signed=True, swap_words=False,
             description="Desired grid power in Passive Mode. + = import, - = export"),
    Register("passive_min_battery_power_w",  0x1189, 2, "holding", 1.0, "W", signed=True, swap_words=False,
             description="Min battery power in Passive Mode. - = discharge limit"),
    Register("passive_max_battery_power_w",  0x118B, 2, "holding", 1.0, "W", signed=True, swap_words=False,
             description="Max battery power in Passive Mode. + = charge limit"),
]


def by_name(name: str) -> Register:
    for r in SOFAR_HYD_REGISTERS:
        if r.name == name:
            return r
    raise KeyError(f"Unknown register: {name}")
