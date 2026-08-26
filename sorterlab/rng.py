"""Deterministic pseudo-random generator matching the browser simulator."""

from __future__ import annotations

from sorterlab.constants import LCG_INCREMENT, LCG_MODULUS, LCG_MULTIPLIER


class LcgRng:
    """32-bit linear congruential generator used by sorterlab-simulator.html."""

    __slots__ = ("_seed",)

    def __init__(self, seed: int) -> None:
        self._seed = seed & (LCG_MODULUS - 1)

    @property
    def seed(self) -> int:
        return self._seed

    def next_unit(self) -> float:
        self._seed = (self._seed * LCG_MULTIPLIER + LCG_INCREMENT) % LCG_MODULUS
        return self._seed / LCG_MODULUS

    def reset(self, seed: int) -> None:
        self._seed = seed & (LCG_MODULUS - 1)
