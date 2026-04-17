"""CLI error handling and logging-mode tests."""

import json
import signal
from unittest.mock import patch

from loguru import logger
import pytest
from typer.testing import CliRunner

from factorise.cli import app
from factorise.cli import configure_logging
from factorise.cli import handle_signal
from factorise.core import FactorisationError

CLI_RUNNER: CliRunner = CliRunner()
CLI_INPUT: str = "123"
SIMULATION_VAL: str = "Simulation"


def test_cli_handle_signal() -> None:
    with patch("sys.exit") as mock_exit:
        handle_signal(signal.SIGINT, None)
        mock_exit.assert_called_with(0)


def test_cli_logging_configuration_verification() -> None:
    configure_logging("DEBUG")
    configure_logging("warning")


def test_cli_error_handling_type_error() -> None:
    with patch("factorise.cli.factorise", side_effect=TypeError(SIMULATION_VAL)):
        result = CLI_RUNNER.invoke(app, [CLI_INPUT])
        assert result.exit_code == 1
        assert "Input Error" in result.output


def test_cli_error_handling_runtime_error() -> None:
    with patch("factorise.cli.factorise", side_effect=FactorisationError(SIMULATION_VAL)):
        result = CLI_RUNNER.invoke(app, [CLI_INPUT])
        assert result.exit_code == 1
        assert "Runtime Error" in result.output


def test_cli_error_handling_invalid_log_level() -> None:
    result = CLI_RUNNER.invoke(app, [CLI_INPUT, "--log-level", "TRACE"])
    assert result.exit_code == 1
    assert "Configuration Error" in result.output


def test_cli_error_handling_invalid_log_format() -> None:
    result = CLI_RUNNER.invoke(app, [CLI_INPUT, "--log-format", "yaml"])
    assert result.exit_code == 1
    assert "Configuration Error" in result.output


def test_json_logging_output_shape(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FACTORISE_REQUEST_ID", "req-env")
    configure_logging("INFO", "json")
    logger.bind(correlation_id="corr-1", trace_id="trace-1").info("json-shape-check")
    payload = json.loads(capsys.readouterr().err.strip().splitlines()[-1])

    assert payload["message"] == "json-shape-check"
    assert payload["request_id"] == "req-env"
    assert payload["correlation_id"] == "corr-1"
    assert payload["trace_id"] == "trace-1"
    for field in (
        "timestamp",
        "level",
        "logger",
        "module",
        "function",
        "line_number",
        "process_id",
        "thread_id",
    ):
        assert field in payload
    assert "span_id" not in payload
    assert "session_id" not in payload


def test_json_logging_exception_payload(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("ERROR", "json")
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("json-exception-check")
    payload = json.loads(capsys.readouterr().err.strip().splitlines()[-1])

    assert payload["message"] == "json-exception-check"
    assert "exception" in payload
    assert payload["exception"]["type"] == "ValueError"
    assert payload["exception"]["message"] == "boom"
    assert "stacktrace" in payload["exception"]


def test_cli_error_handling_value_error() -> None:
    with patch("factorise.cli.factorise", side_effect=ValueError(SIMULATION_VAL)):
        result = CLI_RUNNER.invoke(app, [CLI_INPUT])
        assert result.exit_code == 1
        assert "Value Error" in result.output
