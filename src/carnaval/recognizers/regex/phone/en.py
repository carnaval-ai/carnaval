# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer telephones anglophones (UK, US, CA, AU, IE, NZ).

Formats couverts :
    +44 20 7946 0958          UK
    020 7946 0958
    (415) 555-0132            US
    +1 415-555-0132
    1-800-555-0199
    +61 2 9876 5432           AU
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# UK : +44 puis 10 chiffres significatifs (apres trunk 0 supprime), avec
# separateurs admis (espace, tiret, point, saut de ligne PDF). Le pattern
# precedent attendait des groupes \d{3,4} consecutifs, ce qui rate les
# formats "+44 1208 81 47 14" (groupes de 2) qu'on voit massivement dans
# les AR fournisseurs UK. Le format national `0X...` (sans +44) n'est PAS
# capture ici : il chevauche les telephones FR a 10 chiffres.
PHONE_UK_PATTERN = re.compile(
    r"(?<!\d)"
    r"\+\s?44[\s\-.]?(?:\(0\)[\s\-.]?)?"
    r"\d(?:[\s\-.\n]?\d){9}"
    r"(?!\d)"
)

# US/CA : (XXX) XXX-XXXX, XXX-XXX-XXXX, +1 XXX XXX XXXX
PHONE_US_PATTERN = re.compile(
    r"(?<![\w])"
    r"(?:\+1[\s\-.]?)?"
    r"\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}"
    r"(?![\w])"
)

# AU/IE/NZ : +XX prefixe + numero
PHONE_OCE_PATTERN = re.compile(
    r"(?<![\w])"
    r"\+(?:61|353|64)\s?"
    r"\d{1,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
    r"(?![\w])"
)


def recognize_phone_en(text: str, score: float = 0.8) -> list[Span]:
    """Patterns telephones anglophones, y compris US/CA (10 chiffres
    sans prefix qui peuvent chevaucher avec un telephone FR a 10
    chiffres). Branche par le dispatcher quand la langue detectee
    est `en`.
    """
    spans: list[Span] = []
    for pat, name in (
        (PHONE_UK_PATTERN, "PhoneUkRegex"),
        (PHONE_US_PATTERN, "PhoneUsRegex"),
        (PHONE_OCE_PATTERN, "PhoneOceRegex"),
    ):
        spans.extend(
            regex_to_spans(
                pat,
                text,
                entity_type="PHONE",
                recognizer=name,
                score=score,
            )
        )
    return spans


def recognize_phone_anglo_international(
    text: str, score: float = 0.85
) -> list[Span]:
    """Patterns avec prefix international explicite (+44, +61, +353,
    +64). Sans risque de conflit avec d'autres langues (FR, DE...). A
    brancher en universel pour eviter de rater un telephone UK dans un
    doc dont la langue detectee n'est pas `en` (ex: AR EN contenant des
    termes francais).
    """
    spans: list[Span] = []
    for pat, name in (
        (PHONE_UK_PATTERN, "PhoneUkRegex"),
        (PHONE_OCE_PATTERN, "PhoneOceRegex"),
    ):
        spans.extend(
            regex_to_spans(
                pat,
                text,
                entity_type="PHONE",
                recognizer=name,
                score=score,
            )
        )
    return spans
