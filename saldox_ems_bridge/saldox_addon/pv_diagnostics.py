"""PV-stringdiagnose: signaleert een uitgevallen of lekkende string.

WAAROM DIT BESTAAT
String 2 viel uit in de nacht van 8 op 9 september 2026 en bleef zestien dagen
onopgemerkt liggen -- ruwweg tweederde van de opwek. De data lag er de hele
tijd: pv2_power ging naar 0, de stringspanning stortte in van 450 V naar 6 V,
en de isolatieweerstand zakte van 384 kOhm naar 50 kOhm. Niemand kreeg een
seintje. Dit bestand is de reden dat dat niet nog eens gebeurt.

DREMPELS
Teruggetoetst op 75 dagen eigen historie (13 juli - 23 september 2026):

  string dood      27 treffers, exact twee aaneengesloten blokken
                   (15-25 juli en 8 sept-heden). Nul losse valse meldingen op
                   de 48 gezonde dagen ertussen.

  isolatie <50%    8 meldingen in 75 dagen. Allemaal in de aanloop naar het
                   defect; de eerste op 27 augustus, twaalf dagen voor de
                   string het begaf. Bij 60% komen er twee meldingen bij zonder
                   nieuwe informatie; bij 40% mist hij 8 september.

LOKALE DAGEN, GEEN UTC
De dagindeling volgt de lokale tijd. Tijdens de terugtoets bleken dag- en
uurstatistieken in Home Assistant een dag te verschillen, vrijwel zeker doordat
HA lokaal groepeert en de query UTC-labels gaf. Een alarm dat op datums afgaat
moet dezelfde dagen hanteren als de gebruiker ziet.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_LOG = logging.getLogger(__name__)

# Home Assistant koppelt /data als persistente opslag; die overleeft herstart
# en add-on-update. Zonder dit zou "bevestigd" bij elke herstart terugkomen --
# en de add-on herstartte vandaag al drie keer.
STATE_PATH = os.environ.get("SALDOX_DIAG_STATE", "/data/pv_diagnostics.json")

LOCAL_OFFSET_HOURS = 2          # CEST; alleen voor de dagindeling
DAYLIGHT_MIN_W = 200            # ondergrens waarboven we een string "actief" noemen
STRING_DEAD_MINUTES = 30        # hoe lang het verschil moet aanhouden
VOLTAGE_COLLAPSE_FRACTION = 0.20
INSULATION_FRACTION = 0.50      # gekozen op basis van de terugtoets
INSULATION_BASELINE_DAYS = 14
VOLTAGE_BASELINE_DAYS = 7
MIN_BASELINE_DAYS = 5           # onder dit aantal geen oordeel -- te weinig historie


def _local_day(ts: datetime) -> str:
    return (ts + timedelta(hours=LOCAL_OFFSET_HOURS)).strftime("%Y-%m-%d")


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[len(s) // 2]


@dataclass
class Alarm:
    key: str
    severity: str          # "warning" | "critical"
    title: str
    detail: str
    since: str             # ISO-tijdstip van eerste signalering

    def as_dict(self, acknowledged: bool) -> dict:
        return {
            "key": self.key,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "since": self.since,
            "acknowledged": acknowledged,
        }


@dataclass
class PvDiagnostics:
    """Houdt dagelijkse basislijnen bij en beoordeelt de huidige meting."""

    # dag -> laagste isolatiewaarde die dag
    insulation_daily_min: dict[str, float] = field(default_factory=dict)
    # dag -> hoogste spanning per string
    voltage_daily_max: dict[str, dict[str, float]] = field(default_factory=dict)
    # string -> tijdstip waarop hij voor het eerst dood leek
    dead_since: dict[str, str] = field(default_factory=dict)
    # alarmsleutel -> tijdstip van bevestigen
    acknowledged: dict[str, str] = field(default_factory=dict)

    # ---------------------------------------------------------------- opslag
    @classmethod
    def load(cls) -> "PvDiagnostics":
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            return cls(
                insulation_daily_min=raw.get("insulation_daily_min", {}),
                voltage_daily_max=raw.get("voltage_daily_max", {}),
                dead_since=raw.get("dead_since", {}),
                acknowledged=raw.get("acknowledged", {}),
            )
        except FileNotFoundError:
            return cls()
        except Exception as ex:                      # corrupte state mag niet fataal zijn
            _LOG.warning("Diagnose-state onleesbaar (%s) — opnieuw beginnen", ex)
            return cls()

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
            tmp = STATE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({
                    "insulation_daily_min": self.insulation_daily_min,
                    "voltage_daily_max": self.voltage_daily_max,
                    "dead_since": self.dead_since,
                    "acknowledged": self.acknowledged,
                }, fh)
            os.replace(tmp, STATE_PATH)              # atomair; geen half bestand bij stroomuitval
        except Exception as ex:
            _LOG.warning("Diagnose-state niet op te slaan: %s", ex)

    def _prune(self, keep_days: int = 45) -> None:
        cutoff = _local_day(datetime.now(timezone.utc) - timedelta(days=keep_days))
        for store in (self.insulation_daily_min, self.voltage_daily_max):
            for day in [d for d in store if d < cutoff]:
                del store[day]

    # ------------------------------------------------------------ bijwerken
    def observe(self, readings: dict, now: datetime | None = None) -> None:
        """Verwerk één meting in de dagelijkse basislijnen."""
        now = now or datetime.now(timezone.utc)
        day = _local_day(now)

        def val(key: str):
            entry = readings.get(key)
            return entry.get("value") if isinstance(entry, dict) else None

        iso = val("insulation_resistance")
        if isinstance(iso, (int, float)) and iso > 0:
            prev = self.insulation_daily_min.get(day)
            self.insulation_daily_min[day] = min(prev, iso) if prev is not None else float(iso)

        for s in ("pv1", "pv2"):
            v = val(f"{s}_voltage_v")
            if isinstance(v, (int, float)):
                bucket = self.voltage_daily_max.setdefault(day, {})
                bucket[s] = max(bucket.get(s, 0.0), float(v))

        self._prune()

    # -------------------------------------------------------------- oordeel
    def evaluate(self, readings: dict, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(timezone.utc)
        today = _local_day(now)
        alarms: list[Alarm] = []

        def val(key: str):
            entry = readings.get(key)
            return entry.get("value") if isinstance(entry, dict) else None

        p1, p2 = val("pv1_power_w"), val("pv2_power_w")

        # --- Regel 1: één string levert, de andere niets ---
        for dead, alive, dead_name in (("pv1", "pv2", "1"), ("pv2", "pv1", "2")):
            dp = p1 if dead == "pv1" else p2
            ap = p2 if dead == "pv1" else p1
            if not isinstance(dp, (int, float)) or not isinstance(ap, (int, float)):
                continue
            if ap > DAYLIGHT_MIN_W and dp <= 0:
                first = self.dead_since.get(dead)
                if first is None:
                    self.dead_since[dead] = now.isoformat()
                    continue                                 # eerst laten aanhouden
                elapsed = now - datetime.fromisoformat(first)
                if elapsed >= timedelta(minutes=STRING_DEAD_MINUTES):
                    alarms.append(Alarm(
                        key=f"string_dead_{dead}",
                        severity="critical",
                        title=f"String {dead_name} levert niets",
                        detail=(f"String {dead_name} staat op 0 W terwijl de andere "
                                f"{int(ap)} W levert, al sinds {first[:16].replace('T', ' ')}. "
                                f"Controleer de DC-zijde: zekering, MC4-connectoren, "
                                f"doorvoer."),
                        since=first,
                    ))
            else:
                self.dead_since.pop(dead, None)

        # --- Regel 2: stringspanning ingestort ---
        #
        # Alleen beoordelen wanneer de ANDERE string aantoonbaar levert. Dat is
        # het bewijs dat er zon is; zonder die voorwaarde vergelijk je een
        # ochtendwaarde met een dagmaximum en vuurt de regel elke dag opnieuw.
        # De proefdraai op 75 dagen historie liet dat zien: 42 valse dagen voor
        # BEIDE strings, terwijl string 1 nooit defect is geweest.
        #
        # We toetsen de MOMENTANE spanning, niet het dagmaximum: een string die
        # instort doet dat binnen een uur, en dan wil je het meteen zien.
        for s, name, other in (("pv1", "1", "pv2"), ("pv2", "2", "pv1")):
            v = val(f"{s}_voltage_v")
            other_p = val(f"{other}_power_w")
            if not isinstance(v, (int, float)) or not isinstance(other_p, (int, float)):
                continue
            if other_p <= DAYLIGHT_MIN_W:
                continue                      # geen zon, of de andere string is óók stil
            hist = [d[s] for day, d in sorted(self.voltage_daily_max.items())
                    if day < today and s in d and d[s] > 0]
            hist = hist[-VOLTAGE_BASELINE_DAYS:]
            if len(hist) < MIN_BASELINE_DAYS:
                continue
            baseline = _median(hist)
            if baseline > 0 and v < baseline * VOLTAGE_COLLAPSE_FRACTION:
                alarms.append(Alarm(
                    key=f"voltage_collapse_{s}",
                    severity="critical",
                    title=f"Stringspanning {name} ingestort",
                    detail=(f"Spanning {v:.0f} V terwijl string {other[-1]} "
                            f"{int(other_p)} W levert; normaal staat deze string "
                            f"op {baseline:.0f} V. Wijst op een onderbroken of "
                            f"kortgesloten string."),
                    since=now.isoformat(),
                ))

        # --- Regel 3: isolatieweerstand weggezakt ---
        iso = val("insulation_resistance")
        hist = [v for day, v in sorted(self.insulation_daily_min.items())
                if day < today][-INSULATION_BASELINE_DAYS:]
        if isinstance(iso, (int, float)) and len(hist) >= MIN_BASELINE_DAYS:
            baseline = _median(hist)
            todays_min = self.insulation_daily_min.get(today, float(iso))
            if baseline > 0 and todays_min < baseline * INSULATION_FRACTION:
                alarms.append(Alarm(
                    key="insulation_drop",
                    severity="warning",
                    title="Isolatieweerstand sterk gedaald",
                    detail=(f"Laagste waarde vandaag {todays_min:.0f} kΩ, tegen "
                            f"{baseline:.0f} kΩ over de afgelopen twee weken. "
                            f"Wijst op vocht of een aardlek in de DC-zijde. "
                            f"Dit signaal ging in augustus 2026 twaalf dagen vóór "
                            f"de stringuitval af."),
                    since=now.isoformat(),
                ))

        # Bevestigingen opruimen zodra het alarm verdwijnt, zodat een terugkeer
        # opnieuw opvalt in plaats van stilletjes bevestigd te blijven.
        live = {a.key for a in alarms}
        for key in [k for k in self.acknowledged if k not in live]:
            del self.acknowledged[key]

        self.save()
        return [a.as_dict(a.key in self.acknowledged) for a in alarms]

    # ---------------------------------------------------------- bevestigen
    def acknowledge(self, key: str) -> bool:
        self.acknowledged[key] = datetime.now(timezone.utc).isoformat()
        self.save()
        return True
