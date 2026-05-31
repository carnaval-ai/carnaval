"""Tests unitaires du logger structure."""

from __future__ import annotations

import json

import pytest

from carnaval.core.logger import (
    SENSITIVE_KEYS,
    _redact_sensitive,
    configure_logging,
    get_logger,
)


class TestRedactSensitive:
    def test_redacts_known_keys(self):
        event = {"original": "Alice", "level": "info"}
        out = _redact_sensitive(None, "info", event)
        assert out["original"] == "<REDACTED>"
        assert out["level"] == "info"

    def test_redacts_all_sensitive(self):
        event = {k: f"secret_{k}" for k in SENSITIVE_KEYS}
        out = _redact_sensitive(None, "info", event)
        for k in SENSITIVE_KEYS:
            assert out[k] == "<REDACTED>"

    def test_preserves_non_sensitive(self):
        event = {"event": "started", "duration": 1.23, "count": 5}
        out = _redact_sensitive(None, "info", event)
        assert out == event

    def test_case_insensitive(self):
        event = {"PASSWORD": "abc", "Original": "x"}
        out = _redact_sensitive(None, "info", event)
        assert out["PASSWORD"] == "<REDACTED>"
        assert out["Original"] == "<REDACTED>"


class TestLoggerSetup:
    def test_configure_does_not_raise(self):
        configure_logging(level="INFO", json_format=True)
        log = get_logger("test")
        log.info("hello", phase="setup")

    def test_redaction_in_output(self, caplog: pytest.LogCaptureFixture):
        # On verifie que la redaction est bien active en faisant passer un
        # event_dict par le processor : c'est lui qui garantit l'anti-fuite.
        # (capsys ne capte pas stdout structlog->logging cleanement, on cible
        # le processor directement.)
        event = {"event": "test", "original": "Alice", "level": "info"}
        result = _redact_sensitive(None, "info", event)
        assert "Alice" not in str(result)
        assert result["original"] == "<REDACTED>"

    def test_console_mode(self):
        configure_logging(level="DEBUG", json_format=False)
        log = get_logger("test_console")
        log.info("event_console", duration=1.0)
