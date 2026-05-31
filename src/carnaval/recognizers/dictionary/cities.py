# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de villes par dictionnaire.

Source typique : GeoNames cities500 par pays (telecharge via
scripts/build_dictionaries.py). Permet de masquer toutes les villes
de plus de 500 habitants pour les langues actives.

Score modere (0.7) car risque de faux positifs sur les communes
homophones de noms communs (ex : Bar, Champ, Roche).
"""

from __future__ import annotations

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans
from carnaval.recognizers.dictionary._loader import get_pattern


def recognize_cities(
    text: str,
    languages: set[str],
    score: float = 0.7,
) -> list[Span]:
    """Detecte les villes pour chaque langue active.

    Le dictionnaire est compile depuis assets/dictionaries/cities/{lang}.txt.
    Si le fichier n'existe pas pour une langue, elle est silencieusement ignoree.
    """
    spans: list[Span] = []
    for lang in languages:
        pattern = get_pattern("cities", lang)
        if pattern is None:
            continue
        spans.extend(
            regex_to_spans(
                pattern,
                text,
                entity_type="LOCATION",
                recognizer=f"CityDict_{lang}",
                score=score,
            )
        )
    return spans
