"""Tests for deterministic RNG parity with the browser simulator."""

from __future__ import annotations

from sorterlab.constants import DEFAULT_SEED
from sorterlab.rng import LcgRng

from .conftest import REFERENCE_RNG_VALUES


def test_lcg_sequence_matches_browser_model():
    rng = LcgRng(DEFAULT_SEED)
    values = [rng.next_unit() for _ in range(len(REFERENCE_RNG_VALUES))]
    assert values == REFERENCE_RNG_VALUES


def test_reset_restores_sequence():
    rng = LcgRng(DEFAULT_SEED)
    _ = rng.next_unit()
    rng.reset(DEFAULT_SEED)
    assert rng.next_unit() == REFERENCE_RNG_VALUES[0]
