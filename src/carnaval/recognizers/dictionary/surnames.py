# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de noms de personne en forme abregee : amorce + nom.

GLiNER detecte mal un nom reduit a une amorce courte suivie d'un nom de
famille (« Y. Hering », « M. AUBERT », « Mme DUPONT ») : la forme est trop
pauvre en contexte. Ce recognizer comble ce trou - en complement de
`CiviliteRegex`, qui couvre « civilite + NOM Prenom » (deux mots).

Principe : le pattern repere une amorce structurelle - une initiale (lettre
majuscule + point) ou une civilite FR (« Mme », « Mlle », « MR ») - suivie
d'un mot. Le mot n'est retenu comme nom que s'il figure dans le dictionnaire
de noms de famille (data/dictionaries/surnames/). Cette validation par
dictionnaire ecarte le bruit du pattern seul (« P. Unitaire », « Mme HT »...).
"""

from __future__ import annotations

import re
from functools import lru_cache

from carnaval.core.span import Span
from carnaval.recognizers.dictionary._loader import load_entries

# Amorce = initiale ("Y.", "M.") ou civilite FR ("Mme", "Mlle", "MR").
# Suivie du nom (groupe 1), capitalise OU tout en majuscules ("Hering",
# "AUBERT") via le flag (?i:) local. Le nom capture est valide ensuite par
# le dictionnaire, ce qui ecarte les faux positifs ("Mme HT", "M. Montant").
# (?<![A-Za-z]) au lieu de \b : tolere l'amorce collee a un chiffre, frequent
# en sortie d'extraction PDF ("0,00M. AUBERT").
_INITIAL_SURNAME = re.compile(
    r"(?<![A-Za-z])(?:[A-Z]\.|Mme\.?|MME\.?|Mlle\.?|MLLE\.?|MR\.?)"
    r"\s*([A-Z](?i:[a-zéèêëàâäîïôöùûüç'\-]+))\b"
)


@lru_cache(maxsize=1)
def _surnames() -> frozenset[str]:
    """Dictionnaire de noms de famille, normalise en minuscules."""
    return frozenset(e.lower() for e in load_entries("surnames", "all"))


def recognize_initial_surname(text: str, score: float = 0.7) -> list[Span]:
    """Detecte les noms en forme « initiale + nom de famille ».

    Le mot suivant l'initiale n'est retenu que s'il appartient au
    dictionnaire de noms de famille, ce qui ecarte les abreviations qui
    ne sont pas des noms.
    """
    surnames = _surnames()
    if not surnames:
        return []
    spans: list[Span] = []
    for m in _INITIAL_SURNAME.finditer(text):
        if m.group(1).lower() in surnames:
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    entity_type="PERSON",
                    text=m.group(0),
                    score=score,
                    recognizer="InitialSurnameDict",
                )
            )
    return spans
