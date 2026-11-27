"""Validation engine: runs every check against a RobotElectricalSystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .awg import ohms_per_meter
from .models import RobotElectricalSystem


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Issue:
    severity: Severity
    check: str
    message: str
    subject: str  # the load/cable/connector id this issue is about


@dataclass
class Report:
    system_name: str
    issues: list[Issue] = field(default_factory=list)
    totals: dict = field(default_factory=dict)

    def add(self, severity: Severity, check: str, message: str, subject: str) -> None:
        self.issues.append(Issue(severity, check, message, subject))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def check_voltage_drop(sys: RobotElectricalSystem, report: Report) -> None:
    for cable in sys.cables:
        load = sys.load_by_id(cable.load)
        if load is None:
            report.add(
                Severity.ERROR,
                "voltage_drop",
                f"Cable '{cable.id}' references unknown load '{cable.load}'",
                cable.id,
            )
            continue
        current = load.current.nominal
        length = cable.length_m * (2 if cable.round_trip else 1)
        r_per_m = ohms_per_meter(cable.awg)
        v_drop = current * r_per_m * length
        pct = (v_drop / load.rail_voltage) * 100 if load.rail_voltage else 0.0
        severity = Severity.ERROR if pct > cable.max_drop_pct else Severity.INFO
        msg = (
            f"Cable '{cable.id}' (AWG{cable.awg}, {cable.length_m:.2f} m"
            f"{' round-trip' if cable.round_trip else ' one-way'}) to load "
            f"'{load.display_name()}': {v_drop:.3f} V drop ({pct:.2f}% of "
            f"{load.rail_voltage:g} V) at nominal {current:.2f} A"
        )
        if pct > cable.max_drop_pct:
            msg += f" — exceeds {cable.max_drop_pct:g}% limit"
            report.add(severity, "voltage_drop", msg, cable.id)
        elif pct > cable.max_drop_pct * 0.75:
            report.add(
                Severity.WARNING,
                "voltage_drop",
                msg + " — within 75-100% of limit, little margin",
                cable.id,
            )


def check_connector_ratings(sys: RobotElectricalSystem, report: Report) -> None:
    # Sum nominal/peak current per connector across all loads that use it.
    per_connector: dict[str, dict[str, float]] = {}
    for load in sys.loads:
        if not load.connector:
            continue
        entry = per_connector.setdefault(load.connector, {"nominal": 0.0, "peak": 0.0})
        entry["nominal"] += load.current.nominal
        entry["peak"] += load.current.peak or load.current.nominal

    for conn_id, totals in per_connector.items():
        connector = sys.connector_by_id(conn_id)
        if connector is None:
            report.add(
                Severity.ERROR,
                "connector_rating",
                f"Load references unknown connector '{conn_id}'",
                conn_id,
            )
            continue
        if connector.rated_current_a is None:
            report.add(
                Severity.WARNING,
                "connector_rating",
                f"Connector '{conn_id}' has no rated_current_a set; cannot check "
                f"{totals['peak']:.2f} A peak load against it",
                conn_id,
            )
            continue
        if totals["peak"] > connector.rated_current_a:
            report.add(
                Severity.ERROR,
                "connector_rating",
                f"Connector '{conn_id}' ({connector.part or 'unspecified part'}) is rated "
                f"{connector.rated_current_a:g} A but sees {totals['peak']:.2f} A peak load",
                conn_id,
            )
        elif totals["peak"] > connector.rated_current_a * 0.8:
            report.add(
                Severity.WARNING,
                "connector_rating",
                f"Connector '{conn_id}' is at {totals['peak'] / connector.rated_current_a * 100:.0f}% "
                f"of its {connector.rated_current_a:g} A rating at peak load — little margin",
                conn_id,
            )


def check_fuse_ratings(sys: RobotElectricalSystem, report: Report) -> None:
    per_fuse: dict[str, dict[str, float]] = {}
    for load in sys.loads:
        if not load.fuse:
            continue
        entry = per_fuse.setdefault(load.fuse, {"nominal": 0.0, "peak": 0.0})
        entry["nominal"] += load.current.nominal
        entry["peak"] += load.current.peak or load.current.nominal

    for fuse_id, totals in per_fuse.items():
        fuse = sys.fuse_by_id(fuse_id)
        if fuse is None:
            report.add(
                Severity.ERROR, "fuse_rating", f"Load references unknown fuse '{fuse_id}'", fuse_id
            )
            continue
        if totals["nominal"] > fuse.rated_current_a:
            report.add(
                Severity.ERROR,
                "fuse_rating",
                f"Fuse '{fuse_id}' is rated {fuse.rated_current_a:g} A but sees "
                f"{totals['nominal']:.2f} A nominal load — it will blow under normal operation",
                fuse_id,
            )
        elif totals["peak"] > fuse.rated_current_a:
            report.add(
                Severity.WARNING,
                "fuse_rating",
                f"Fuse '{fuse_id}' ({fuse.rated_current_a:g} A) is exceeded by peak load "
                f"({totals['peak']:.2f} A) — will blow during peak events",
                fuse_id,
            )


def check_pin_conflicts(sys: RobotElectricalSystem, report: Report) -> None:
    for connector in sys.connectors:
        seen: dict[str, str] = {}
        for assignment in connector.pins:
            if assignment.pin in seen:
                report.add(
                    Severity.ERROR,
                    "pin_conflict",
                    f"Connector '{connector.id}' pin '{assignment.pin}' is assigned to both "
                    f"'{seen[assignment.pin]}' and '{assignment.signal}'",
                    connector.id,
                )
            else:
                seen[assignment.pin] = assignment.signal


def check_power_budget(sys: RobotElectricalSystem, report: Report) -> None:
    def total_watts(mode: str) -> float:
        total = 0.0
        for load in sys.loads:
            current = getattr(load.current, mode)
            if current is None:
                current = load.current.nominal
            total += current * load.rail_voltage
        return total

    battery = sys.battery
    w_idle = total_watts("idle")
    w_nominal = total_watts("nominal")
    w_peak = total_watts("peak")

    # Rough current draw as seen by the battery, assuming pack voltage approximates
    # the rail voltages (fine for a first-pass budget; flag it as an approximation).
    i_nominal_at_pack = w_nominal / battery.nominal_voltage
    i_peak_at_pack = w_peak / battery.nominal_voltage
    max_discharge = battery.max_discharge_current_a

    report.totals.update(
        {
            "watts_idle": w_idle,
            "watts_nominal": w_nominal,
            "watts_peak": w_peak,
            "battery_max_discharge_a": max_discharge,
            "approx_pack_current_nominal_a": i_nominal_at_pack,
            "approx_pack_current_peak_a": i_peak_at_pack,
        }
    )

    if i_peak_at_pack > max_discharge:
        report.add(
            Severity.ERROR,
            "power_budget",
            f"Peak load draws ~{i_peak_at_pack:.2f} A from the pack, exceeding the battery's "
            f"max continuous discharge of {max_discharge:.2f} A "
            f"({battery.capacity_ah:g} Ah x {battery.max_discharge_c:g} C)",
            battery.name,
        )
    elif i_peak_at_pack > max_discharge * 0.8:
        report.add(
            Severity.WARNING,
            "power_budget",
            f"Peak draw (~{i_peak_at_pack:.2f} A) is within 80-100% of the battery's max "
            f"discharge ({max_discharge:.2f} A) — little margin",
            battery.name,
        )

    if i_nominal_at_pack > 0:
        usable_ah = battery.capacity_ah * battery.usable_fraction
        runtime_hours = usable_ah / i_nominal_at_pack
        report.totals["estimated_runtime_hours"] = runtime_hours
        report.add(
            Severity.INFO,
            "power_budget",
            f"Estimated runtime at nominal load: {runtime_hours:.2f} h "
            f"({usable_ah:.2f} Ah usable / {i_nominal_at_pack:.2f} A)",
            battery.name,
        )


ALL_CHECKS = [
    check_voltage_drop,
    check_connector_ratings,
    check_fuse_ratings,
    check_pin_conflicts,
    check_power_budget,
]


def run_all_checks(sys: RobotElectricalSystem) -> Report:
    report = Report(system_name=sys.name)
    for check in ALL_CHECKS:
        check(sys, report)
    return report
