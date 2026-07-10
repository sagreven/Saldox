"""Saldox Battery Arbitrage Optimizer.

Analyses the 48-hour EPEX price curve and generates an optimal
charge/discharge schedule to maximize profit from price spreads.

Algorithm: two-pass greedy with forward SoC simulation.
  Pass 1 — Mark PV surplus hours as free charge (SolarCharge).
  Pass 2 — Sort remaining hours by price: cheapest → charge pool,
           most expensive → discharge pool. Filter by minimum spread.
  Pass 3 — Forward chronological SoC simulation: emit actions while
           respecting capacity, power limits, efficiency, and overnight
           reserve constraints.

No external dependencies — pure Python, runs in microseconds on 48 slots.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

_LOG = logging.getLogger(__name__)


@dataclass
class ArbitrageConfig:
    """Tunable parameters for the optimizer.

    Hardware limits (fixed by inverter/battery):
        capacity_kwh, max_power_kw

    Fine-tune parameters (optimizable):
        ac_charge_kw      — max grid (AC) → battery charge rate
        pv_charge_kw      — max PV (DC) → battery charge rate
        ac_discharge_kw   — max battery → home (self-use) discharge rate
        export_discharge_kw — max battery → grid export discharge rate
        pv_surplus_threshold_w — minimum PV surplus (W) to trigger solar charge
        charge_soc_target_pct  — stop grid-charging at this SoC (%)
        min_soc_pct       — overnight reserve floor (%)
        min_spread_eur    — minimum profitable price spread
        night_start_hour  — start of overnight reserve window (local hour)
        night_end_hour    — end of overnight reserve window (local hour)
        max_cycles_per_day — battery wear limit
    """
    # --- Hardware limits ---
    capacity_kwh: float = 30.0
    max_power_kw: float = 15.0        # overall inverter limit (fallback)

    # --- Power limits per mode ---
    ac_charge_kw: float = 0.0         # grid → battery (0 = use max_power_kw)
    pv_charge_kw: float = 0.0         # PV → battery  (0 = use max_power_kw)
    ac_discharge_kw: float = 0.0      # battery → home self-use (0 = use max_power_kw)
    export_discharge_kw: float = 0.0  # battery → grid export (0 = use max_power_kw)

    # --- Efficiency ---
    efficiency: float = 0.90          # roundtrip (charge × discharge)

    # --- Thresholds ---
    pv_surplus_threshold_w: float = 100.0   # min PV surplus (W) to trigger SolarCharge
    charge_soc_target_pct: float = 100.0    # stop grid-charge at this SoC %

    # --- Reserve & timing ---
    min_soc_pct: float = 20.0         # overnight reserve (% of capacity)
    min_spread_eur: float = 0.02      # minimum profitable spread per kWh
    night_start_hour: int = 22        # local hour — start of overnight reserve window
    night_end_hour: int = 6           # local hour — end of overnight reserve window
    max_cycles_per_day: int = 2       # limit battery wear
    grid_export_enabled: bool = False # False = NL saldering strategie

    # --- Resolved limits (use these in code) ---
    @property
    def eff_ac_charge_kw(self) -> float:
        return self.ac_charge_kw if self.ac_charge_kw > 0 else self.max_power_kw

    @property
    def eff_pv_charge_kw(self) -> float:
        return self.pv_charge_kw if self.pv_charge_kw > 0 else self.max_power_kw

    @property
    def eff_ac_discharge_kw(self) -> float:
        return self.ac_discharge_kw if self.ac_discharge_kw > 0 else self.max_power_kw

    @property
    def eff_export_discharge_kw(self) -> float:
        return self.export_discharge_kw if self.export_discharge_kw > 0 else self.max_power_kw

    @property
    def charge_soc_limit_kwh(self) -> float:
        return self.capacity_kwh * self.charge_soc_target_pct / 100.0


@dataclass
class ArbitrageResult:
    """Output of the optimizer."""
    actions: list[dict] = field(default_factory=list)
    soc_curve: list[dict] = field(default_factory=list)
    projected_profit_eur: float = 0.0
    charge_cost_eur: float = 0.0
    discharge_revenue_eur: float = 0.0
    pv_savings_eur: float = 0.0
    cycles: int = 0
    summary: str = ""


class ArbitrageOptimizer:
    """Optimizes battery charge/discharge schedule for EPEX price arbitrage."""

    def __init__(self, config: ArbitrageConfig | None = None):
        self._cfg = config or ArbitrageConfig()

    def optimize(self, timeline: list[dict], current_soc_kwh: float) -> ArbitrageResult:
        """Run the optimizer over the plan timeline.

        Args:
            timeline: List of hourly slot dicts from the EMS plan.
                      Each has startUtc, endUtc, priceEurKwh, pvWatts, consumptionWatts.
            current_soc_kwh: Actual battery state of charge in kWh right now.

        Returns:
            ArbitrageResult with optimized actions and projected profit.
        """
        cfg = self._cfg
        if not timeline or len(timeline) < 2:
            return ArbitrageResult(summary="Onvoldoende data")

        # --- Parse timeline into slot structs ---
        slots = []
        for i, s in enumerate(timeline):
            try:
                start = s.get("startUtc", "")
                end = s.get("endUtc", "")
                price = float(s.get("priceEurKwh", 0))
                pv = float(s.get("pvWatts", 0) or 0)
                cons = float(s.get("consumptionWatts", 0) or 0)
            except (ValueError, TypeError):
                continue
            slots.append({
                "idx": i,
                "start": start,
                "end": end,
                "price": price,
                "pv_w": pv,
                "cons_w": cons,
                "net_w": pv - cons,  # positive = surplus
                "hour_local": self._local_hour(start),
                "action": None,
                "charge_kwh": 0.0,
                "discharge_kwh": 0.0,
            })

        if not slots:
            return ArbitrageResult(summary="Geen geldige slots")

        # --- Pass 1: PV surplus detection ---
        for s in slots:
            if s["net_w"] > cfg.pv_surplus_threshold_w:
                s["free_charge_kwh"] = min(s["net_w"] / 1000.0, cfg.eff_pv_charge_kw)
            else:
                s["free_charge_kwh"] = 0.0

        # --- Pass 2: Dynamic break-even price arbitrage ---
        # For each hour, determine if it's profitable to discharge (sell/self-use)
        # or charge (buy) based on the cheapest future recharge opportunity.
        #
        # Break-even logic: discharge at price P is profitable if
        #   P > cheapest_future_price / efficiency + min_spread
        # This maximizes the number of profitable discharge hours instead of
        # limiting to a fixed count around the median.

        all_prices = sorted(s["price"] for s in slots)
        cheapest = all_prices[0]
        most_expensive = all_prices[-1]
        overall_spread = most_expensive * cfg.efficiency - cheapest
        if overall_spread < cfg.min_spread_eur:
            return ArbitrageResult(
                summary=f"Spread te klein ({overall_spread:.3f} €/kWh < {cfg.min_spread_eur})"
            )

        # For each slot, compute the cheapest price in the FUTURE (remaining slots).
        # This lets us decide: "can I recharge cheaper later?"
        n_slots = len(slots)
        cheapest_future = [0.0] * n_slots
        min_so_far = slots[-1]["price"]
        cheapest_future[-1] = min_so_far
        for i in range(n_slots - 2, -1, -1):
            min_so_far = min(min_so_far, slots[i + 1]["price"])
            cheapest_future[i] = min_so_far

        # Break-even price: below this, discharging is not profitable
        # (because you could recharge cheaper in the future)
        charge_target = cfg.charge_soc_limit_kwh
        charge_set: set[int] = set()
        discharge_set: set[int] = set()

        for i, s in enumerate(slots):
            break_even = cheapest_future[i] / cfg.efficiency + cfg.min_spread_eur
            if s["price"] >= break_even:
                discharge_set.add(s["idx"])
            elif s["price"] <= cheapest_future[i] + cfg.min_spread_eur * 0.5:
                # Charge when price is near the cheapest available
                charge_set.add(s["idx"])

        # --- Pass 3: Forward SoC simulation ---
        soc = current_soc_kwh
        min_soc = cfg.capacity_kwh * cfg.min_soc_pct / 100.0
        charge_target = cfg.charge_soc_limit_kwh
        actions = []
        soc_curve = []
        charge_cost = 0.0
        discharge_revenue = 0.0
        pv_savings = 0.0
        total_charged = 0.0
        total_discharged = 0.0

        for s in slots:
            hour = s["hour_local"]
            is_night = self._is_night_hour(hour, cfg)
            start_utc = s["start"]
            end_utc = s["end"]
            price = s["price"]

            soc_curve.append({
                "timestampUtc": start_utc,
                "soCKwh": round(soc, 2),
                "capacityKwh": cfg.capacity_kwh,
            })

            if cfg.grid_export_enabled:
                # ===== EXPORT STRATEGIE =====

                # 1. PV surplus → SolarCharge (skip als export-slot)
                free_kwh = min(s["free_charge_kwh"], charge_target - soc)
                if free_kwh > 0.1 and s["idx"] not in discharge_set:
                    soc += free_kwh
                    pv_savings += free_kwh * price
                    actions.append(self._make_action(
                        "SolarCharge", start_utc, end_utc, free_kwh,
                        free_kwh * price,
                        f"PV-overschot {free_kwh:.1f} kWh opslaan (€{price:.3f}/kWh vermeden)"
                    ))

                # 2. Grid charge in cheap hours (AC charge)
                if s["idx"] in charge_set and soc < charge_target - 0.5:
                    room = charge_target - soc
                    charge_kwh = min(room, cfg.eff_ac_charge_kw)
                    if charge_kwh > 0.5:
                        soc += charge_kwh
                        charge_cost += charge_kwh * price
                        total_charged += charge_kwh
                        est_profit = charge_kwh * (most_expensive * cfg.efficiency - price)
                        actions.append(self._make_action(
                            "ChargeBattery", start_utc, end_utc, charge_kwh,
                            max(0, est_profit),
                            f"AC laden @ €{price:.3f}/kWh → export @ €{most_expensive:.3f}/kWh"
                        ))

                # 3. Export to grid in expensive hours
                elif s["idx"] in discharge_set and not is_night:
                    hours_to_night = self._hours_until_night(hour, cfg)
                    effective_min = min_soc if hours_to_night <= 3 else 0.5
                    available = soc - effective_min
                    discharge_kwh = min(available, cfg.eff_export_discharge_kw)
                    if discharge_kwh > 0.5:
                        soc -= discharge_kwh
                        revenue = discharge_kwh * price * cfg.efficiency
                        discharge_revenue += revenue
                        total_discharged += discharge_kwh
                        actions.append(self._make_action(
                            "ExportToGrid", start_utc, end_utc, discharge_kwh,
                            revenue,
                            f"Export {discharge_kwh:.1f} kWh @ €{price:.3f}/kWh "
                            f"(€{revenue:.2f} na {cfg.efficiency:.0%} eff)"
                        ))

                # 4. Default: Self Use (AC discharge)
                else:
                    deficit_kwh = max(0, s["cons_w"] - s["pv_w"]) / 1000.0
                    if deficit_kwh > 0 and soc > min_soc:
                        drain = min(deficit_kwh, soc - min_soc, cfg.eff_ac_discharge_kw)
                        soc -= drain
                        pv_savings += drain * price

            else:
                # ===== SALDERING STRATEGIE (geen grid export) =====
                # Key insight: when price is HIGH and there's PV surplus,
                # let PV go to grid for saldering instead of charging battery.
                # Recharge battery from grid later when price is LOW.

                has_pv_surplus = s["free_charge_kwh"] > 0.1
                break_even_i = cheapest_future[s["idx"]] / cfg.efficiency + cfg.min_spread_eur
                price_is_high = s["idx"] in discharge_set  # price > break-even

                # 1. Grid charge in cheapest hours (AC charge, tot charge target)
                if s["idx"] in charge_set and soc < charge_target - 0.5:
                    room = charge_target - soc
                    charge_kwh = min(room, cfg.eff_ac_charge_kw)
                    if charge_kwh > 0.5:
                        soc += charge_kwh
                        charge_cost += charge_kwh * price
                        total_charged += charge_kwh
                        actions.append(self._make_action(
                            "ChargeBattery", start_utc, end_utc, charge_kwh,
                            charge_kwh * (most_expensive - price),
                            f"AC laden @ €{price:.3f}/kWh — batterij vol → PV saldering"
                        ))

                # 2. High price + PV surplus → saldering (PV naar grid, battery stays)
                #    Don't charge battery from PV when selling to grid is more profitable.
                elif has_pv_surplus and price_is_high:
                    surplus = s["free_charge_kwh"]
                    pv_savings += surplus * price  # saldering credit
                    # Also discharge battery for home deficit if any
                    deficit_kwh = max(0, s["cons_w"] - s["pv_w"]) / 1000.0
                    drain = 0.0
                    if deficit_kwh > 0.1 and soc > min_soc:
                        drain = min(deficit_kwh, soc - min_soc, cfg.eff_ac_discharge_kw)
                        soc -= drain
                        total_discharged += drain
                        discharge_revenue += drain * price
                    actions.append(self._make_action(
                        "DischargeBattery", start_utc, end_utc, drain,
                        surplus * price + drain * price,
                        f"PV {surplus:.1f} kWh → grid (saldering @ €{price:.3f}/kWh)"
                        + (f" + Self Use {drain:.1f} kWh" if drain > 0.1 else "")
                    ))

                # 3. Battery full + PV surplus → saldering (any price)
                elif has_pv_surplus and soc >= charge_target - 1.0:
                    surplus = s["free_charge_kwh"]
                    pv_savings += surplus * price
                    actions.append(self._make_action(
                        "DischargeBattery", start_utc, end_utc, 0,
                        surplus * price,
                        f"Batterij vol → {surplus:.1f} kWh PV naar grid (saldering @ €{price:.3f}/kWh)"
                    ))

                # 4. Low price + PV surplus + battery not full → PV charge
                elif has_pv_surplus:
                    free_kwh = min(s["free_charge_kwh"], charge_target - soc)
                    if free_kwh > 0.1:
                        soc += free_kwh
                        pv_savings += free_kwh * price
                        actions.append(self._make_action(
                            "SolarCharge", start_utc, end_utc, free_kwh,
                            free_kwh * price,
                            f"PV-laden {free_kwh:.1f} kWh (€{price:.3f}/kWh — goedkoop, batterij opslaan)"
                        ))

                # 5. No PV surplus + discharge hour: Self Use (AC discharge)
                elif price_is_high and soc > min_soc:
                    deficit_kwh = max(0, s["cons_w"] - s["pv_w"]) / 1000.0
                    if deficit_kwh > 0.1:
                        drain = min(deficit_kwh, soc - min_soc, cfg.eff_ac_discharge_kw)
                        soc -= drain
                        total_discharged += drain
                        saved = drain * price
                        discharge_revenue += saved
                        actions.append(self._make_action(
                            "DischargeBattery", start_utc, end_utc, drain,
                            saved,
                            f"Self Use {drain:.1f} kWh @ €{price:.3f}/kWh "
                            f"(€{saved:.2f} dure import vermeden)"
                        ))

                # 6. Default: Self Use for remaining deficit (AC discharge)
                else:
                    deficit_kwh = max(0, s["cons_w"] - s["pv_w"]) / 1000.0
                    if deficit_kwh > 0 and soc > min_soc:
                        drain = min(deficit_kwh, soc - min_soc, cfg.eff_ac_discharge_kw)
                        soc -= drain
                        pv_savings += drain * price

            # Clamp SoC
            soc = max(0, min(cfg.capacity_kwh, soc))

        # Final SoC point
        if slots:
            soc_curve.append({
                "timestampUtc": slots[-1]["end"],
                "soCKwh": round(soc, 2),
                "capacityKwh": cfg.capacity_kwh,
            })

        # --- Calculate results ---
        profit = discharge_revenue - charge_cost
        cycles = min(
            int(total_charged / cfg.capacity_kwh + 0.5) if cfg.capacity_kwh > 0 else 0,
            int(total_discharged / cfg.capacity_kwh + 0.5) if cfg.capacity_kwh > 0 else 0,
        )

        # Build summary
        charge_hours = sum(1 for a in actions if a["kind"] == "ChargeBattery")
        export_hours = sum(1 for a in actions if a["kind"] == "ExportToGrid")
        solar_hours = sum(1 for a in actions if a["kind"] == "SolarCharge")
        selfuse_hours = sum(1 for a in actions if a["kind"] == "DischargeBattery")
        strategy = "export" if cfg.grid_export_enabled else "saldering"
        summary = (
            f"{strategy}: {cycles} cyclus, {charge_hours}u laden"
            + (f", {export_hours}u export" if export_hours else "")
            + (f", {selfuse_hours}u self-use" if selfuse_hours else "")
            + (f", {solar_hours}u zon" if solar_hours else "")
            + f" · winst €{profit:.2f}"
        )

        _LOG.info("Arbitrage optimizer: %s", summary)

        return ArbitrageResult(
            actions=actions,
            soc_curve=soc_curve,
            projected_profit_eur=round(profit, 2),
            charge_cost_eur=round(charge_cost, 2),
            discharge_revenue_eur=round(discharge_revenue, 2),
            pv_savings_eur=round(pv_savings, 2),
            cycles=cycles,
            summary=summary,
        )

    @staticmethod
    def _make_action(kind: str, start: str, end: str, kwh: float,
                     savings: float, rationale: str) -> dict:
        """Build an action dict matching the EmsActionDto format."""
        return {
            "kind": kind,
            "risk": "Low",
            "startUtc": start,
            "endUtc": end,
            "kwh": round(kwh, 1),
            "eurSavings": round(savings, 2),
            "rationale": rationale,
        }

    @staticmethod
    def _local_hour(utc_str: str) -> int:
        """Parse UTC timestamp and return local hour."""
        try:
            dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            return dt.astimezone().hour
        except (ValueError, AttributeError):
            return 12  # safe default

    @staticmethod
    def _is_night_hour(hour: int, cfg: ArbitrageConfig) -> bool:
        """Check if the local hour falls in the overnight reserve window."""
        if cfg.night_start_hour > cfg.night_end_hour:
            # e.g., 22..6 wraps around midnight
            return hour >= cfg.night_start_hour or hour < cfg.night_end_hour
        return cfg.night_start_hour <= hour < cfg.night_end_hour

    @staticmethod
    def _hours_until_night(hour: int, cfg: ArbitrageConfig) -> int:
        """Hours from current local hour until night_start_hour."""
        diff = cfg.night_start_hour - hour
        if diff <= 0:
            diff += 24
        return diff
