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
    """Tunable parameters for the optimizer."""
    capacity_kwh: float = 30.0
    max_power_kw: float = 15.0
    efficiency: float = 0.90          # roundtrip (charge × discharge)
    min_soc_pct: float = 20.0         # overnight reserve (% of capacity)
    min_spread_eur: float = 0.02      # minimum profitable spread per kWh
    night_start_hour: int = 22        # local hour — start of overnight reserve window
    night_end_hour: int = 6           # local hour — end of overnight reserve window
    max_cycles_per_day: int = 2       # limit battery wear
    grid_export_enabled: bool = False # False = NL saldering strategie:
    #   Batterij laden in daluren → batterij vol → PV gaat naar grid (saldering)
    #   Batterij ontlaadt via Self Use in dure uren → vermijdt grid import


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
            if s["net_w"] > 100:  # >100W surplus threshold
                s["free_charge_kwh"] = min(s["net_w"] / 1000.0, cfg.max_power_kw)
            else:
                s["free_charge_kwh"] = 0.0

        # --- Pass 2: Price arbitrage pools ---
        prices = sorted(s["price"] for s in slots)
        median_price = prices[len(prices) // 2]

        # Charge candidates: cheapest hours (sorted cheapest first)
        charge_candidates = sorted(
            [s for s in slots if s["price"] < median_price],
            key=lambda s: s["price"]
        )

        # Discharge/self-use candidates: most expensive hours (sorted most expensive first)
        discharge_candidates = sorted(
            [s for s in slots if s["price"] > median_price],
            key=lambda s: -s["price"]
        )

        if not charge_candidates or not discharge_candidates:
            return ArbitrageResult(summary="Geen prijs-spread gevonden")

        cheapest = charge_candidates[0]["price"]
        most_expensive = discharge_candidates[0]["price"]
        spread = most_expensive * cfg.efficiency - cheapest
        if spread < cfg.min_spread_eur:
            return ArbitrageResult(
                summary=f"Spread te klein ({spread:.3f} €/kWh < {cfg.min_spread_eur})"
            )

        # Mark charge and discharge pools
        hours_per_cycle = max(1, int(cfg.capacity_kwh / cfg.max_power_kw))
        max_charge_hours = hours_per_cycle * cfg.max_cycles_per_day
        max_discharge_hours = hours_per_cycle * cfg.max_cycles_per_day

        charge_set = {s["idx"] for s in charge_candidates[:max_charge_hours]}
        discharge_set = {s["idx"] for s in discharge_candidates[:max_discharge_hours]}

        # --- Pass 3: Forward SoC simulation ---
        soc = current_soc_kwh
        min_soc = cfg.capacity_kwh * cfg.min_soc_pct / 100.0
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
                # Batterij exporteert naar grid in dure uren.

                # 1. PV surplus → SolarCharge (skip als export-slot)
                free_kwh = min(s["free_charge_kwh"], cfg.capacity_kwh - soc)
                if free_kwh > 0.1 and s["idx"] not in discharge_set:
                    soc += free_kwh
                    pv_savings += free_kwh * price
                    actions.append(self._make_action(
                        "SolarCharge", start_utc, end_utc, free_kwh,
                        free_kwh * price,
                        f"PV-overschot {free_kwh:.1f} kWh opslaan (€{price:.3f}/kWh vermeden)"
                    ))

                # 2. Grid charge in cheap hours
                if s["idx"] in charge_set and soc < cfg.capacity_kwh - 0.5:
                    room = cfg.capacity_kwh - soc
                    charge_kwh = min(room, cfg.max_power_kw)
                    if charge_kwh > 0.5:
                        soc += charge_kwh
                        charge_cost += charge_kwh * price
                        total_charged += charge_kwh
                        est_profit = charge_kwh * (most_expensive * cfg.efficiency - price)
                        actions.append(self._make_action(
                            "ChargeBattery", start_utc, end_utc, charge_kwh,
                            max(0, est_profit),
                            f"Laden @ €{price:.3f}/kWh → export @ €{most_expensive:.3f}/kWh"
                        ))

                # 3. Export to grid in expensive hours
                elif s["idx"] in discharge_set and not is_night:
                    hours_to_night = self._hours_until_night(hour, cfg)
                    effective_min = min_soc if hours_to_night <= 3 else 0.5
                    available = soc - effective_min
                    discharge_kwh = min(available, cfg.max_power_kw)
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

                # 4. Default: Self Use
                else:
                    deficit_kwh = max(0, s["cons_w"] - s["pv_w"]) / 1000.0
                    if deficit_kwh > 0 and soc > min_soc:
                        drain = min(deficit_kwh, soc - min_soc, cfg.max_power_kw)
                        soc -= drain
                        pv_savings += drain * price

            else:
                # ===== SALDERING STRATEGIE (geen grid export) =====
                # Laden in daluren → batterij vol → PV gaat naar grid (saldering)
                # Dure uren → Self Use (batterij dekt verbruik, vermijdt dure import)

                # 1. Grid charge in cheapest hours (batterij vol maken vóór zonne-uren)
                if s["idx"] in charge_set and soc < cfg.capacity_kwh - 0.5:
                    room = cfg.capacity_kwh - soc
                    charge_kwh = min(room, cfg.max_power_kw)
                    if charge_kwh > 0.5:
                        soc += charge_kwh
                        charge_cost += charge_kwh * price
                        total_charged += charge_kwh
                        actions.append(self._make_action(
                            "ChargeBattery", start_utc, end_utc, charge_kwh,
                            charge_kwh * (most_expensive - price),
                            f"Laden @ €{price:.3f}/kWh — batterij vol → PV gaat naar grid (saldering)"
                        ))

                # 2. During PV surplus hours: battery is full → PV goes to grid via saldering
                #    We DON'T charge the battery (it's already full from cheap grid hours).
                #    Instead we let PV flow to grid = saldering revenue.
                elif s["free_charge_kwh"] > 0.1 and soc >= cfg.capacity_kwh - 1.0:
                    # Battery full, PV surplus goes to grid via saldering
                    surplus = s["free_charge_kwh"]
                    pv_savings += surplus * price  # saldering: valued at current price
                    actions.append(self._make_action(
                        "DischargeBattery", start_utc, end_utc, 0,
                        surplus * price,
                        f"Batterij vol → {surplus:.1f} kWh PV naar grid (saldering @ €{price:.3f}/kWh)"
                    ))

                # 3. PV surplus but battery not full → charge from solar (free)
                elif s["free_charge_kwh"] > 0.1:
                    free_kwh = min(s["free_charge_kwh"], cfg.capacity_kwh - soc)
                    if free_kwh > 0.1:
                        soc += free_kwh
                        pv_savings += free_kwh * price
                        actions.append(self._make_action(
                            "SolarCharge", start_utc, end_utc, free_kwh,
                            free_kwh * price,
                            f"PV-overschot {free_kwh:.1f} kWh opslaan (€{price:.3f}/kWh vermeden)"
                        ))

                # 4. Expensive hours: Self Use — battery covers home, avoids import
                elif s["idx"] in discharge_set and soc > min_soc:
                    deficit_kwh = max(0, s["cons_w"] - s["pv_w"]) / 1000.0
                    if deficit_kwh > 0.1:
                        drain = min(deficit_kwh, soc - min_soc, cfg.max_power_kw)
                        soc -= drain
                        total_discharged += drain
                        saved = drain * price  # avoided expensive import
                        discharge_revenue += saved
                        actions.append(self._make_action(
                            "DischargeBattery", start_utc, end_utc, drain,
                            saved,
                            f"Self Use {drain:.1f} kWh @ €{price:.3f}/kWh "
                            f"(€{saved:.2f} dure import vermeden)"
                        ))

                # 5. Default: Self Use for remaining deficit
                else:
                    deficit_kwh = max(0, s["cons_w"] - s["pv_w"]) / 1000.0
                    if deficit_kwh > 0 and soc > min_soc:
                        drain = min(deficit_kwh, soc - min_soc, cfg.max_power_kw)
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
