# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Logging structure avec garde-fou anti-fuite.

Principe : un logger structlog standard, plus un filtre qui interdit toute
journalisation contenant des cles a haut risque (`original`, `raw_text`, `mapping`).
Si une telle cle apparait, sa valeur est remplacee par `<REDACTED>` avant emission.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

# Cles dont la valeur ne doit JAMAIS apparaitre dans les logs.
SENSITIVE_KEYS = frozenset(
    {
        "original",
        "raw_text",
        "raw",
        "text",
        "mapping",
        "vault",
        "vault_contents",
        "password",
        "secret",
        "forward",
        "backward",
    }
)


def _redact_sensitive(
    logger, method_name, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Processor structlog : remplace les valeurs sensibles par <REDACTED>."""
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "<REDACTED>"
    return event_dict


def configure_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Configure structlog au niveau global.

    Args:
        level: 'DEBUG', 'INFO', 'WARNING', 'ERROR'.
        json_format: True -> sortie JSON (prod). False -> sortie console lisible.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_sensitive,  # garde-fou anti-fuite
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "carnaval") -> structlog.BoundLogger:
    """Obtient un logger structure (configure_logging() doit avoir ete appele)."""
    return structlog.get_logger(name)
