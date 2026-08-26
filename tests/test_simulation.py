"""Tests for minute-by-minute flow simulation."""

from __future__ import annotations

import pytest

from sorterlab.simulation import run_simulation
from sorterlab.types import SimulationConfig
from sorterlab.validation import ValidationError

from .conftest import DEFAULT_SEED_VALUE, DEFAULT_SYSTEM_PARAMETERS, REFERENCE_SNAPSHOTS


def test_default_simulation_snapshots_match_browser_model():
    result = run_simulation(
        SimulationConfig(
            parameters=DEFAULT_SYSTEM_PARAMETERS,
            seed=DEFAULT_SEED_VALUE,
            duration_minutes=len(REFERENCE_SNAPSHOTS),
        )
    )

    assert len(result.snapshots) == len(REFERENCE_SNAPSHOTS)
    for snapshot, (minute, incoming, processed, backlog) in zip(
        result.snapshots, REFERENCE_SNAPSHOTS
    ):
        assert snapshot.minute == minute
        assert snapshot.incoming_items_per_minute == pytest.approx(incoming, rel=1e-6)
        assert snapshot.processed_items_per_minute == pytest.approx(processed, rel=1e-6)
        assert snapshot.backlog_items == pytest.approx(backlog, rel=1e-6)


def test_simulation_rejects_non_positive_duration():
    with pytest.raises(ValidationError, match="duration_minutes"):
        run_simulation(
            SimulationConfig(
                parameters=DEFAULT_SYSTEM_PARAMETERS,
                duration_minutes=0,
            )
        )


def test_peak_backlog_tracks_maximum():
    result = run_simulation(
        SimulationConfig(
            parameters=DEFAULT_SYSTEM_PARAMETERS,
            seed=DEFAULT_SEED_VALUE,
            duration_minutes=5,
        )
    )
    assert result.peak_backlog == pytest.approx(795.503855, rel=1e-6)
    assert result.final_backlog == pytest.approx(795.503855, rel=1e-6)
