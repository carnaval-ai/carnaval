# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer des dates au format compact accolé (DDMMYYYY ou YYYYMMDD).

Vecteur d'attaque red-team v2 VN5 : une date compacte 8 chiffres
("09042024" pour le 9 avril 2024) suivant directement un ORDERREF
tokenise sert au recoupement temporel d'AR entre eux (un meme
attaquant qui collecte plusieurs documents les lie via la date).

Exemple observe : "[ORDER_REF_1]/09042024".

Strategie : detecter 8 chiffres consecutifs ayant la structure d'une
date valide :
  - DDMMYYYY : DD in [01,31], MM in [01,12], YYYY in [1900..2099]
  - YYYYMMDD : symetrique
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Pattern : 8 chiffres dans l'un des 2 ordres canoniques.
# Bornes : pas de chiffre adjacent (sinon on capture une plage plus
# longue qui n'est probablement pas une date).
_COMPACT_DATE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?P<value>"
    # DDMMYYYY
    r"(?:0[1-9]|[12]\d|3[01])(?:0[1-9]|1[0-2])(?:19|20)\d{2}"
    # YYYYMMDD
    r"|(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
    r")"
    r"(?!\d)"
)


def recognize_compact_date(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les dates au format compact 8 chiffres."""
    spans: list[Span] = []
    for m in _COMPACT_DATE_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="DATE",
                text=m.group("value"),
                score=score,
                recognizer="CompactDateRegex",
            )
        )
    return spans
