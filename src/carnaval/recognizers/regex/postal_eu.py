# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Codes postaux internationaux (UE) avec formats fermes univoques.

Vecteur d'attaque red-team V5 : fragments d'adresse internationale
laisses en clair (ex code postal portugais "1050-061") permettent
d'identifier le fournisseur via les annuaires entreprises etrangers.

Strategie : detecter uniquement les formats AVEC SEPARATEUR DISTINCTIF
(tiret pour PT/PL, lettres pour UK/NL, espace interne pour CZ). Les
formats 4-5 chiffres simples (DE/ES/IT/BE) sont laisses aux patterns
address/* par langue qui exigent CP+ville sur la meme ligne (plus
robuste contre les faux positifs).
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Portugal : NNNN-NNN (4+3 chiffres + tiret obligatoire).
# Lookbehind/ahead etendu : exclut contexte alphanumerique pour eviter
# les faux positifs dans des refs produit (ex : "E1234-567X").
_PT_POSTAL_PATTERN = re.compile(
    r"(?<![\w-])(?P<v>\d{4}-\d{3})(?![\w-])"
)

# Royaume-Uni : "A9 9AA" / "AA9 9AA" / "A9A 9AA" / "AA9A 9AA".
_UK_POSTAL_PATTERN = re.compile(
    r"(?<![A-Z0-9])"
    r"(?P<v>[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})"
    r"(?![A-Z0-9])"
)

# Pologne : NN-NNN (2+3 + tiret). Lookbehind/ahead etendu pour eviter
# les matches dans des refs produit (ex : "E02-139G-K18" -> "02-139"
# faux positif observe sur Mesureur).
_PL_POSTAL_PATTERN = re.compile(
    r"(?<![\w-])(?P<v>\d{2}-\d{3})(?![\w-])"
)

# Pays-Bas : "9999 AA" (4 chiffres + espace + 2 lettres maj).
_NL_POSTAL_PATTERN = re.compile(
    r"(?<![\dA-Z])(?P<v>\d{4}\s?[A-Z]{2})(?![A-Z0-9])"
)

# Republique tcheque : NNN NN (3+2 avec espace OBLIGATOIRE).
_CZ_POSTAL_PATTERN = re.compile(
    r"(?<![\d])(?P<v>\d{3}\s\d{2})(?![\d])"
)


_PATTERNS = [
    (_PT_POSTAL_PATTERN, "PT"),
    (_UK_POSTAL_PATTERN, "UK"),
    (_PL_POSTAL_PATTERN, "PL"),
    (_NL_POSTAL_PATTERN, "NL"),
    (_CZ_POSTAL_PATTERN, "CZ"),
]


def recognize_postal_eu(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les codes postaux EU a format ferme univoque (PT/UK/PL/NL/CZ).

    Les CP 4-5 chiffres simples (DE/ES/IT/BE) sont laisses aux patterns
    address/* par langue (CP+ville sur meme ligne) - plus robuste.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Liste de Span de type LOCATION.
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()
    for pat, country in _PATTERNS:
        for m in pat.finditer(text):
            start, end = m.span("v")
            if (start, end) in seen:
                continue
            seen.add((start, end))
            spans.append(
                Span(
                    start=start, end=end,
                    entity_type="LOCATION",
                    text=m.group("v"),
                    score=score,
                    recognizer="PostalEuRegex",
                    metadata={"country": country},
                )
            )
    return spans
