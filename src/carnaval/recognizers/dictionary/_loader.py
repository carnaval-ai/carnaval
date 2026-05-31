# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Loader de dictionnaires (1 entree par ligne, UTF-8).

Charge un fichier .txt, filtre les commentaires (#) et les lignes vides,
compile en regex unique avec alternance + word boundaries, et met en cache
le pattern compile.

Format fichier attendu :
    # commentaire optionnel
    Paris
    Lyon
    Marseille
    ...

Le fichier peut comporter jusqu'a quelques dizaines de milliers d'entrees.
La compilation est faite une fois par fichier et mise en cache.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from carnaval.recognizers.base import build_alternation_pattern

# Dictionnaires livres avec le paquet : src/carnaval/data/dictionaries/
_DICT_DIR = Path(__file__).resolve().parents[2] / "data" / "dictionaries"


def load_entries(category: str, language: str) -> list[str]:
    """Charge la liste d'entrees brute pour (category, language).

    Args:
        category: 'cities', 'firstnames', etc.
        language: code ISO 639-1.

    Returns:
        Liste de chaines (vide si fichier absent).
    """
    path = _DICT_DIR / category / f"{language}.txt"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        ]


def load_stoplist(category: str) -> set[str]:
    """Charge le stoplist d'une categorie (mots ambigus a NE PAS matcher).

    Exemple : 'Marie' / 'Pierre' sont a la fois des prenoms et des noms
    communs. On les exclut du dictionnaire pour eviter les faux positifs.
    """
    path = _DICT_DIR / category / "_stoplist.txt"
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {
            line.strip().lower()
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        }


@lru_cache(maxsize=64)
def _compiled_pattern(
    category: str,
    language: str,
    case_sensitive: bool,
    tolerant_accents: bool,
) -> re.Pattern[str] | None:
    """Compile le pattern combine pour (category, language). Mise en cache."""
    entries = load_entries(category, language)
    if not entries:
        return None

    # Filtrer les mots de la stoplist (case insensitive)
    stop = load_stoplist(category)
    entries = [e for e in entries if e.lower() not in stop]

    if not entries:
        return None

    return build_alternation_pattern(
        entries,
        case_sensitive=case_sensitive,
        word_boundary=True,
        tolerant_accents=tolerant_accents,
    )


def get_pattern(
    category: str,
    language: str,
    *,
    case_sensitive: bool = False,
    tolerant_accents: bool = True,
) -> re.Pattern[str] | None:
    """API publique : pattern compile pour (category, language) ou None."""
    return _compiled_pattern(category, language, case_sensitive, tolerant_accents)
