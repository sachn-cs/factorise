"""Tests for factorise.cli."""

from click.testing import Result as CliResult
from typer.testing import CliRunner

from factorise.cli import app

runner = CliRunner()


def invoke(*args: int | str) -> CliResult:
    """Invoke the CLI app with the given arguments and return the result."""
    return runner.invoke(app, [str(a) for a in args])


def test_cli_prime_shows_panel():
    """Verify functionality of cli_prime_shows_panel."""
    result = invoke(97)
    assert result.exit_code == 0
    assert "prime" in result.output.lower()


def test_cli_prime_large():
    """Verify functionality of cli_prime_large."""
    result = invoke(10**9 + 7)
    assert result.exit_code == 0
    assert "prime" in result.output.lower()


def test_cli_composite_shows_factors():
    """Verify functionality of cli_composite_shows_factors."""
    result = invoke(12)
    assert result.exit_code == 0
    assert "2" in result.output
    assert "3" in result.output


def test_cli_composite_shows_exponents():
    """Verify functionality of cli_composite_shows_exponents."""
    result = invoke(12)
    assert result.exit_code == 0
    assert "2" in result.output


def test_cli_large_composite():
    """Verify functionality of cli_large_composite."""
    result = invoke(123456789)
    assert result.exit_code == 0
    assert "3607" in result.output
    assert "3803" in result.output


def test_cli_verbose_shows_expression():
    """Verify functionality of cli_verbose_shows_expression."""
    result = invoke(12, "--verbose")
    assert result.exit_code == 0
    assert "*" in result.output


def test_cli_verbose_negative():
    """Verify functionality of cli_verbose_negative."""
    result = invoke(-12, "--verbose")
    assert result.exit_code == 2


def test_cli_short_verbose_flag():
    """Verify functionality of cli_short_verbose_flag."""
    result = invoke(12, "-v")
    assert result.exit_code == 0
    assert "*" in result.output


def test_cli_negative_composite_exit_nonzero():
    """Verify functionality of cli_negative_composite_exit_nonzero."""
    result = invoke(-12)
    assert result.exit_code != 0


def test_cli_negative_prime_exit_nonzero():
    """Verify functionality of cli_negative_prime_exit_nonzero."""
    result = invoke(-13)
    assert result.exit_code != 0


def test_cli_zero():
    """Verify functionality of cli_zero."""
    result = invoke(0)
    assert result.exit_code == 0


def test_cli_one():
    """Verify functionality of cli_one."""
    result = invoke(1)
    assert result.exit_code == 0


def test_cli_two():
    """Verify functionality of cli_two."""
    result = invoke(2)
    assert result.exit_code == 0
    assert "prime" in result.output.lower()


def test_cli_help_exits_zero():
    """Verify functionality of cli_help_exits_zero."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert ("factorise" in result.output.lower() or
            "number" in result.output.lower())


def test_cli_missing_argument_exits_nonzero():
    """Verify functionality of cli_missing_argument_exits_nonzero."""
    result = runner.invoke(app, [])
    assert result.exit_code != 0


def test_cli_non_integer_argument_exits_nonzero():
    """Verify functionality of cli_non_integer_argument_exits_nonzero."""
    result = runner.invoke(app, ["abc"])
    assert result.exit_code != 0


def test_cli_float_argument_exits_nonzero():
    """Verify functionality of cli_float_argument_exits_nonzero."""
    result = runner.invoke(app, ["3.14"])
    assert result.exit_code != 0
