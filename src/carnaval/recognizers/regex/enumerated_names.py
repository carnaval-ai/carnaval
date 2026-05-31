# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer des noms ENUMERES apres `MM.` / `Mmes` / `M.` / `Mme`.

Cas couvert : un nom de famille intercale dans une liste apres une
civilite collective, sans civilite individuelle :

    MM. Fischer, Tremeau et Voirin
    Mmes Vandermeer, Brossard et Carvalho

GLiNER detecte parfois le premier nom de la liste mais manque les
suivants (separateurs `, ` et ` et ` peu standards). Resultat : `Fischer`
masque mais `Tremeau` reste en clair, et la liste fuit la PII des autres
personnes citees.

On capture explicitement la civilite collective puis la sequence de noms
qui suit. Chaque nom est masque individuellement (un span par nom).
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Civilite collective FR (MM., Mmes) et anglaise (Messrs., Mss).
_GROUP_TITLE = (
    r"(?:"
    r"MM\.?|Mmes?\.?|Messrs?\.?|Mss?\.?|Misses\.?"
    r")"
)

# Un nom propre : commence par majuscule, accepte tirets et apostrophes
# pour les composes (Martineau-Chassaing, O'Connor).
_NAME = r"[A-ZÀ-Ý][A-Za-zÀ-ÿ\-'’]{2,}"

# Pattern global : civilite collective + liste de noms separes par
# virgule ou "et / and / und".
_GROUP_NAMES_PATTERN = re.compile(
    rf"\b{_GROUP_TITLE}\s+"
    rf"(?P<list>{_NAME}(?:\s*(?:,\s*|\s+et\s+|\s+and\s+|\s+und\s+){_NAME})+)"
)

# Suiveurs qui ne sont pas un nom (pour filtrer les faux positifs sur
# des sous-listes de mots).
_STOP_WORDS = frozenset({
    "et", "and", "und", "ou", "or", "oder",
    "non", "yes", "aucun", "sont",
    "ne", "nee", "née",
})


def recognize_enumerated_names(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les noms enumeres apres une civilite collective.

    Chaque nom de la liste produit son propre Span PERSON, separement.
    Les separateurs (virgules, "et") restent en clair.
    """
    spans: list[Span] = []
    name_re = re.compile(_NAME)
    for m in _GROUP_NAMES_PATTERN.finditer(text):
        list_start = m.start("list")
        list_text = m.group("list")
        for nm in name_re.finditer(list_text):
            tok = nm.group(0)
            if tok.lower() in _STOP_WORDS:
                continue
            abs_start = list_start + nm.start()
            abs_end = list_start + nm.end()
            spans.append(
                Span(
                    start=abs_start,
                    end=abs_end,
                    entity_type="PERSON",
                    text=tok,
                    score=score,
                    recognizer="EnumeratedNamesRegex",
                )
            )
    return spans
