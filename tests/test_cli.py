"""Tests for CLI entry point."""

from __future__ import annotations

from sorterlab.cli import main


def test_cli_capacity_table_exits_zero(capsys):
    code = main(["capacity", "--format", "table"])
    output = capsys.readouterr().out
    assert code == 0
    assert "Bottleneck" in output
    assert "108,000" in output.replace(" ", "")


def test_cli_simulate_json_exits_zero(capsys):
    code = main(["simulate", "--minutes", "2", "--format", "json"])
    output = capsys.readouterr().out
    assert code == 0
    assert '"snapshots"' in output
