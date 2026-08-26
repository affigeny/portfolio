"""Node capacity and bottleneck calculations."""

from __future__ import annotations

import math

from sorterlab.constants import (
    DEFAULT_GOAL_ITEMS_PER_HOUR,
    ITEMS_PER_HOUR_PER_SORT_LOOP,
    ITEMS_PER_MINUTE_PER_FEED_LINE,
    RHO_MIN,
    RHO_SLOPE,
    SECONDS_PER_HOUR,
)
from sorterlab.types import BottleneckNode, CapacityResult, SystemParameters


def direction_efficiency(direction_concentration: float) -> float:
    """Scenario correction rho(k) for skewed destination mix."""
    return max(RHO_MIN, 1.0 - RHO_SLOPE * direction_concentration)


def compute_capacities(
    params: SystemParameters,
    *,
    goal_items_per_hour: float = DEFAULT_GOAL_ITEMS_PER_HOUR,
) -> CapacityResult:
    """Compute hourly capacities for nodes A, B, E and the system bottleneck.

    Formulas (items/hour):
      A = feed_lines * 150 * 60
      B = sort_loops * 30_000 * rho(k)
      E = amr_count * floor(3600 / cycle_seconds) * tote_capacity
      T_sys = min(A, B, E)
    """
    rho = direction_efficiency(params.direction_concentration)

    feed = params.feed_lines * ITEMS_PER_MINUTE_PER_FEED_LINE * 60
    sort_cap = params.sort_loops * ITEMS_PER_HOUR_PER_SORT_LOOP * rho
    trips_per_hour = math.floor(SECONDS_PER_HOUR / params.amr_cycle_seconds)
    amr = params.amr_count * trips_per_hour * params.tote_capacity

    nodes: list[tuple[BottleneckNode, float]] = [
        (BottleneckNode.FEED, feed),
        (BottleneckNode.SORT, sort_cap),
        (BottleneckNode.AMR, amr),
    ]
    bottleneck_node, system = min(nodes, key=lambda item: item[1])
    reserve_pct = (system / goal_items_per_hour - 1.0) * 100.0

    return CapacityResult(
        feed_items_per_hour=feed,
        sort_items_per_hour=sort_cap,
        amr_items_per_hour=amr,
        system_items_per_hour=system,
        bottleneck=bottleneck_node,
        direction_efficiency=rho,
        reserve_vs_goal_pct=reserve_pct,
    )
