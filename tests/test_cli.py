"""Tests for factorise.cli using only standard library."""

import dataclasses
import sys
from io import StringIO

import pytest

from factorise.cli import display_factors
from factorise.cli import display_prime
from factorise.cli import main
from factorise.core import FactorisationResult


@dataclasses.dataclass(frozen=True)
class _Result(FactorisationResult):
    """Minimal fake FactorisationResult for testing."""
    original: int
    sign: int = 1
    factors: list[int] = dataclasses.field(default_factory=list)
    powers: dict[int, int] = dataclasses.field(default_factory=dict)
    is_prime: bool = False


def _run_main(argv: list[str]) -> tuple[int, str, str]:
    """Run main() with argv, capture stdout/stderr, return (exit_code, stdout, stderr)."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_buf = StringIO()
    stderr_buf = StringIO()
    try:
        sys.stdout = stdout_buf
        sys.stderr = stderr_buf
        try:
            main(argv)
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1
        return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


class TestCLIDisplay:
    def test_display_prime(self, capsys: pytest.CaptureFixture[str]) -> None:
        display_prime(97)
        out = capsys.readouterr().out
        assert "97" in out
        assert "prime" in out.lower()

    def test_display_factors(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = _Result(original=12, factors=[2, 3], powers={2: 2, 3: 1}, is_prime=False)
        display_factors(result, verbose=False)
        out = capsys.readouterr().out
        assert "12" in out
        assert "2" in out
        assert "3" in out

    def test_display_factors_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = _Result(original=12, factors=[2, 3], powers={2: 2, 3: 1}, is_prime=False)
        display_factors(result, verbose=True)
        out = capsys.readouterr().out
        assert "2^2" in out or "2" in out


class TestCLIMain:
    def test_cli_prime_shows_panel(self) -> None:
        exit_code, stdout, stderr = _run_main(["97"])
        assert exit_code == 0
        assert "prime" in stdout.lower()

    def test_cli_prime_large(self) -> None:
        exit_code, stdout, stderr = _run_main(["1000000007"])
        assert exit_code == 0
        assert "prime" in stdout.lower()

    def test_cli_composite_shows_factors(self) -> None:
        exit_code, stdout, stderr = _run_main(["12"])
        assert exit_code == 0
        assert "2" in stdout
        assert "3" in stdout

    def test_cli_composite_shows_exponents(self) -> None:
        exit_code, stdout, stderr = _run_main(["12"])
        assert exit_code == 0
        assert "2" in stdout

    def test_cli_large_composite(self) -> None:
        exit_code, stdout, stderr = _run_main(["123456789"])
        assert exit_code == 0

    def test_cli_verbose_shows_expression(self) -> None:
        exit_code, stdout, stderr = _run_main(["12", "--verbose"])
        assert exit_code == 0
        assert "*" in stdout

    def test_cli_short_verbose_flag(self) -> None:
        exit_code, stdout, stderr = _run_main(["12", "-v"])
        assert exit_code == 0
        assert "*" in stdout

    def test_cli_zero(self) -> None:
        exit_code, stdout, stderr = _run_main(["0"])
        assert exit_code == 0

    def test_cli_one(self) -> None:
        exit_code, stdout, stderr = _run_main(["1"])
        assert exit_code == 0

    def test_cli_two(self) -> None:
        exit_code, stdout, stderr = _run_main(["2"])
        assert exit_code == 0
        assert "prime" in stdout.lower()

    def test_cli_help_exits_zero(self) -> None:
        exit_code, stdout, stderr = _run_main(["--help"])
        assert exit_code == 0

    def test_cli_missing_argument_exits_nonzero(self) -> None:
        exit_code, stdout, stderr = _run_main([])
        assert exit_code != 0

    def test_cli_non_integer_argument_exits_nonzero(self) -> None:
        exit_code, stdout, stderr = _run_main(["abc"])
        assert exit_code != 0

    def test_cli_float_argument_exits_nonzero(self) -> None:
        exit_code, stdout, stderr = _run_main(["3.14"])
        assert exit_code != 0

    def test_cli_negative_composite_exit_nonzero(self) -> None:
        exit_code, stdout, stderr = _run_main(["-12"])
        assert exit_code == 0

    def test_cli_negative_prime_exit_nonzero(self) -> None:
        exit_code, stdout, stderr = _run_main(["-13"])
        assert exit_code == 0

    def test_cli_verbose_negative(self) -> None:
        exit_code, stdout, stderr = _run_main(["-12", "--verbose"])
        assert exit_code == 0
