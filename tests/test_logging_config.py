import json
import logging
import os
import subprocess
import sys

from decrochage.logging_config import JsonLogFormatter, configure_json_logger


def test_json_formatter_merges_structured_event() -> None:
    record = logging.LogRecord(
        name="decrochage.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='{"event":"proof","request_id":"req-1"}',
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["event"] == "proof"
    assert payload["request_id"] == "req-1"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "decrochage.test"
    assert payload["timestamp"].endswith("+00:00")


def test_logger_configuration_is_idempotent() -> None:
    logger = configure_json_logger("decrochage.test.idempotent")
    configured_handlers = len(logger.handlers)

    assert configure_json_logger("decrochage.test.idempotent") is logger
    assert len(logger.handlers) == configured_handlers
    assert logger.propagate is False


def test_cli_import_survives_a_legacy_console_encoding() -> None:
    """Importing the CLI must make emoji-bearing output safe to print.

    MLflow 3.15 prints run links prefixed with emoji. On a Windows console
    (cp1252) that raises `UnicodeEncodeError` from inside `mlflow.end_run`, so a
    training command fails *after* recording its run. `cli._configure_stdio`
    forces UTF-8 on stdout/stderr; this test pins that behaviour.

    A subprocess is required: the encoding of a stream is decided when the
    interpreter starts, and pytest has already replaced `sys.stdout` in-process.
    """
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    script = (
        "import decrochage.cli\n"
        "import sys\n"
        "assert sys.stdout.encoding.lower().replace('-', '') == 'utf8', sys.stdout.encoding\n"
        "print('\\U0001f3c3 View run')\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    assert "UnicodeEncodeError" not in result.stderr
    assert "View run" in result.stdout
