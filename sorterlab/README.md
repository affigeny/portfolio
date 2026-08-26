# SorterLab Python model

Production implementation of the exploratory sorting-center analysis from
`sorterlab.html` and `sorterlab-simulator.html`.

## What it models

The research case decomposes an automated sorting center into three measurable
nodes:

| Node | Meaning | Capacity formula (items/hour) |
|------|---------|-------------------------------|
| **A** | Feed and scanning lines | `feed_lines × 150 × 60` |
| **B** | Cross-belt sort loops | `sort_loops × 30_000 × ρ(k)` |
| **E** | AMR tote removal | `amr_count × floor(3600 / cycle_s) × tote_capacity` |

System throughput is `T_sys = min(A, B, E)`.

The minute-by-minute simulator adds a daily wave and deterministic noise to
demand, then tracks backlog when inbound flow exceeds processing capacity.

## Inputs

`SystemParameters` (validated ranges match the browser sliders):

| Field | Range | Default |
|-------|-------|---------|
| `feed_lines` | 4–24 | 12 |
| `sort_loops` | 1–8 | 4 |
| `amr_count` | 5–80 | 37 |
| `tote_capacity` | 6–40 | 16 |
| `amr_cycle_seconds` | 10–60 | 19 |
| `feed_unevenness` | 0.0–0.60 | 0.30 |
| `direction_concentration` | 0.0–1.5 | 0.4 |

## Outputs

- **`CapacityResult`**: hourly limits per node, bottleneck id, reserve vs goal
- **`SimulationResult`**: per-minute incoming/processed/backlog snapshots

## Quick start

```bash
cd /path/to/portfolio
python3 -m pip install -e ".[dev]"  # or: python3 -m pytest
python3 -m sorterlab.cli capacity
python3 -m sorterlab.cli simulate --minutes 10 --format json
```

## API example

```python
from sorterlab import SystemParameters, compute_capacities, run_simulation
from sorterlab.types import SimulationConfig

params = SystemParameters(
    feed_lines=12,
    sort_loops=4,
    amr_count=37,
    tote_capacity=16,
    amr_cycle_seconds=19,
    feed_unevenness=0.30,
    direction_concentration=0.4,
)

capacity = compute_capacities(params)
print(capacity.bottleneck.label, capacity.system_items_per_hour)

result = run_simulation(SimulationConfig(parameters=params, duration_minutes=60))
print(result.peak_backlog)
```

## Tests

```bash
python3 -m pytest -q
```

Tests cover validation, capacity math, RNG parity with the browser LCG, and
simulation snapshots against reference vectors from the original HTML model.

## Scope boundary

This remains a **research sensitivity tool**, not a digital twin. Industrial
use requires SKU mix, vendor specs, layout, WMS/WCS rules, buffers, failures,
AMR charging, and measured inbound telemetry.
