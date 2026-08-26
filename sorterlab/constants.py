"""Physical and model constants for the SorterLab research simulator."""

from __future__ import annotations

# Business target used by the exploratory analysis.
DEFAULT_GOAL_ITEMS_PER_HOUR = 100_000
DEFAULT_GOAL_ITEMS_PER_MINUTE = DEFAULT_GOAL_ITEMS_PER_HOUR / 60

# Node A: inbound feed and scanning lines.
ITEMS_PER_MINUTE_PER_FEED_LINE = 150

# Node B: cross-belt sorter loops.
ITEMS_PER_HOUR_PER_SORT_LOOP = 30_000
RHO_MIN = 0.65
RHO_SLOPE = 0.12

# Node E: AMR tote removal.
SECONDS_PER_HOUR = 3600

# Demand variability model.
WAVE_PERIOD_MINUTES = 24
NOISE_AMPLITUDE = 0.35

# Deterministic pseudo-random generator (matches browser simulator).
DEFAULT_SEED = 20260823
LCG_MULTIPLIER = 1_664_525
LCG_INCREMENT = 1_013_904_223
LCG_MODULUS = 2**32

# Default scenario from sorterlab-simulator.html sliders.
DEFAULT_PARAMETERS = {
    "feed_lines": 12,
    "sort_loops": 4,
    "amr_count": 37,
    "tote_capacity": 16,
    "amr_cycle_seconds": 19,
    "feed_unevenness": 0.30,
    "direction_concentration": 0.4,
}
