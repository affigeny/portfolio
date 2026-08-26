"""Typed inputs and outputs for the SorterLab model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class BottleneckNode(str, Enum):
    """Physical node that limits system throughput."""

    FEED = "feed"
    SORT = "sort"
    AMR = "amr"

    @property
    def label(self) -> str:
        return {
            BottleneckNode.FEED: "Подача A",
            BottleneckNode.SORT: "Сортировка B",
            BottleneckNode.AMR: "AMR E",
        }[self]


@dataclass(frozen=True)
class SystemParameters:
    """Configurable system configuration.

    All rates are expressed in items (товарных единиц) unless noted otherwise.
    """

    feed_lines: int
    sort_loops: int
    amr_count: int
    tote_capacity: int
    amr_cycle_seconds: int
    feed_unevenness: float
    direction_concentration: float


@dataclass(frozen=True)
class CapacityResult:
    """Hourly capacities for each node and the resulting bottleneck."""

    feed_items_per_hour: float
    sort_items_per_hour: float
    amr_items_per_hour: float
    system_items_per_hour: float
    bottleneck: BottleneckNode
    direction_efficiency: float
    reserve_vs_goal_pct: float


@dataclass(frozen=True)
class SimulationConfig:
    """Runtime options for a discrete-time simulation."""

    parameters: SystemParameters
    goal_items_per_hour: float = 100_000
    seed: int = 20260823
    duration_minutes: int = 60


@dataclass(frozen=True)
class MinuteSnapshot:
    """One simulated minute of flow."""

    minute: int
    incoming_items_per_minute: float
    processed_items_per_minute: float
    backlog_items: float


@dataclass(frozen=True)
class SimulationResult:
    """Full simulation output."""

    config: SimulationConfig
    capacity: CapacityResult
    snapshots: tuple[MinuteSnapshot, ...] = field(default_factory=tuple)

    @property
    def final_backlog(self) -> float:
        if not self.snapshots:
            return 0.0
        return self.snapshots[-1].backlog_items

    @property
    def peak_backlog(self) -> float:
        if not self.snapshots:
            return 0.0
        return max(snapshot.backlog_items for snapshot in self.snapshots)


@dataclass
class SimulationState:
    """Mutable state while stepping through a simulation."""

    tick: int = 0
    backlog_items: float = 0.0
    seed: int = 20260823
    history_feed: list[float] = field(default_factory=list)
    history_processed: list[float] = field(default_factory=list)

    def reset(self, seed: int) -> None:
        self.tick = 0
        self.backlog_items = 0.0
        self.seed = seed
        self.history_feed.clear()
        self.history_processed.clear()


NodeCapacities = dict[BottleneckNode, float]
ExportFormat = Literal["json", "csv", "table"]
