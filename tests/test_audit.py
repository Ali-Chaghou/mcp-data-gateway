"""Tests for structured audit logging of tool invocations."""

import logging

import pytest

from mcp_data_gateway import audit

AUDIT_LOGGER = "mcp_data_gateway.audit"


def test_successful_call_emits_one_success_line(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=AUDIT_LOGGER):
        result = audit.audited("search_passengers", {"sex": "female"}, lambda: [1, 2, 3])
    assert result == [1, 2, 3]
    assert len(caplog.records) == 1
    msg = caplog.records[0].message
    assert 'tool="search_passengers"' in msg
    assert 'outcome="success"' in msg
    assert "result_count=3" in msg
    assert '"sex": "female"' in msg


def test_failed_call_emits_error_line_and_reraises(caplog: pytest.LogCaptureFixture) -> None:
    def boom() -> None:
        raise ValueError("bad filter")

    with caplog.at_level(logging.INFO, logger=AUDIT_LOGGER):
        with pytest.raises(ValueError):
            audit.audited("get_passenger", {"passenger_id": 0}, boom)
    msg = caplog.records[0].message
    assert 'outcome="error"' in msg
    assert 'error_type="ValueError"' in msg
    assert "bad filter" not in msg  # message text is not logged, only the type


def test_result_count_for_single_and_none() -> None:
    assert audit._result_count({"a": 1}) == 1
    assert audit._result_count(None) == 0
    assert audit._result_count([1, 2]) == 2


def test_sensitive_and_none_arguments_are_dropped(caplog: pytest.LogCaptureFixture) -> None:
    args = {
        "pclass": 1,
        "sex": None,  # unset filter
        "password": "hunter2",
        "database_url": "postgresql://reader:secret@localhost/agentdata",
        "api_token": "abc123",
    }
    with caplog.at_level(logging.INFO, logger=AUDIT_LOGGER):
        audit.audited("search_passengers", args, lambda: [])
    msg = caplog.records[0].message
    assert '"pclass": 1' in msg
    assert "sex" not in msg  # None values omitted
    for leaked in ("hunter2", "secret", "abc123", "database_url", "password", "api_token"):
        assert leaked not in msg


def test_configure_logging_sets_level_and_single_handler() -> None:
    from mcp_data_gateway.config import Settings

    settings = Settings(
        database_url="postgresql://reader:pw@localhost:5432/agentdata",
        log_level="WARNING",
    )
    logger = logging.getLogger("mcp_data_gateway")
    before = list(logger.handlers)
    try:
        audit.configure_logging(settings)
        audit.configure_logging(settings)  # idempotent: no duplicate handler
        assert logger.level == logging.WARNING
        assert len(logger.handlers) == len(before) + 1
    finally:
        logger.handlers = before
        logger.setLevel(logging.NOTSET)
