# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer telephones Italie / Suisse italophone.

Formats couverts :
    +39 06 12345678              Rome
    06 12345678
    +39 02 1234.5678             Milan
    +39 348 1234567              mobile
    348 1234567
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Italie : +39 puis 9 a 11 chiffres avec separateurs.
PHONE_IT_PATTERN = re.compile(
    r"(?<![\w])"
    r"(?:\+39\s?)?"
    r"0?\d{1,4}[\s\-./]?\d{3,4}[\s\-./]?\d{3,5}"
    r"(?![\w])"
)


def recognize_phone_it(text: str, score: float = 0.75) -> list[Span]:
    return regex_to_spans(
        PHONE_IT_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhoneItRegex",
        score=score,
    )
