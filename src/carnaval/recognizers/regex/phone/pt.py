# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer telefones Portugal / Brasil.

Formats couverts :
    +351 21 1234 5678        Portugal fixe
    21 1234 5678
    +351 91 234 5678         Portugal mobile
    +55 11 91234-5678        Brasil
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Format strict pour eviter les faux positifs sur les numeros de commande
# Portugal : soit avec prefixe +351 explicite, soit avec separateurs visibles
# (point/espace) entre les groupes - jamais un nombre brut a 9 chiffres.
PHONE_PT_PATTERN = re.compile(
    r"(?<![\w])(?:"
    # Avec prefixe pays
    r"\+351\s?[239]\d{1,2}\s?\d{3}\s?\d{3,4}"
    r"|"
    # Sans prefixe mais avec separateurs visibles
    r"[239]\d{1,2}[\s.\-]\d{3,4}[\s.\-]\d{3,4}"
    r")(?![\w])"
)

PHONE_BR_PATTERN = re.compile(
    r"(?<![\w])" r"\+55\s?" r"\(?\d{2}\)?[\s\-]?9?\d{4}[\s\-]?\d{4}" r"(?![\w])"
)


def recognize_phone_pt(text: str, score: float = 0.75) -> list[Span]:
    return regex_to_spans(
        PHONE_PT_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhonePtRegex",
        score=score,
    ) + regex_to_spans(
        PHONE_BR_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhoneBrRegex",
        score=score,
    )
