# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer telephones Belgique (+32).

Formats couverts :
    +32 470 18 22 09          (mobile 04XX)
    +32 2 414 88 21           (Bruxelles, 8 chiffres apres +32)
    +32 4 76 12 88 04         (Liege/Hainaut, 9 chiffres)
    0032 470 18 22 09          (international avec 00)
    +32 800 12 12 12           (numero vert / service)
    (+33) 4-76-12-88-15        Note : ce dernier appartient au pattern FR.

Ne capte PAS le format national `0470 18 22 09` (sans +32) : ambigu avec
les telephones FR a 10 chiffres en `0...`. Le recognizer FR couvre ce
format.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Prefixe BE international : +32, 0032, (32)... Le "(0)" intermediaire,
# convention internationale du numero national entre parentheses, est
# tolere mais optionnel.
_PREFIX = (
    r"(?:"
    r"\+[\s.\-]?32[\s.\-]?(?:\(0\)[\s.\-]?)?"
    r"|00[\s.\-]?32[\s.\-]?(?:\(0\)[\s.\-]?)?"
    r"|\(\+?32\)[\s.\-]?(?:\(0\)[\s.\-]?)?"
    r")"
)

# Apres le prefixe, 8 ou 9 chiffres significatifs avec separateurs admis.
# Le 1er chiffre national est 1-9 (pas de 0 redondant apres +32).
PHONE_BE_PATTERN = re.compile(
    r"(?<!\d)" + _PREFIX + r"[1-9](?:[\s.\-]?\d){7,8}(?!\d)"
)


def recognize_phone_be(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        PHONE_BE_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhoneBeRegex",
        score=score,
    )
