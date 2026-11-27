from harness_check.checks import Severity, run_all_checks
from harness_check.models import Cable, Connector, Fuse, PinAssignment


def test_minimal_system_passes_clean(minimal_system):
    report = run_all_checks(minimal_system)
    assert report.passed
    assert report.errors == []


def test_voltage_drop_flags_long_thin_cable(minimal_system):
    minimal_system.cables = [
        Cable(id="cable-a", load="load-a", awg=26, length_m=3.0, max_drop_pct=3.0)
    ]
    report = run_all_checks(minimal_system)
    drop_issues = [i for i in report.issues if i.check == "voltage_drop"]
    assert any(i.severity == Severity.ERROR for i in drop_issues)


def test_voltage_drop_passes_short_thick_cable(minimal_system):
    minimal_system.cables = [
        Cable(id="cable-a", load="load-a", awg=12, length_m=0.1, max_drop_pct=3.0)
    ]
    report = run_all_checks(minimal_system)
    drop_issues = [i for i in report.issues if i.check == "voltage_drop"]
    assert not any(i.severity == Severity.ERROR for i in drop_issues)


def test_connector_rating_flags_overloaded_connector(minimal_system):
    minimal_system.connectors = [
        Connector(id="conn-a", part="small-conn", rated_current_a=1.0)
    ]
    report = run_all_checks(minimal_system)
    conn_issues = [i for i in report.issues if i.check == "connector_rating"]
    assert any(i.severity == Severity.ERROR for i in conn_issues)


def test_connector_rating_warns_on_missing_rating(minimal_system):
    minimal_system.connectors = [Connector(id="conn-a", part="unknown-conn")]
    report = run_all_checks(minimal_system)
    conn_issues = [i for i in report.issues if i.check == "connector_rating"]
    assert any(i.severity == Severity.WARNING for i in conn_issues)


def test_fuse_rating_flags_undersized_fuse(minimal_system):
    minimal_system.fuses = [Fuse(id="fuse-a", rated_current_a=0.5)]
    report = run_all_checks(minimal_system)
    fuse_issues = [i for i in report.issues if i.check == "fuse_rating"]
    assert any(i.severity == Severity.ERROR for i in fuse_issues)


def test_pin_conflict_detects_duplicate_pin(minimal_system):
    minimal_system.connectors[0].pins = [
        PinAssignment(pin="1", signal="V+"),
        PinAssignment(pin="1", signal="SDA"),
    ]
    report = run_all_checks(minimal_system)
    pin_issues = [i for i in report.issues if i.check == "pin_conflict"]
    assert len(pin_issues) == 1
    assert pin_issues[0].severity == Severity.ERROR


def test_power_budget_flags_peak_exceeding_discharge_rating(minimal_system):
    minimal_system.battery.max_discharge_c = 0.1  # 0.5 Ah * 0.1C is tiny
    report = run_all_checks(minimal_system)
    budget_issues = [i for i in report.issues if i.check == "power_budget"]
    assert any(i.severity == Severity.ERROR for i in budget_issues)


def test_power_budget_estimates_runtime(minimal_system):
    report = run_all_checks(minimal_system)
    assert "estimated_runtime_hours" in report.totals
    assert report.totals["estimated_runtime_hours"] > 0


def test_unknown_load_reference_on_cable_is_an_error(minimal_system):
    minimal_system.cables = [Cable(id="cable-x", load="does-not-exist", awg=18, length_m=0.1)]
    report = run_all_checks(minimal_system)
    assert any(i.check == "voltage_drop" and i.severity == Severity.ERROR for i in report.issues)
