"""Saldox Arbitrage Simulator — backtest battery strategies on historical data.

Compares four strategies:
  1. Naive      — no battery, pay spot price for all consumption
  2. Self Use   — battery covers home deficit only (no grid arbitrage)
  3. Saldering  — charge cheap → PV saldering → self-use expensive (NL)
  4. Export     — charge cheap → discharge to grid in expensive hours

Supports:
  - Live data from Saldox API (prices + PV forecast + consumption)
  - Synthetic/configurable PV & consumption profiles
  - Parameter sweep (grid search) to find optimal config
  - Multi-day backtesting with day-by-day breakdown

Usage (standalone):
    python -m saldox_addon.arbitrage_simulator [--days 7] [--api-url URL] [--api-token TOKEN]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import product
from typing import Any

import aiohttp

from .arbitrage_optimizer import ArbitrageConfig, ArbitrageOptimizer, ArbitrageResult

_LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HourSlot:
    """One hour of historical/synthetic data."""
    hour_utc: datetime
    price_eur_kwh: float
    pv_watts: float = 0.0
    consumption_watts: float = 800.0  # NL avg ~800W baseline


@dataclass
class DayResult:
    """Results for a single simulated day."""
    date: str
    strategy: str
    profit_eur: float = 0.0
    charge_cost_eur: float = 0.0
    discharge_revenue_eur: float = 0.0
    pv_savings_eur: float = 0.0
    naive_cost_eur: float = 0.0
    savings_vs_naive_eur: float = 0.0
    cycles: int = 0


@dataclass
class SimulationResult:
    """Aggregate results for a full simulation run."""
    strategy: str
    config: dict
    days: list[DayResult] = field(default_factory=list)
    total_profit_eur: float = 0.0
    total_naive_cost_eur: float = 0.0
    total_savings_eur: float = 0.0
    avg_daily_profit_eur: float = 0.0
    total_cycles: int = 0


@dataclass
class SweepResult:
    """One parameter combination in a sweep."""
    params: dict
    profit_eur: float
    savings_eur: float
    cycles: int


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

async def fetch_prices_from_api(
    api_url: str,
    api_token: str,
    from_utc: datetime,
    to_utc: datetime,
) -> list[dict]:
    """Fetch hourly prices from Saldox API in 31-day chunks."""
    all_prices: list[dict] = []
    headers = {"Authorization": f"Bearer {api_token}"}
    chunk_days = 30  # API max is 31

    async with aiohttp.ClientSession(headers=headers) as session:
        cursor = from_utc
        while cursor < to_utc:
            chunk_end = min(cursor + timedelta(days=chunk_days), to_utc)
            url = f"{api_url.rstrip('/')}/api/prices/hourly"
            params = {
                "from": cursor.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            all_prices.extend(data)
                            _LOG.info("Fetched %d prices for %s → %s",
                                      len(data), cursor.date(), chunk_end.date())
                    else:
                        _LOG.warning("API HTTP %s for %s → %s", resp.status, cursor.date(), chunk_end.date())
            except aiohttp.ClientError as ex:
                _LOG.warning("API fetch failed: %s", ex)
            cursor = chunk_end

    return all_prices


def parse_api_prices(raw: list[dict]) -> list[HourSlot]:
    """Convert API response [{hourUtc, priceEurKwh}, ...] to HourSlots."""
    slots = []
    for entry in raw:
        hour_str = entry.get("hourUtc", "")
        try:
            dt = datetime.fromisoformat(hour_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        price = float(entry.get("priceEurKwh", entry.get("pricePerKwh", 0)))
        slots.append(HourSlot(hour_utc=dt, price_eur_kwh=price))
    slots.sort(key=lambda s: s.hour_utc)
    return slots


def generate_pv_profile(hour_local: int, peak_kw: float = 10.0) -> float:
    """Synthetic bell curve PV profile (W). Peak at solar noon (13:00 local)."""
    # Gaussian-ish centered on 13:00, width ~4h
    import math
    center = 13.0
    sigma = 4.0
    if 5 <= hour_local <= 21:
        factor = math.exp(-0.5 * ((hour_local - center) / sigma) ** 2)
        return peak_kw * 1000 * factor
    return 0.0


def generate_consumption_profile(hour_local: int, base_w: float = 800.0) -> float:
    """Synthetic NL household consumption profile (W).

    Peaks at 7-9 (morning) and 17-21 (evening). Low at night.
    Based on E1A Liander load profile shape.
    """
    profiles = {
        0: 0.5, 1: 0.4, 2: 0.35, 3: 0.35, 4: 0.4, 5: 0.5,
        6: 0.7, 7: 1.2, 8: 1.3, 9: 1.1, 10: 0.9, 11: 0.85,
        12: 1.0, 13: 0.9, 14: 0.8, 15: 0.8, 16: 0.9, 17: 1.3,
        18: 1.5, 19: 1.4, 20: 1.3, 21: 1.1, 22: 0.9, 23: 0.6,
    }
    return base_w * profiles.get(hour_local, 1.0)


def enrich_slots_with_profiles(
    slots: list[HourSlot],
    pv_peak_kw: float = 10.0,
    base_consumption_w: float = 800.0,
    nl_offset_hours: int = 2,  # CEST
) -> list[HourSlot]:
    """Add synthetic PV and consumption to price-only slots."""
    for s in slots:
        local_hour = (s.hour_utc + timedelta(hours=nl_offset_hours)).hour
        if s.pv_watts == 0:
            s.pv_watts = generate_pv_profile(local_hour, pv_peak_kw)
        if s.consumption_watts == 800.0:  # default → replace with profile
            s.consumption_watts = generate_consumption_profile(local_hour, base_consumption_w)
    return slots


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def slots_to_timeline(slots: list[HourSlot]) -> list[dict]:
    """Convert HourSlots to the timeline format expected by ArbitrageOptimizer."""
    timeline = []
    for s in slots:
        end = s.hour_utc + timedelta(hours=1)
        timeline.append({
            "startUtc": s.hour_utc.isoformat(),
            "endUtc": end.isoformat(),
            "priceEurKwh": s.price_eur_kwh,
            "pvWatts": s.pv_watts,
            "consumptionWatts": s.consumption_watts,
        })
    return timeline


def compute_naive_cost(slots: list[HourSlot]) -> float:
    """Cost without battery: pay spot price for net consumption (import)."""
    total = 0.0
    for s in slots:
        net_import_kwh = max(0, s.consumption_watts - s.pv_watts) / 1000.0
        net_export_kwh = max(0, s.pv_watts - s.consumption_watts) / 1000.0
        # Import costs money, export earns (saldering = same price)
        total += net_import_kwh * s.price_eur_kwh
        total -= net_export_kwh * s.price_eur_kwh  # saldering credit
    return total


def simulate_selfuse(
    slots: list[HourSlot],
    config: ArbitrageConfig,
    initial_soc_kwh: float,
) -> ArbitrageResult:
    """Self-use only: PV surplus → battery → discharge when consumption > PV.

    No grid arbitrage. Battery only stores PV surplus and covers home deficit.
    Uses per-mode power limits from config.
    """
    soc = initial_soc_kwh
    min_soc = config.capacity_kwh * 0.10  # 10% min for self-use
    charge_target = config.charge_soc_limit_kwh
    pv_charge_kw = config.eff_pv_charge_kw
    ac_discharge_kw = config.eff_ac_discharge_kw
    pv_savings = 0.0
    total_charged = 0.0
    total_discharged = 0.0

    for s in slots:
        net_w = s.pv_watts - s.consumption_watts

        # PV surplus → charge battery (PV charge limit)
        if net_w > config.pv_surplus_threshold_w:
            surplus_kwh = net_w / 1000.0
            room = charge_target - soc
            charge = min(surplus_kwh, room, pv_charge_kw)
            if charge > 0.01:
                soc += charge
                total_charged += charge
                pv_savings += charge * s.price_eur_kwh

        # Deficit → discharge battery (AC discharge limit)
        elif net_w < 0:
            deficit_kwh = -net_w / 1000.0
            if deficit_kwh > 0.01 and soc > min_soc:
                available = soc - min_soc
                drain = min(deficit_kwh, available, ac_discharge_kw)
                if drain > 0.01:
                    effective = drain * config.efficiency
                    soc -= drain
                    total_discharged += drain
                    pv_savings += effective * s.price_eur_kwh

        soc = max(0, min(config.capacity_kwh, soc))

    cycles = min(
        int(total_charged / config.capacity_kwh + 0.5) if config.capacity_kwh > 0 else 0,
        int(total_discharged / config.capacity_kwh + 0.5) if config.capacity_kwh > 0 else 0,
    )
    return ArbitrageResult(
        projected_profit_eur=0,
        charge_cost_eur=0,
        discharge_revenue_eur=round(pv_savings, 2),
        pv_savings_eur=round(pv_savings, 2),
        cycles=cycles,
        summary=f"selfuse: {cycles} cycli, PV-besparing €{pv_savings:.2f}",
    )


def simulate_strategy(
    strategy: str,
    slots: list[HourSlot],
    config: ArbitrageConfig,
    initial_soc_kwh: float | None = None,
) -> ArbitrageResult:
    """Run one strategy on a set of hourly slots."""
    soc = initial_soc_kwh if initial_soc_kwh is not None else config.capacity_kwh * 0.5

    if strategy == "naive":
        return ArbitrageResult(summary="Geen batterij")

    if strategy == "selfuse":
        return simulate_selfuse(slots, config, soc)

    cfg = ArbitrageConfig(
        capacity_kwh=config.capacity_kwh,
        max_power_kw=config.max_power_kw,
        ac_charge_kw=config.ac_charge_kw,
        pv_charge_kw=config.pv_charge_kw,
        ac_discharge_kw=config.ac_discharge_kw,
        export_discharge_kw=config.export_discharge_kw,
        efficiency=config.efficiency,
        pv_surplus_threshold_w=config.pv_surplus_threshold_w,
        charge_soc_target_pct=config.charge_soc_target_pct,
        min_soc_pct=config.min_soc_pct,
        min_spread_eur=config.min_spread_eur,
        night_start_hour=config.night_start_hour,
        night_end_hour=config.night_end_hour,
        max_cycles_per_day=config.max_cycles_per_day,
        grid_export_enabled=(strategy == "export"),
    )

    timeline = slots_to_timeline(slots)
    optimizer = ArbitrageOptimizer(cfg)
    return optimizer.optimize(timeline, soc)


def run_day_simulation(
    day_slots: list[HourSlot],
    config: ArbitrageConfig,
    strategy: str,
    initial_soc_kwh: float | None = None,
) -> DayResult:
    """Simulate one day for one strategy."""
    if not day_slots:
        return DayResult(date="?", strategy=strategy)

    date_str = day_slots[0].hour_utc.strftime("%Y-%m-%d")
    naive_cost = compute_naive_cost(day_slots)

    result = simulate_strategy(strategy, day_slots, config, initial_soc_kwh)

    if strategy == "naive":
        return DayResult(
            date=date_str,
            strategy=strategy,
            naive_cost_eur=round(naive_cost, 4),
            profit_eur=0,
            savings_vs_naive_eur=0,
        )

    # Net profit = (discharge revenue + pv savings) - charge cost
    profit = result.projected_profit_eur + result.pv_savings_eur
    # Total cost with battery = naive_cost - savings from battery
    battery_savings = result.discharge_revenue_eur + result.pv_savings_eur - result.charge_cost_eur
    savings_vs_naive = battery_savings

    return DayResult(
        date=date_str,
        strategy=strategy,
        profit_eur=round(result.projected_profit_eur, 4),
        charge_cost_eur=round(result.charge_cost_eur, 4),
        discharge_revenue_eur=round(result.discharge_revenue_eur, 4),
        pv_savings_eur=round(result.pv_savings_eur, 4),
        naive_cost_eur=round(naive_cost, 4),
        savings_vs_naive_eur=round(savings_vs_naive, 4),
        cycles=result.cycles,
    )


def split_into_days(slots: list[HourSlot], nl_offset_hours: int = 2) -> list[list[HourSlot]]:
    """Split slots into per-day groups (local time days)."""
    days: dict[str, list[HourSlot]] = {}
    for s in slots:
        local = s.hour_utc + timedelta(hours=nl_offset_hours)
        key = local.strftime("%Y-%m-%d")
        days.setdefault(key, []).append(s)
    return [v for v in days.values() if len(v) >= 12]  # skip incomplete days


def run_full_simulation(
    slots: list[HourSlot],
    config: ArbitrageConfig,
    strategies: list[str] | None = None,
) -> list[SimulationResult]:
    """Run multi-day simulation for all strategies."""
    if strategies is None:
        strategies = ["naive", "selfuse", "saldering", "export"]

    day_groups = split_into_days(slots)
    if not day_groups:
        _LOG.warning("No complete days in data (%d slots total)", len(slots))
        return []

    results = []
    for strategy in strategies:
        sim = SimulationResult(
            strategy=strategy,
            config={
                "capacity_kwh": config.capacity_kwh,
                "max_power_kw": config.max_power_kw,
                "efficiency": config.efficiency,
                "min_soc_pct": config.min_soc_pct,
                "min_spread_eur": config.min_spread_eur,
                "max_cycles_per_day": config.max_cycles_per_day,
            },
        )
        for day_slots in day_groups:
            day_result = run_day_simulation(day_slots, config, strategy)
            sim.days.append(day_result)
            sim.total_profit_eur += day_result.profit_eur
            sim.total_naive_cost_eur += day_result.naive_cost_eur
            sim.total_savings_eur += day_result.savings_vs_naive_eur
            sim.total_cycles += day_result.cycles

        n = len(sim.days)
        sim.avg_daily_profit_eur = round(sim.total_profit_eur / n, 4) if n else 0
        sim.total_profit_eur = round(sim.total_profit_eur, 2)
        sim.total_naive_cost_eur = round(sim.total_naive_cost_eur, 2)
        sim.total_savings_eur = round(sim.total_savings_eur, 2)
        results.append(sim)

    return results


# ---------------------------------------------------------------------------
# Parameter sweep
# ---------------------------------------------------------------------------

def parameter_sweep(
    slots: list[HourSlot],
    strategy: str = "saldering",
    param_grid: dict[str, list] | None = None,
) -> list[SweepResult]:
    """Grid search over ArbitrageConfig parameters.

    Default grid sweeps over the most impactful parameters:
      - min_soc_pct: overnight reserve floor
      - min_spread_eur: minimum profitable spread
      - max_cycles_per_day: battery wear limit
      - ac_charge_kw: grid charge power limit
      - ac_discharge_kw: self-use discharge power limit
      - pv_charge_kw: PV charge power limit
      - charge_soc_target_pct: charge ceiling
      - pv_surplus_threshold_w: PV surplus trigger

    Pass a custom param_grid to focus on specific parameters, e.g.:
        parameter_sweep(slots, param_grid={"ac_charge_kw": [5, 10, 15]})
    """
    if param_grid is None:
        param_grid = {
            "min_soc_pct": [10.0, 20.0, 30.0],
            "min_spread_eur": [0.01, 0.02, 0.05],
            "max_cycles_per_day": [1, 2, 3],
            "ac_charge_kw": [5.0, 10.0, 15.0],
            "ac_discharge_kw": [5.0, 10.0, 15.0],
        }

    base_config = ArbitrageConfig()
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    total_combos = 1
    for v in values:
        total_combos *= len(v)
    _LOG.info("Parameter sweep: %d combinaties over %s", total_combos, keys)

    results: list[SweepResult] = []
    for combo in product(*values):
        params = dict(zip(keys, combo))
        cfg = ArbitrageConfig(
            capacity_kwh=base_config.capacity_kwh,
            max_power_kw=base_config.max_power_kw,
            efficiency=params.get("efficiency", base_config.efficiency),
            min_soc_pct=params.get("min_soc_pct", base_config.min_soc_pct),
            min_spread_eur=params.get("min_spread_eur", base_config.min_spread_eur),
            night_start_hour=params.get("night_start_hour", base_config.night_start_hour),
            night_end_hour=params.get("night_end_hour", base_config.night_end_hour),
            max_cycles_per_day=params.get("max_cycles_per_day", base_config.max_cycles_per_day),
            ac_charge_kw=params.get("ac_charge_kw", base_config.ac_charge_kw),
            pv_charge_kw=params.get("pv_charge_kw", base_config.pv_charge_kw),
            ac_discharge_kw=params.get("ac_discharge_kw", base_config.ac_discharge_kw),
            export_discharge_kw=params.get("export_discharge_kw", base_config.export_discharge_kw),
            pv_surplus_threshold_w=params.get("pv_surplus_threshold_w", base_config.pv_surplus_threshold_w),
            charge_soc_target_pct=params.get("charge_soc_target_pct", base_config.charge_soc_target_pct),
            grid_export_enabled=(strategy == "export"),
        )

        sim_results = run_full_simulation(slots, cfg, [strategy])
        if sim_results:
            r = sim_results[0]
            results.append(SweepResult(
                params=params,
                profit_eur=r.total_profit_eur,
                savings_eur=r.total_savings_eur,
                cycles=r.total_cycles,
            ))

    # Sort by savings descending (savings = money saved vs naive)
    results.sort(key=lambda r: r.savings_eur, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Planned load scheduler — find optimal start times for appliances
# ---------------------------------------------------------------------------

# Common NL household appliance profiles (average watts, duration hours)
APPLIANCE_PROFILES: dict[str, tuple[float, float]] = {
    "wasmachine":    (2000, 2.5),   # 2000W avg, 2.5h cycle = 5.0 kWh
    "droger":        (3000, 2.0),   # 3000W avg, 2.0h cycle = 6.0 kWh
    "vaatwasser":    (1800, 2.5),   # 1800W avg, 2.5h cycle = 4.5 kWh
    "oven":          (2500, 1.5),   # 2500W avg, 1.5h cycle = 3.75 kWh
    "ev_laden":      (7400, 4.0),   # 7.4kW (32A 1-fase), 4h = 29.6 kWh
    "warmtepomp":    (1500, 3.0),   # 1500W avg, 3h cycle = 4.5 kWh
    "airco":         (1200, 2.0),   # 1200W avg, 2h = 2.4 kWh
    "boiler":        (2000, 1.0),   # 2000W, 1h = 2.0 kWh
}


@dataclass
class PlannedLoad:
    """A flexible load that can be scheduled at the optimal time."""
    name: str
    avg_watts: float
    duration_hours: float
    # Optional constraints
    earliest_hour: int = 0      # local hour — don't start before this
    latest_hour: int = 24       # local hour — must finish before this
    allow_overnight: bool = True

    @property
    def kwh(self) -> float:
        return self.avg_watts * self.duration_hours / 1000.0

    @classmethod
    def from_profile(cls, name: str, **overrides) -> "PlannedLoad":
        """Create from a known appliance profile."""
        key = name.lower().replace(" ", "_")
        if key in APPLIANCE_PROFILES:
            watts, hours = APPLIANCE_PROFILES[key]
            return cls(name=name, avg_watts=watts, duration_hours=hours, **overrides)
        raise ValueError(f"Onbekend apparaat '{name}'. Keuze: {', '.join(APPLIANCE_PROFILES)}")


@dataclass
class ScheduleResult:
    """Optimal schedule for one appliance."""
    name: str
    best_start_hour: int        # local hour
    best_start_utc: str         # ISO timestamp
    end_hour: int               # local hour
    duration_hours: float
    kwh: float
    cost_eur: float             # cost at optimal time
    worst_cost_eur: float       # cost at most expensive time
    savings_eur: float          # savings vs worst time
    avg_price_eur: float        # average price during run
    pv_coverage_pct: float      # % of load covered by PV


def schedule_load(
    load: PlannedLoad,
    slots: list[HourSlot],
    nl_offset_hours: int = 2,
) -> ScheduleResult | None:
    """Find the cheapest contiguous window to run an appliance.

    Only considers FUTURE hours (slots with hour_utc > now).

    Considers:
      - Electricity spot price per hour
      - PV production (free energy reduces effective cost)
      - Duration constraint (must fit in contiguous hours)
      - Time window constraints (earliest/latest hour)

    The effective cost per hour = max(0, load_watts - pv_surplus) × price / 1000
    PV surplus that exceeds load is "free" — reduces the cost of running.
    """
    if not slots:
        return None

    # Filter to future slots only
    now_utc = datetime.now(timezone.utc)
    future_slots = [s for s in slots if s.hour_utc >= now_utc.replace(minute=0, second=0, microsecond=0)]
    if not future_slots:
        future_slots = slots  # fallback if all slots are "past" (synthetic data)

    dur_slots = max(1, round(load.duration_hours))  # round to whole hours
    if len(future_slots) < dur_slots:
        return None

    best_cost = float("inf")
    worst_cost = float("-inf")
    best_start_idx = 0

    for i in range(len(future_slots) - dur_slots + 1):
        window = future_slots[i:i + dur_slots]

        # Check time constraints (local hours)
        local_start = (window[0].hour_utc + timedelta(hours=nl_offset_hours)).hour
        local_end = (window[-1].hour_utc + timedelta(hours=nl_offset_hours)).hour + 1
        if local_end > 24:
            local_end -= 24

        if load.earliest_hour <= load.latest_hour:
            # Normal range (e.g., 6-22)
            if local_start < load.earliest_hour:
                continue
            if local_end > load.latest_hour and not load.allow_overnight:
                continue
        else:
            # Overnight range (e.g., 22-6) — skip for now
            pass

        # Calculate effective cost: load minus PV surplus = net grid import
        window_cost = 0.0
        for s in window:
            # PV surplus available (after baseline home consumption)
            pv_surplus_w = max(0, s.pv_watts - s.consumption_watts)
            # Net power from grid needed for this appliance
            net_grid_w = max(0, load.avg_watts - pv_surplus_w)
            # Cost for this hour (fractional if duration is not whole hours)
            window_cost += net_grid_w * s.price_eur_kwh / 1000.0

        # Adjust for fractional hours
        fraction = load.duration_hours / dur_slots
        window_cost *= fraction

        if window_cost < best_cost:
            best_cost = window_cost
            best_start_idx = i

        if window_cost > worst_cost:
            worst_cost = window_cost

    # Build result
    best_window = future_slots[best_start_idx:best_start_idx + dur_slots]
    local_start = (best_window[0].hour_utc + timedelta(hours=nl_offset_hours)).hour
    local_end = local_start + dur_slots
    if local_end >= 24:
        local_end -= 24

    # PV coverage
    total_pv_cover = 0.0
    total_load = load.avg_watts * load.duration_hours  # Wh
    for s in best_window:
        pv_surplus_w = max(0, s.pv_watts - s.consumption_watts)
        covered = min(load.avg_watts, pv_surplus_w)
        total_pv_cover += covered  # Wh per hour
    pv_pct = (total_pv_cover / total_load * 100) if total_load > 0 else 0

    avg_price = sum(s.price_eur_kwh for s in best_window) / len(best_window)

    return ScheduleResult(
        name=load.name,
        best_start_hour=local_start,
        best_start_utc=best_window[0].hour_utc.isoformat(),
        end_hour=local_end,
        duration_hours=load.duration_hours,
        kwh=round(load.kwh, 1),
        cost_eur=round(best_cost, 2),
        worst_cost_eur=round(worst_cost, 2),
        savings_eur=round(worst_cost - best_cost, 2),
        avg_price_eur=round(avg_price, 4),
        pv_coverage_pct=round(pv_pct, 0),
    )


def schedule_multiple_loads(
    loads: list[PlannedLoad],
    slots: list[HourSlot],
    nl_offset_hours: int = 2,
) -> list[ScheduleResult]:
    """Schedule multiple appliances, avoiding overlap where possible.

    Greedy approach: schedule highest-kWh loads first (they benefit most
    from cheap hours), then remaining loads avoid already-claimed hours.
    """
    # Sort by kWh descending (biggest loads get priority for cheapest slots)
    sorted_loads = sorted(loads, key=lambda l: l.kwh, reverse=True)
    results: list[ScheduleResult] = []
    claimed_hours: set[int] = set()  # indices into slots that are "taken"

    for load in sorted_loads:
        # Filter out claimed hours by increasing their effective price
        adjusted_slots = []
        for i, s in enumerate(slots):
            if i in claimed_hours:
                # Penalize already-claimed hours (another appliance runs here)
                # Add the load's power to consumption so PV surplus shrinks
                adjusted = HourSlot(
                    hour_utc=s.hour_utc,
                    price_eur_kwh=s.price_eur_kwh,
                    pv_watts=s.pv_watts,
                    consumption_watts=s.consumption_watts + 2000,  # penalty
                )
                adjusted_slots.append(adjusted)
            else:
                adjusted_slots.append(s)

        result = schedule_load(load, adjusted_slots, nl_offset_hours)
        if result:
            results.append(result)
            # Claim the hours
            dur = max(1, round(load.duration_hours))
            start_idx = next(
                (i for i, s in enumerate(slots) if s.hour_utc.isoformat() == result.best_start_utc),
                None,
            )
            if start_idx is not None:
                for j in range(dur):
                    claimed_hours.add(start_idx + j)

    # Sort results by start hour for display
    results.sort(key=lambda r: r.best_start_hour)
    return results


def format_schedule_table(results: list[ScheduleResult]) -> str:
    """Format schedule results as a console table."""
    if not results:
        return "  Geen apparaten gepland."

    lines = ["\n  OPTIMAAL SCHEMA — gepland verbruik", ""]
    hdr = f"  {'Apparaat':<16} {'Start':>6} {'Eind':>6} {'kWh':>6} {'Kosten €':>9} {'Besparing €':>12} {'PV %':>5}"
    lines.append(hdr)
    lines.append("  " + "-" * (len(hdr) - 2))

    total_cost = 0.0
    total_savings = 0.0
    for r in results:
        lines.append(
            f"  {r.name:<16} {r.best_start_hour:>5}:00 {r.end_hour:>5}:00 "
            f"{r.kwh:>6.1f} {r.cost_eur:>9.2f} {r.savings_eur:>12.2f} {r.pv_coverage_pct:>4.0f}%"
        )
        total_cost += r.cost_eur
        total_savings += r.savings_eur

    lines.append("  " + "-" * (len(hdr) - 2))
    lines.append(
        f"  {'TOTAAL':<16} {'':>6} {'':>6} "
        f"{'':>6} {total_cost:>9.2f} {total_savings:>12.2f}"
    )
    lines.append("")

    # Advice per appliance
    lines.append("  ADVIES:")
    for r in results:
        lines.append(
            f"  → {r.name}: start om {r.best_start_hour:02d}:00 "
            f"(gem. €{r.avg_price_eur:.3f}/kWh, {r.pv_coverage_pct:.0f}% PV-dekking, "
            f"€{r.savings_eur:.2f} goedkoper dan duurste moment)"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_comparison_table(results: list[SimulationResult]) -> str:
    """Format strategy comparison as a console table."""
    lines = []
    n_days = len(results[0].days) if results else 0
    lines.append(f"\n{'='*78}")
    lines.append(f"  ARBITRAGE SIMULATOR — {n_days} dagen backtested")
    lines.append(f"{'='*78}")
    lines.append("")

    # Header
    hdr = f"{'Strategie':<12} {'Winst €':>10} {'Besparing €':>12} {'Naive kost €':>13} {'Cycli':>6} {'€/dag':>8}"
    lines.append(hdr)
    lines.append("-" * len(hdr))

    for r in results:
        lines.append(
            f"{r.strategy:<12} {r.total_profit_eur:>10.2f} {r.total_savings_eur:>12.2f} "
            f"{r.total_naive_cost_eur:>13.2f} {r.total_cycles:>6} {r.avg_daily_profit_eur:>8.2f}"
        )

    lines.append("")

    # Best strategy
    best = max(results, key=lambda r: r.total_savings_eur)
    lines.append(f"  Beste strategie: {best.strategy} (€{best.total_savings_eur:.2f} bespaard over {n_days} dagen)")

    if n_days > 0:
        annual = best.total_savings_eur / n_days * 365
        lines.append(f"  Geschatte jaarbesparing: €{annual:.0f}")

    lines.append("")
    return "\n".join(lines)


def format_daily_breakdown(results: list[SimulationResult], strategy: str | None = None) -> str:
    """Format day-by-day breakdown for one strategy."""
    if strategy is None:
        strategy = max(results, key=lambda r: r.total_savings_eur).strategy

    sim = next((r for r in results if r.strategy == strategy), None)
    if not sim:
        return f"Strategie '{strategy}' niet gevonden."

    lines = [f"\n  Dagelijkse breakdown — {strategy}:", ""]
    hdr = f"  {'Datum':<12} {'Winst €':>9} {'Laden €':>9} {'Ontladen €':>10} {'PV €':>8} {'Naive €':>9} {'Besp. €':>9} {'Cyc':>4}"
    lines.append(hdr)
    lines.append("  " + "-" * (len(hdr) - 2))

    for d in sim.days:
        lines.append(
            f"  {d.date:<12} {d.profit_eur:>9.2f} {d.charge_cost_eur:>9.2f} "
            f"{d.discharge_revenue_eur:>10.2f} {d.pv_savings_eur:>8.2f} "
            f"{d.naive_cost_eur:>9.2f} {d.savings_vs_naive_eur:>9.2f} {d.cycles:>4}"
        )

    lines.append("")
    return "\n".join(lines)


def format_sweep_table(sweep: list[SweepResult], top_n: int = 10) -> str:
    """Format parameter sweep results as a table."""
    lines = [f"\n  Top {top_n} parameter combinaties (gesorteerd op winst):", ""]

    # Collect all param keys
    if not sweep:
        return "  Geen sweep resultaten."
    keys = list(sweep[0].params.keys())
    hdr_parts = [f"{k:>18}" for k in keys]
    hdr = "  " + " ".join(hdr_parts) + f" {'Winst €':>10} {'Besp. €':>10} {'Cycli':>6}"
    lines.append(hdr)
    lines.append("  " + "-" * (len(hdr) - 2))

    for r in sweep[:top_n]:
        val_parts = [f"{r.params[k]:>18}" for k in keys]
        lines.append(
            "  " + " ".join(val_parts)
            + f" {r.profit_eur:>10.2f} {r.savings_eur:>10.2f} {r.cycles:>6}"
        )

    if len(sweep) > top_n:
        lines.append(f"  ... en {len(sweep) - top_n} meer combinaties")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def main_async(args: argparse.Namespace) -> None:
    """Main async entry point."""
    slots: list[HourSlot] = []

    if args.api_url and args.api_token:
        # Fetch real prices from API
        to_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        from_utc = to_utc - timedelta(days=args.days)
        print(f"Fetching {args.days} days of prices from {args.api_url} ...")
        raw = await fetch_prices_from_api(args.api_url, args.api_token, from_utc, to_utc)
        if raw:
            slots = parse_api_prices(raw)
            print(f"  → {len(slots)} hourly prices loaded")
        else:
            print("  → Geen prijsdata ontvangen, gebruik synthetische data")

    if not slots:
        # Generate synthetic data for demo/testing
        print(f"Generating {args.days} days of synthetic data ...")
        slots = generate_synthetic_dataset(args.days)
        print(f"  → {len(slots)} hourly slots generated")

    # Enrich with PV and consumption profiles
    slots = enrich_slots_with_profiles(
        slots,
        pv_peak_kw=args.pv_peak_kw,
        base_consumption_w=args.base_consumption_w,
    )

    config = ArbitrageConfig(
        capacity_kwh=args.capacity_kwh,
        max_power_kw=args.max_power_kw,
        ac_charge_kw=args.ac_charge_kw,
        pv_charge_kw=args.pv_charge_kw,
        ac_discharge_kw=args.ac_discharge_kw,
        export_discharge_kw=args.export_discharge_kw,
        efficiency=args.efficiency,
        pv_surplus_threshold_w=args.pv_surplus_threshold_w,
        charge_soc_target_pct=args.charge_soc_target_pct,
        min_soc_pct=args.min_soc_pct,
        min_spread_eur=args.min_spread_eur,
        max_cycles_per_day=args.max_cycles_per_day,
    )

    # Run simulation
    print("\nSimulating strategies ...")
    results = run_full_simulation(slots, config)
    print(format_comparison_table(results))

    # Daily breakdown for best strategy
    print(format_daily_breakdown(results))

    # Parameter sweep
    if args.sweep:
        print("Running parameter sweep (this may take a moment) ...")
        sweep = parameter_sweep(slots, strategy="saldering")
        print(format_sweep_table(sweep))

        # Also show best config
        if sweep:
            best = sweep[0]
            print(f"  Optimale parameters: {best.params}")
            print(f"  Winst: €{best.profit_eur:.2f}, besparing: €{best.savings_eur:.2f}, cycli: {best.cycles}")
            print()


def generate_synthetic_dataset(days: int = 7) -> list[HourSlot]:
    """Generate synthetic EPEX-like price data for testing.

    Uses a realistic NL day-ahead price pattern:
      - Cheap at night (02:00-06:00): ~€0.05-0.10/kWh
      - Morning peak (07:00-09:00): ~€0.15-0.25/kWh
      - Midday dip (11:00-14:00): ~€0.08-0.12/kWh (solar surplus)
      - Evening peak (17:00-21:00): ~€0.20-0.35/kWh
    """
    import math
    import random

    random.seed(42)  # reproducible
    base_date = datetime(2026, 7, 1, tzinfo=timezone.utc)
    slots = []

    # Base price curve (local hour → EUR/kWh)
    base_prices = {
        0: 0.08, 1: 0.06, 2: 0.05, 3: 0.04, 4: 0.05, 5: 0.06,
        6: 0.10, 7: 0.18, 8: 0.22, 9: 0.20, 10: 0.15, 11: 0.10,
        12: 0.08, 13: 0.07, 14: 0.09, 15: 0.12, 16: 0.16, 17: 0.25,
        18: 0.30, 19: 0.28, 20: 0.22, 21: 0.15, 22: 0.12, 23: 0.10,
    }

    for day in range(days):
        # Daily variation factor (±20%)
        day_factor = 1.0 + 0.2 * math.sin(day * 0.7)
        for hour_local in range(24):
            hour_utc = hour_local - 2  # CEST offset
            dt = base_date + timedelta(days=day, hours=hour_utc)
            price = base_prices[hour_local] * day_factor
            # Add noise (±15%)
            price *= (1.0 + random.uniform(-0.15, 0.15))
            # Occasional negative prices (midday solar surplus)
            if hour_local in (12, 13, 14) and random.random() < 0.1:
                price = -random.uniform(0.01, 0.05)
            slots.append(HourSlot(hour_utc=dt, price_eur_kwh=round(price, 4)))

    return slots


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Saldox Arbitrage Simulator — backtest battery strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--days", type=int, default=7, help="Number of days to simulate (default: 7)")
    parser.add_argument("--api-url", type=str, default="", help="Saldox API URL for live prices")
    parser.add_argument("--api-token", type=str, default="", help="Saldox API bearer token")
    parser.add_argument("--sweep", action="store_true", help="Run parameter optimization sweep")

    # Battery hardware
    parser.add_argument("--capacity-kwh", type=float, default=30.0, help="Battery capacity (kWh)")
    parser.add_argument("--max-power-kw", type=float, default=15.0, help="Inverter max power (kW)")

    # Per-mode power limits (0 = use max-power-kw)
    parser.add_argument("--ac-charge-kw", type=float, default=0, help="Grid→battery charge limit (kW)")
    parser.add_argument("--pv-charge-kw", type=float, default=0, help="PV→battery charge limit (kW)")
    parser.add_argument("--ac-discharge-kw", type=float, default=0, help="Battery→home discharge limit (kW)")
    parser.add_argument("--export-discharge-kw", type=float, default=0, help="Battery→grid export limit (kW)")

    # Thresholds
    parser.add_argument("--efficiency", type=float, default=0.90, help="Roundtrip efficiency (0-1)")
    parser.add_argument("--pv-surplus-threshold-w", type=float, default=100.0, help="Min PV surplus to trigger charge (W)")
    parser.add_argument("--charge-soc-target-pct", type=float, default=100.0, help="Stop grid-charge at this SoC (%%)")
    parser.add_argument("--min-soc-pct", type=float, default=20.0, help="Min SoC reserve (%%)")
    parser.add_argument("--min-spread-eur", type=float, default=0.02, help="Min spread (EUR/kWh)")
    parser.add_argument("--max-cycles-per-day", type=int, default=2, help="Max cycles per day")

    # Profile config
    parser.add_argument("--pv-peak-kw", type=float, default=10.0, help="PV peak power (kW)")
    parser.add_argument("--base-consumption-w", type=float, default=800.0, help="Base home consumption (W)")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
