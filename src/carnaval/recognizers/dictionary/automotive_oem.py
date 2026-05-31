# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de constructeurs automobiles et equipementiers Tier-1.

Detecte les mentions de constructeurs (Renault, Toyota, Stellantis...)
et d'equipementiers (Bosch, Continental, ZF, Hitachi...) dans
le texte. Le dictionnaire est universel (independant de la langue du
document) car les noms d'entreprises restent stables a travers les
langues - "Renault" s'ecrit "Renault" en francais, anglais, allemand,
espagnol, etc.

Cas d'usage typique :
    - Commentaire libre dans une designation produit :
      "PINCEAU ABRASIF (A2569 - Renault G)"
    - Mention dans une liste de references client :
      "Compatible BMW, Mercedes, Audi"
    - Pied de page avec accreditations :
      "Fournisseur agree par Stellantis et Volkswagen"

La detection est :
    - case-insensitive (Renault, RENAULT, renault, ReNaUlT)
    - tolerante aux accents (Citroen / Citroën, Skoda / Škoda)
    - respect des bords de mot (ne matche pas "Fordism" pour "Ford")
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from carnaval.core.span import Span
from carnaval.recognizers.base import build_alternation_pattern, regex_to_spans

# Le dictionnaire est universel : un seul fichier independant de la langue.
_DICT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data" / "dictionaries" / "automotive_oem" / "universal.txt"
)


@lru_cache(maxsize=1)
def _automotive_oem_pattern() -> re.Pattern[str] | None:
    """Compile le pattern d'alternance des constructeurs / equipementiers.

    Mise en cache : compile une fois, reutilise sur tous les documents.
    """
    if not _DICT_PATH.exists():
        return None
    with open(_DICT_PATH, encoding="utf-8") as f:
        entries = [
            line.strip()
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if not entries:
        return None
    return build_alternation_pattern(
        entries,
        case_sensitive=False,
        word_boundary=True,
        tolerant_accents=True,
    )


def recognize_automotive_oem(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les mentions de constructeurs auto et equipementiers Tier-1.

    Le span produit est de type `ORGANIZATION` (pas un type dedie) pour
    rester compatible avec le placeholder `[ORG_n]` deja utilise dans le
    pipeline : un nom de constructeur dans le texte est masque comme
    n'importe quelle autre organisation.

    Args:
        text: texte source.
        score: confiance (defaut 0.85 - signature de dictionnaire forte).

    Returns:
        Liste de Span de type ORGANIZATION.
    """
    pattern = _automotive_oem_pattern()
    if pattern is None:
        return []
    return regex_to_spans(
        pattern,
        text,
        entity_type="ORGANIZATION",
        recognizer="AutomotiveOemDict",
        score=score,
    )
