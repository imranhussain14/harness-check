import pytest

from harness_check.awg import ohms_per_meter


def test_known_gauge_matches_reference_table():
    # 18 AWG copper is ~6.385 ohms/1000ft => ~0.02095 ohms/m
    assert ohms_per_meter(18) == pytest.approx(6.385 / 1000 * 3.28084, rel=1e-6)


def test_thicker_wire_has_lower_resistance():
    assert ohms_per_meter(10) < ohms_per_meter(20)


def test_interpolated_odd_gauge_is_between_neighbors():
    r19 = ohms_per_meter(19)
    assert ohms_per_meter(18) < r19 < ohms_per_meter(20)


def test_out_of_range_gauge_raises():
    with pytest.raises(ValueError):
        ohms_per_meter(60)
