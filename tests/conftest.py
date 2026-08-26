"""Shared fixtures for SorterLab tests."""

from __future__ import annotations

from sorterlab.constants import DEFAULT_PARAMETERS, DEFAULT_SEED
from sorterlab.types import SystemParameters

DEFAULT_SYSTEM_PARAMETERS = SystemParameters(**DEFAULT_PARAMETERS)

# First five LCG outputs with seed 20260823 (verified against sorterlab-model.js).
REFERENCE_RNG_VALUES = [
    0.367197232786566,
    0.20997203164733946,
    0.932045760564506,
    0.7056716072838753,
    0.2681821654550731,
]

# Default scenario capacities (items/hour).
REFERENCE_CAPACITIES = {
    "feed": 108_000.0,
    "sort": 114_240.0,
    "amr": 111_888.0,
    "system": 108_000.0,
    "bottleneck": "feed",
    "rho": 0.952,
    "reserve_pct": 8.0,
}

# First five simulation minutes with default parameters and seed.
REFERENCE_SNAPSHOTS = [
    (0, 1620.185698, 1620.185698, 0.0),
    (1, 1686.684600, 1686.684600, 0.0),
    (2, 2090.565085, 1800.0, 290.565085),
    (3, 2107.475458, 1800.0, 598.040543),
    (4, 1997.463312, 1800.0, 795.503855),
]

DEFAULT_SEED_VALUE = DEFAULT_SEED
