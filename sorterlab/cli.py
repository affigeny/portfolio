"""Command-line interface for the SorterLab throughput model."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from sorterlab.capacity import compute_capacities
from sorterlab.constants import DEFAULT_GOAL_ITEMS_PER_HOUR, DEFAULT_PARAMETERS, DEFAULT_SEED
from sorterlab.simulation import run_simulation
from sorterlab.types import SimulationConfig, SystemParameters
from sorterlab.validation import ValidationError, validate_parameters


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sorterlab",
        description="Parametric throughput model for an automated sorting center (A → B → E).",
    )
    parser.add_argument(
        "command",
        choices=["capacity", "simulate"],
        help="capacity: compute node limits; simulate: run minute-by-minute flow model",
    )

    for name, default in DEFAULT_PARAMETERS.items():
        if isinstance(default, float):
            parser.add_argument(f"--{name.replace('_', '-')}", type=float, default=default)
        else:
            parser.add_argument(f"--{name.replace('_', '-')}", type=int, default=default)

    parser.add_argument(
        "--goal",
        type=float,
        default=DEFAULT_GOAL_ITEMS_PER_HOUR,
        help="Target throughput in items/hour (default: 100000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="RNG seed for reproducible demand noise",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=60,
        help="Simulation length in minutes (simulate command only)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output file path (defaults to stdout)",
    )
    return parser


def _parameters_from_args(args: argparse.Namespace) -> SystemParameters:
    return SystemParameters(
        feed_lines=args.feed_lines,
        sort_loops=args.sort_loops,
        amr_count=args.amr_count,
        tote_capacity=args.tote_capacity,
        amr_cycle_seconds=args.amr_cycle_seconds,
        feed_unevenness=args.feed_unevenness,
        direction_concentration=args.direction_concentration,
    )


def _format_capacity_table(result) -> str:
    lines = [
        "SorterLab capacity analysis",
        "===========================",
        f"Feed (A):     {result.feed_items_per_hour:,.0f} items/h",
        f"Sort (B):     {result.sort_items_per_hour:,.0f} items/h  (rho={result.direction_efficiency:.3f})",
        f"AMR (E):      {result.amr_items_per_hour:,.0f} items/h",
        f"System:       {result.system_items_per_hour:,.0f} items/h",
        f"Bottleneck:   {result.bottleneck.label}",
        f"Reserve/goal: {result.reserve_vs_goal_pct:+.1f}%",
    ]
    return "\n".join(lines)


def _format_simulation_table(result) -> str:
    header = [
        "SorterLab simulation",
        "====================",
        _format_capacity_table(result.capacity),
        "",
        "Minute snapshots:",
        "minute  incoming/min  processed/min  backlog",
    ]
    rows = [
        f"{snap.minute:6d}  {snap.incoming_items_per_minute:11.1f}  "
        f"{snap.processed_items_per_minute:12.1f}  {snap.backlog_items:,.0f}"
        for snap in result.snapshots
    ]
    footer = [
        "",
        f"Peak backlog: {result.peak_backlog:,.0f} items",
        f"Final backlog: {result.final_backlog:,.0f} items",
    ]
    return "\n".join(header + rows + footer)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        params = validate_parameters(_parameters_from_args(args))
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "capacity":
        result = compute_capacities(params, goal_items_per_hour=args.goal)
        if args.format == "json":
            payload = {
                "feed_items_per_hour": result.feed_items_per_hour,
                "sort_items_per_hour": result.sort_items_per_hour,
                "amr_items_per_hour": result.amr_items_per_hour,
                "system_items_per_hour": result.system_items_per_hour,
                "bottleneck": result.bottleneck.value,
                "direction_efficiency": result.direction_efficiency,
                "reserve_vs_goal_pct": result.reserve_vs_goal_pct,
            }
            output = json.dumps(payload, indent=2)
        elif args.format == "csv":
            output = "metric,value\n" + "\n".join(
                f"{key},{value}"
                for key, value in {
                    "feed_items_per_hour": result.feed_items_per_hour,
                    "sort_items_per_hour": result.sort_items_per_hour,
                    "amr_items_per_hour": result.amr_items_per_hour,
                    "system_items_per_hour": result.system_items_per_hour,
                    "bottleneck": result.bottleneck.value,
                    "direction_efficiency": result.direction_efficiency,
                    "reserve_vs_goal_pct": result.reserve_vs_goal_pct,
                }.items()
            )
        else:
            output = _format_capacity_table(result)
    else:
        config = SimulationConfig(
            parameters=params,
            goal_items_per_hour=args.goal,
            seed=args.seed,
            duration_minutes=args.minutes,
        )
        result = run_simulation(config)
        if args.format == "json":
            payload = {
                "capacity": {
                    "feed_items_per_hour": result.capacity.feed_items_per_hour,
                    "sort_items_per_hour": result.capacity.sort_items_per_hour,
                    "amr_items_per_hour": result.capacity.amr_items_per_hour,
                    "system_items_per_hour": result.capacity.system_items_per_hour,
                    "bottleneck": result.capacity.bottleneck.value,
                    "direction_efficiency": result.capacity.direction_efficiency,
                    "reserve_vs_goal_pct": result.capacity.reserve_vs_goal_pct,
                },
                "peak_backlog": result.peak_backlog,
                "final_backlog": result.final_backlog,
                "snapshots": [
                    {
                        "minute": snap.minute,
                        "incoming_items_per_minute": snap.incoming_items_per_minute,
                        "processed_items_per_minute": snap.processed_items_per_minute,
                        "backlog_items": snap.backlog_items,
                    }
                    for snap in result.snapshots
                ],
            }
            output = json.dumps(payload, indent=2)
        elif args.format == "csv":
            lines = [
                [
                    "minute",
                    "incoming_items_per_minute",
                    "processed_items_per_minute",
                    "backlog_items",
                ]
            ]
            lines.extend(
                [
                    snap.minute,
                    f"{snap.incoming_items_per_minute:.6f}",
                    f"{snap.processed_items_per_minute:.6f}",
                    f"{snap.backlog_items:.6f}",
                ]
                for snap in result.snapshots
            )
            from io import StringIO

            buffer = StringIO()
            csv.writer(buffer).writerows(lines)
            output = buffer.getvalue()
        else:
            output = _format_simulation_table(result)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
