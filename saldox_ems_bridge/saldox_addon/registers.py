"""Sofar Solar HYD 5-20KTL-3PH Modbus register map.

Bron: community-gepubliceerde register-PDF's voor de Sofar HYD-serie + SolarMan
DataLogger Stick documentation. Verifieer met `Sofar HYD 5-20KTL-3PH Modbus
Protocol V1.x` PDF op de Sofar-website bij firmware-updates.

Register-typen:
  • holding (FC03) — read-write configuratie + writable controls
  • input   (FC04) — read-only realtime metingen

Schaling: het `scale` veld zegt hoe de raw int omgezet wordt naar fysieke
eenheid. Sofar gebruikt veel `0.1 kWh` / `0.01 V` / `0.001 kVar` schalen.

Signed: `signed=True` betekent dat de raw waarde tweecomplement is (bv. negatief
power = teruglevering / discharge).
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Register:
    name: str
    address: int
    word_count: int       # 1 of 2 (32-bit waardes spannen 2 registers)
    fc: Literal["holding", "input"]
    scale: float
    unit: str
    signed: bool = False
    description: str = ""


# Subset — meest-gebruikte registers voor EMS-monitoring. Volledige map
# (300+ registers) is extensible via dezelfde dataclass.
SOFAR_HYD_REGISTERS: list[Register] = [
    # ----- Inverter state -----
    # NB: Sofar HYD beantwoordt ALLE registers via FC03 (holding), niet FC04 (input).
    # SolaX Modbus plugin_sofar.py bevestigt: register_type = REG_HOLDING voor alles.
    Register("inverter_status",          0x0404, 1, "holding", 1.0,   "",        description="0=stand-by, 1=self-check, 2=normal, 3=fault, 4=permanent-fault"),
    Register("inverter_temperature_c",   0x0418, 1, "holding", 1.0,   "°C", signed=True),
    Register("inverter_fault_code",      0x0414, 1, "holding", 1.0,   "",        description="0 = geen fout; non-zero = error-code uit handleiding bijlage A"),

    # ----- PV-input (DC) -----
    Register("pv1_voltage_v",            0x0584, 1, "holding", 0.1,   "V"),
    Register("pv1_current_a",            0x0585, 1, "holding", 0.01,  "A"),
    Register("pv2_voltage_v",            0x0588, 1, "holding", 0.1,   "V"),
    Register("pv2_current_a",            0x0589, 1, "holding", 0.01,  "A"),
    Register("pv_total_power_w",         0x05C4, 2, "holding", 100.0, "W",       description="Totale PV-productie (32-bit). Schaal × 100 (registers leveren 0.01 kW)"),

    # ----- AC output (grid-side) -----
    Register("ac_active_power_w",        0x0485, 2, "holding", 100.0, "W", signed=True, description="+ = export naar grid, − = import van grid"),
    Register("ac_frequency_hz",          0x0480, 1, "holding", 0.01,  "Hz"),

    # ----- Battery -----
    Register("battery_soc_percent",      0x0608, 1, "holding", 1.0,   "%"),
    Register("battery_power_w",          0x0606, 2, "holding", 100.0, "W", signed=True, description="+ = laden, − = ontladen"),
    Register("battery_voltage_v",        0x0604, 1, "holding", 0.1,   "V"),
    Register("battery_temperature_c",    0x060A, 1, "holding", 0.1,   "°C", signed=True),

    # ----- Energy counters -----
    Register("today_production_kwh",     0x0686, 1, "holding", 0.1,   "kWh"),
    Register("total_production_kwh",     0x0684, 2, "holding", 0.1,   "kWh",     description="32-bit lifetime totaal"),
    Register("today_consumption_kwh",    0x068A, 1, "holding", 0.1,   "kWh"),
    Register("today_import_kwh",         0x068C, 1, "holding", 0.1,   "kWh"),
    Register("today_export_kwh",         0x068E, 1, "holding", 0.1,   "kWh"),
    Register("battery_input_today_kwh",  0x0694, 1, "holding", 0.1,   "kWh", description="Batterij geladen vandaag"),
    Register("battery_output_today_kwh", 0x0696, 1, "holding", 0.1,   "kWh", description="Batterij ontladen vandaag"),

    # ----- Extra registers -----
    Register("battery_soh_percent",      0x060B, 1, "holding", 1.0,   "%"),
    Register("battery_cycles",           0x060C, 2, "holding", 1.0,   ""),
    Register("load_power_w",             0x04AF, 2, "holding", 100.0, "W",       description="Home consumption"),
    Register("pv1_power_w",              0x0586, 2, "holding", 100.0, "W"),
    Register("pv2_power_w",              0x058A, 2, "holding", 100.0, "W"),
    Register("grid_frequency_hz",        0x0480, 1, "holding", 0.01,  "Hz"),

    # ----- Writable controls (voor Saldox-commands → Modbus-write) -----
    # Active power limit (0-100% van max) — gebruikt voor PV-curtailment bij
    # negatieve prijzen of overproductie.
    Register("active_power_limit_pct",   0x1004, 1, "holding", 1.0, "%",       description="Schrijf 0-100. Default 100 = geen begrenzing."),
    # Remote on/off switch
    Register("remote_switch",            0x1104, 1, "holding", 1.0, "",        description="0=Off, 1=On"),
    # Battery charge/discharge mode: 0=auto, 1=force-charge, 2=force-discharge, 3=standby
    Register("battery_mode",             0x1110, 1, "holding", 1.0, "",        description="0=auto, 1=force-charge, 2=force-discharge, 3=standby"),
    Register("battery_charge_power_w",   0x1112, 2, "holding", 100.0, "W",     description="Doel-laadvermogen wanneer mode=force-charge"),
    Register("battery_discharge_power_w",0x1114, 2, "holding", 100.0, "W",     description="Doel-ontlaadvermogen wanneer mode=force-discharge"),

    # ----- Energy storage mode (writable) -----
    Register("energy_storage_mode",      0x1200, 1, "holding", 1.0, "",        description="0=Self Use, 1=Time of Use, 2=Timing Mode, 3=Passive Mode, 4=Peak Cut"),

    # ----- Passive Mode registers (writable, signed) -----
    Register("passive_max_battery_power_w", 0x1187, 1, "holding", 10.0, "W", signed=True,
             description="Max battery power in Passive Mode. + = charge limit"),
    Register("passive_min_battery_power_w", 0x1188, 1, "holding", 10.0, "W", signed=True,
             description="Min battery power in Passive Mode. - = discharge limit"),
    Register("passive_desired_grid_power_w", 0x1189, 1, "holding", 10.0, "W", signed=True,
             description="Desired grid power in Passive Mode. + = import, - = export"),
]


def by_name(name: str) -> Register:
    for r in SOFAR_HYD_REGISTERS:
        if r.name == name:
            return r
    raise KeyError(f"Unknown register: {name}")
