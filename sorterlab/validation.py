"""Input validation for SorterLab model parameters."""

from __future__ import annotations

from sorterlab.types import SimulationConfig, SystemParameters

# Slider ranges from sorterlab-simulator.html.
PARAMETER_BOUNDS: dict[str, tuple[int | float, int | float]] = {
    "feed_lines": (4, 24),
    "sort_loops": (1, 8),
    "amr_count": (5, 80),
    "tote_capacity": (6, 40),
    "amr_cycle_seconds": (10, 60),
    "feed_unevenness": (0.0, 0.60),
    "direction_concentration": (0.0, 1.5),
}


class ValidationError(ValueError):
    """Raised when model inputs are outside supported bounds."""


def _check_range(name: str, value: int | float, low: int | float, high: int | float) -> None:
    if not low <= value <= high:
        raise ValidationError(f"{name} must be between {low} and {high}, got {value}")


def validate_parameters(params: SystemParameters) -> SystemParameters:
    """Validate and return parameters unchanged when all checks pass."""
    _check_range("feed_lines", params.feed_lines, *PARAMETER_BOUNDS["feed_lines"])
    _check_range("sort_loops", params.sort_loops, *PARAMETER_BOUNDS["sort_loops"])
    _check_range("amr_count", params.amr_count, *PARAMETER_BOUNDS["amr_count"])
    _check_range("tote_capacity", params.tote_capacity, *PARAMETER_BOUNDS["tote_capacity"])
    _check_range(
        "amr_cycle_seconds",
        params.amr_cycle_seconds,
        *PARAMETER_BOUNDS["amr_cycle_seconds"],
    )
    _check_range(
        "feed_unevenness",
        params.feed_unevenness,
        *PARAMETER_BOUNDS["feed_unevenness"],
    )
    _check_range(
        "direction_concentration",
        params.direction_concentration,
        *PARAMETER_BOUNDS["direction_concentration"],
    )

    if params.feed_lines <= 0:
        raise ValidationError("feed_lines must be positive")
    if params.sort_loops <= 0:
        raise ValidationError("sort_loops must be positive")
    if params.amr_count <= 0:
        raise ValidationError("amr_count must be positive")
    if params.tote_capacity <= 0:
        raise ValidationError("tote_capacity must be positive")
    if params.amr_cycle_seconds <= 0:
        raise ValidationError("amr_cycle_seconds must be positive")

    return params


def validate_simulation_config(config: SimulationConfig) -> SimulationConfig:
    """Validate simulation configuration."""
    validate_parameters(config.parameters)

    if config.goal_items_per_hour <= 0:
        raise ValidationError("goal_items_per_hour must be positive")
    if config.duration_minutes <= 0:
        raise ValidationError("duration_minutes must be positive")
    if config.seed < 0:
        raise ValidationError("seed must be non-negative")

    return config
