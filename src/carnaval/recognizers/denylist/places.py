# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Deny-list recognizer for toponyms (specific place names).

Useful for masking city / district / site names that are
sensitive ONLY in a given client context. Example: 'SPRINGFIELD'
is not sensitive in general, but it is your company's address -> must be masked in your documents.
"""

from __future__ import annotations

from carnaval.core.span import Span
from carnaval.recognizers.base import build_alternation_pattern, regex_to_spans


def recognize_places(
    text: str,
    places: list[str],
    entity_type: str = "LOCATION",
    recognizer_name: str = "PlacesDenyList",
    score: float = 0.95,
    case_sensitive: bool = False,
    word_boundary: bool = True,
    tolerant_accents: bool = True,
) -> list[Span]:
    """Detects the listed toponyms.

    tolerant_accents=True (default) allows matching the listed 'Chambery' with
    'Chambéry' in the text (and vice versa). Essential because source lists
    from GeoNames/INSEE are not systematically accented.
    """
    if not places:
        return []
    pattern = build_alternation_pattern(
        places,
        case_sensitive=case_sensitive,
        word_boundary=word_boundary,
        tolerant_accents=tolerant_accents,
    )
    return regex_to_spans(
        pattern,
        text,
        entity_type=entity_type,
        recognizer=recognizer_name,
        score=score,
    )
