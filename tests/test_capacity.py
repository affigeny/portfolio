"""Tests for node capacity and bottleneck selection."""

from __future__ import annotations

import pytest

from sorterlab.capacity import compute_capacities, direction_efficiency
from sorterlab.types import BottleneckNode, SystemParameters
from sorterlab.validation import ValidationError, validate_parameters

from .conftest import DEFAULT_SYSTEM_PARAMETERS, REFERENCE_CAPACITIES


def test_default_capacity_matches_reference():
    result = compute_capacities(DEFAULT_SYSTEM_PARAMETERS)
    assert result.feed_items_per_hour == REFERENCE_CAPACITIES["feed"]
    assert result.sort_items_per_hour == REFERENCE_CAPACITIES["sort"]
    assert result.amr_items_per_hour == REFERENCE_CAPACITIES["amr"]
    assert result.system_items_per_hour == REFERENCE_CAPACITIES["system"]
    assert result.bottleneck == BottleneckNode.FEED
    assert result.direction_efficiency == pytest.approx(REFERENCE_CAPACITIES["rho"])
    assert result.reserve_vs_goal_pct == pytest.approx(REFERENCE_CAPACITIES["reserve_pct"])


def test_direction_efficiency_floor():
    assert direction_efficiency(10.0) == 0.65


def test_bottleneck_switches_to_sort_when_sort_loops_are_few():
    """With one sort loop the sorter, not the feed, becomes the constraint.

    feed_lines=4 -> 36_000 items/h, sort_loops=1 -> 30_000 items/h,
    amr_count=80 -> 1_152_000 items/h. Minimum is sort, so the system
    runs at 30_000 items/h.
    """
    params = SystemParameters(
        feed_lines=4,
        sort_loops=1,
        amr_count=80,
        tote_capacity=40,
        amr_cycle_seconds=10,
        feed_unevenness=0.0,
        direction_concentration=0.0,
    )
    result = compute_capacities(params)
    assert result.bottleneck == BottleneckNode.SORT
    assert result.system_items_per_hour == 30_000


def test_bottleneck_switches_to_amr_with_slow_cycle():
    params = SystemParameters(
        feed_lines=24,
        sort_loops=8,
        amr_count=5,
        tote_capacity=6,
        amr_cycle_seconds=60,
        feed_unevenness=0.0,
        direction_concentration=0.0,
    )
    result = compute_capacities(params)
    assert result.bottleneck == BottleneckNode.AMR
    assert result.amr_items_per_hour == 1_800


def test_validate_parameters_rejects_out_of_range():
    params = SystemParameters(
        feed_lines=3,
        sort_loops=4,
        amr_count=37,
        tote_capacity=16,
        amr_cycle_seconds=19,
        feed_unevenness=0.3,
        direction_concentration=0.4,
    )
    with pytest.raises(ValidationError, match="feed_lines"):
        validate_parameters(params)
