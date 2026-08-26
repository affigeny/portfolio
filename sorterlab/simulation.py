"""Discrete-time flow simulation with deterministic demand noise."""

from __future__ import annotations

import math

from sorterlab.capacity import compute_capacities
from sorterlab.constants import (
    DEFAULT_GOAL_ITEMS_PER_HOUR,
    NOISE_AMPLITUDE,
    WAVE_PERIOD_MINUTES,
)
from sorterlab.rng import LcgRng
from sorterlab.types import MinuteSnapshot, SimulationConfig, SimulationResult, SimulationState
from sorterlab.validation import validate_simulation_config


def incoming_rate(
    *,
    minute: int,
    goal_items_per_minute: float,
    feed_unevenness: float,
    rng: LcgRng,
) -> float:
    """Compute stochastic inbound rate for one minute."""
    wave = 1.0 + feed_unevenness * math.sin(2.0 * math.pi * minute / WAVE_PERIOD_MINUTES)
    noise = 1.0 + feed_unevenness * NOISE_AMPLITUDE * (rng.next_unit() * 2.0 - 1.0)
    return max(0.0, goal_items_per_minute * wave * noise)


def step(
    state: SimulationState,
    config: SimulationConfig,
    *,
    capacity_items_per_hour: float | None = None,
) -> MinuteSnapshot:
    """Advance the simulation by one minute."""
    validate_simulation_config(config)

    capacity = (
        capacity_items_per_hour
        if capacity_items_per_hour is not None
        else compute_capacities(
            config.parameters,
            goal_items_per_hour=config.goal_items_per_hour,
        ).system_items_per_hour
    )

    goal_per_minute = config.goal_items_per_hour / 60.0
    rng = LcgRng(state.seed)

    incoming = incoming_rate(
        minute=state.tick,
        goal_items_per_minute=goal_per_minute,
        feed_unevenness=config.parameters.feed_unevenness,
        rng=rng,
    )

    capacity_per_minute = capacity / 60.0
    processed = min(incoming + state.backlog_items, capacity_per_minute)
    backlog = max(0.0, state.backlog_items + incoming - processed)

    snapshot = MinuteSnapshot(
        minute=state.tick,
        incoming_items_per_minute=incoming,
        processed_items_per_minute=processed,
        backlog_items=backlog,
    )

    state.tick += 1
    state.backlog_items = backlog
    state.seed = rng.seed
    state.history_feed.append(incoming)
    state.history_processed.append(processed)

    return snapshot


def run_simulation(config: SimulationConfig) -> SimulationResult:
    """Run a full simulation for the configured duration."""
    validate_simulation_config(config)

    capacity = compute_capacities(
        config.parameters,
        goal_items_per_hour=config.goal_items_per_hour,
    )
    state = SimulationState(seed=config.seed)
    snapshots: list[MinuteSnapshot] = []

    for _ in range(config.duration_minutes):
        snapshots.append(step(state, config, capacity_items_per_hour=capacity.system_items_per_hour))

    return SimulationResult(
        config=config,
        capacity=capacity,
        snapshots=tuple(snapshots),
    )
