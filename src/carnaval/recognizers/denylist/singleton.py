# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer 'singleton' : toutes les occurrences d'une meme entite recoivent
le meme placeholder, sans index numerique.

Exemple : si on declare une entreprise unique a anonymiser, toutes ses
variantes orthographiques produiront le meme placeholder canonique.
"""

from __future__ import annotations

from carnaval.core.span import Span
from carnaval.recognizers.base import build_alternation_pattern, regex_to_spans


def recognize_singleton(
    text: str,
    variants: list[str],
    entity_type: str = "ORG_SINGLETON",
    recognizer_name: str = "SingletonDenyList",
    score: float = 1.0,
    case_sensitive: bool = False,
    word_boundary: bool = True,
) -> list[Span]:
    """Detecte toutes les variantes d'une entite unique.

    Args:
        text: texte source.
        variants: liste des variantes orthographiques a matcher.
        entity_type: type d'entite affecte aux Spans (defaut ORG_SINGLETON).
        recognizer_name: nom pour audit / dedup.
        score: score Span produit.
        case_sensitive: True pour exiger une casse exacte.
        word_boundary: True pour exiger des limites de mots.

    Returns:
        Liste de Span.
    """
    if not variants:
        return []
    pattern = build_alternation_pattern(
        variants,
        case_sensitive=case_sensitive,
        word_boundary=word_boundary,
        tolerant_accents=True,
    )
    return regex_to_spans(
        pattern,
        text,
        entity_type=entity_type,
        recognizer=recognizer_name,
        score=score,
    )


def recognize_singleton_loose(
    text: str,
    variants: list[str],
    entity_type: str = "ORG_SINGLETON",
    recognizer_name: str = "SingletonLooseDenyList",
    score: float = 0.85,
    min_len: int = 6,
) -> list[Span]:
    """Variante 'tolerante' du singleton : SANS word boundary.

    Permet de matcher une variante meme noyee dans un mot colle (par
    exemple `ACMECORPSAS` dans `GLOBEXACMECORPSAS`, frequent sur
    les PDFs mal extraits ou texte parasite).

    Filtre les variantes < `min_len` chars pour limiter le risque
    de faux positifs.
    """
    candidates = [v for v in variants if len(v) >= min_len]
    if not candidates:
        return []
    pattern = build_alternation_pattern(
        candidates,
        case_sensitive=False,
        word_boundary=False,
        tolerant_accents=True,
    )
    return regex_to_spans(
        pattern,
        text,
        entity_type=entity_type,
        recognizer=recognizer_name,
        score=score,
    )
