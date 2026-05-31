# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer telephones Allemagne / Autriche / Suisse alemanique.

Formats couverts :
    +49 30 12345678        Berlin
    030 12345678
    +49 (0)89 12345-67     Munich
    089 / 1234 5678
    0049 30 12345678
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Indicatif international (49=DE, 43=AT, 41=CH) ou 0X local.
# La partie ville/operateur fait 2-5 chiffres, suivie de 4-9 chiffres
# pouvant inclure tirets et slashes.
PHONE_DE_PATTERN = re.compile(
    r"(?<![\w])"
    r"(?:\+(?:49|43|41)|0)"
    r"[\s\-/.()]*\(?[0]?\d{2,5}\)?"
    r"[\s\-/.]+"
    r"\d{2,4}[\s\-/.]?\d{2,8}"
    r"(?![\w])"
)


def recognize_phone_de(text: str, score: float = 0.8) -> list[Span]:
    return regex_to_spans(
        PHONE_DE_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhoneDeRegex",
        score=score,
    )
