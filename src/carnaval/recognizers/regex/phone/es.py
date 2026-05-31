# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer telephones Espagne / hispanoamerique.

Formats couverts :
    +34 91 123 45 67           Espagne fixe (Madrid)
    91 123 45 67
    +34 612 34 56 78           Espagne mobile
    612345678
    +52 55 1234 5678           Mexico
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Espagne : +34 puis 9 chiffres groupes 3-3-3 ou 2-3-2-2
PHONE_ES_PATTERN = re.compile(
    r"(?<![\w])"
    r"(?:\+34\s?)?"
    r"[6789]\d{2}[\s\-]?\d{2,3}[\s\-]?\d{2,3}[\s\-]?\d{0,2}"
    r"(?![\w])"
)

# Mexique / Amerique latine
PHONE_LATAM_PATTERN = re.compile(
    r"(?<![\w])"
    r"\+(?:52|54|55|56|57|58|51)\s?"
    r"\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
    r"(?![\w])"
)


def recognize_phone_es(text: str, score: float = 0.8) -> list[Span]:
    return regex_to_spans(
        PHONE_ES_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhoneEsRegex",
        score=score,
    ) + regex_to_spans(
        PHONE_LATAM_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhoneLatamRegex",
        score=score,
    )
