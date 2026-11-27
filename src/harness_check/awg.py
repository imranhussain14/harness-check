"""Standard AWG copper wire resistance table and helpers."""

# Ohms per 1000 ft, solid copper wire at 20 degC (standard reference values).
_OHMS_PER_KFT: dict[int, float] = {
    0: 0.0983,
    2: 0.1563,
    4: 0.2485,
    6: 0.3951,
    8: 0.6282,
    10: 0.9989,
    12: 1.588,
    14: 2.525,
    16: 4.016,
    18: 6.385,
    20: 10.15,
    22: 16.14,
    24: 25.67,
    26: 40.81,
    28: 64.9,
    30: 103.2,
}

_FT_PER_M = 3.28084


def ohms_per_meter(awg: int) -> float:
    """Return copper resistance in ohms/meter for a standard AWG size.

    Raises ValueError for AWG sizes not in the standard table (odd gauges
    between the listed even sizes, or anything wildly out of range).
    """
    if awg in _OHMS_PER_KFT:
        return _OHMS_PER_KFT[awg] / 1000 * _FT_PER_M
    # Interpolate for odd gauges between known even gauges, since wire
    # resistance is log-linear in AWG over this range.
    lower = max((k for k in _OHMS_PER_KFT if k < awg), default=None)
    upper = min((k for k in _OHMS_PER_KFT if k > awg), default=None)
    if lower is None or upper is None:
        raise ValueError(f"AWG {awg} is outside the supported range (0-30)")
    import math

    log_lower, log_upper = math.log(_OHMS_PER_KFT[lower]), math.log(_OHMS_PER_KFT[upper])
    frac = (awg - lower) / (upper - lower)
    interpolated = math.exp(log_lower + frac * (log_upper - log_lower))
    return interpolated / 1000 * _FT_PER_M
