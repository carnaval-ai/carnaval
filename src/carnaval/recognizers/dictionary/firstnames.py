# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de prenoms par dictionnaire.

Source typique :
    FR : INSEE etat civil (jeu de donnees public)
    DE : WikiData / GeoNames forenames
    EN : US Social Security Administration / UK ONS
    ES : INE Espana
    IT : ISTAT

Le score est plus modere (0.6) car beaucoup de prenoms sont des homonymes
de noms communs (Marie, Pierre, Rose en FR). On compense via un stoplist
explicite (assets/dictionaries/firstnames/_stoplist.txt).
"""

from __future__ import annotations

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans
from carnaval.recognizers.dictionary._loader import get_pattern


def recognize_firstnames(
    text: str,
    languages: set[str],
    score: float = 0.6,
) -> list[Span]:
    """Detecte les prenoms pour chaque langue active.

    NB : on emet des Spans PERSON_HINT plutot que PERSON pour les
    distinguer des PERSON forts (contexte clair, civilites). Permet a
    s4_resolve de les arbitrer si un span PERSON plus long les recouvre.
    """
    spans: list[Span] = []
    for lang in languages:
        pattern = get_pattern("firstnames", lang)
        if pattern is None:
            continue
        spans.extend(
            regex_to_spans(
                pattern,
                text,
                entity_type="PERSON",
                recognizer=f"FirstnameDict_{lang}",
                score=score,
            )
        )
    return spans
