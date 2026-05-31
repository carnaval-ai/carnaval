# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Deny-list recognizer for recurring person names (employees, contacts)."""

from __future__ import annotations

from carnaval.core.span import Span
from carnaval.recognizers.base import build_alternation_pattern, regex_to_spans


def recognize_people(
    text: str,
    people: list[str],
    entity_type: str = "PERSON",
    recognizer_name: str = "PeopleDenyList",
    score: float = 1.0,
    case_sensitive: bool = False,
    word_boundary: bool = True,
) -> list[Span]:
    """Detects the listed persons."""
    if not people:
        return []
    pattern = build_alternation_pattern(
        people,
        case_sensitive=case_sensitive,
        word_boundary=word_boundary,
    )
    return regex_to_spans(
        pattern,
        text,
        entity_type=entity_type,
        recognizer=recognizer_name,
        score=score,
    )
