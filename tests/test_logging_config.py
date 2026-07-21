import json
import logging

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
