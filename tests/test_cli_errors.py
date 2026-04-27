"""CLI error handling and logging-mode tests — standard library only."""

import signal
from unittest.mock import patch

from factorise.cli import configure_logging
from factorise.cli import handle_signal
from factorise.cli import main


class _Result:
    """Minimal fake FactorisationResult for testing display."""
    __slots__ = ("original", "sign", "factors", "powers", "is_prime")

    def __init__(
        self,
        original: int,
        factors: list[int],
        powers: dict[int, int],
        is_prime: bool,
    ) -> None:
        self.original = original
        self.sign = 1
        self.factors = factors
        self.powers = powers
        self.is_prime = is_prime

    def expression(self) -> str:
        terms = [
            f"{p}^{e}" if e > 1 else str(p)
            for p, e in sorted(self.powers.items())
        ]
        return " * ".join(terms)


def _run_main(argv: list[str]) -> tuple[int, str, str]:
    """Run main() with argv, capture stdout/stderr, return (exit_code, stdout, stderr)."""
    import sys
    from io import StringIO
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


def test_cli_handle_signal() -> None:
    """Verify that handle_signal exits with the correct Unix signal code."""
    with patch("sys.exit") as mock_exit:
        handle_signal(signal.SIGINT, None)
        mock_exit.assert_called_with(130)
    with patch("sys.exit") as mock_exit:
        handle_signal(signal.SIGTERM, None)
        mock_exit.assert_called_with(143)


def test_cli_logging_configuration_verification() -> None:
    """Verify that configure_logging accepts valid levels without error."""
    configure_logging("DEBUG")
    configure_logging("WARNING")


def test_cli_error_handling_type_error() -> None:
    """Verify that TypeError in the core library is caught as an Input Error."""
    with patch("factorise.cli.factorise", side_effect=TypeError("not an int")):
        exit_code, stdout, stderr = _run_main(["123"])
        assert exit_code == 1
        assert "Input Error" in stderr


def test_cli_error_handling_runtime_error() -> None:
    """Verify that FactorisationError is caught as a Runtime Error."""
    from factorise.core import FactorisationError
    with patch(
        "factorise.cli.factorise",
        side_effect=FactorisationError("simulated failure"),
    ):
        exit_code, stdout, stderr = _run_main(["123"])
        assert exit_code == 1
        assert "Runtime Error" in stderr


def test_cli_error_handling_invalid_log_level() -> None:
    """Verify that invalid log levels result in exit code 2 from argparse."""
    exit_code, stdout, stderr = _run_main(["123", "--log-level", "TRACE"])
    # argparse exits with 2 for invalid choice
    assert exit_code == 2


def test_cli_error_handling_value_error() -> None:
    """Verify that ValueError is caught as a Value Error in the CLI."""
    with patch("factorise.cli.factorise", side_effect=ValueError("bad value")):
        exit_code, stdout, stderr = _run_main(["123"])
        assert exit_code == 1
        assert "Value Error" in stderr


def test_cli_main_invalid_input_value() -> None:
    """Hit the ValueError catch block in cli.main (e.g. invalid config from env)."""
    with patch(
        "factorise.cli.FactoriserConfig.from_env",
        side_effect=ValueError("bad config"),
    ):
        exit_code, stdout, stderr = _run_main(["8051"])
        assert exit_code == 1
        assert "Value Error" in stderr


def test_cli_main_type_error_catch() -> None:
    """Hit the TypeError catch block in cli.main."""
    with patch("factorise.cli.factorise", side_effect=TypeError("not an int")):
        exit_code, stdout, stderr = _run_main(["8051"])
        assert exit_code == 1
        assert "Input Error" in stderr