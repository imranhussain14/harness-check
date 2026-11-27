from pathlib import Path

from harness_check.checks import run_all_checks
from harness_check.loader import load_spec

EXAMPLE = Path(__file__).parent.parent / "examples" / "example_robot.yaml"


def test_example_spec_loads():
    system = load_spec(EXAMPLE)
    assert system.name == "demo-rover"
    assert len(system.loads) == 3


def test_example_spec_has_expected_known_issues():
    system = load_spec(EXAMPLE)
    report = run_all_checks(system)
    checks_hit = {i.check for i in report.issues}
    # The example spec is deliberately built to trip each of these.
    assert {"voltage_drop", "connector_rating", "fuse_rating", "pin_conflict"} <= checks_hit
    assert not report.passed
