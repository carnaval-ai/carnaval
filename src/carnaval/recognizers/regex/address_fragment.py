# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de fragments d'adresse residuels apres tokenisation.

Vecteur d'attaque red-team v2 VN6 : le tokeniseur d'adresse masque le
bloc structure (numero + rue + code postal + ville) mais laisse des
fragments lexicaux :
    "PLANT [ADDR_1]-[ORG][ADDR_2] DE STALINGRAD" - "DE STALINGRAD" en clair
    "Parc d'activites du Val de Moine Ouest"    - "Val de Moine Ouest" en clair
    "SoluTechnic Adis Ouest"                    - "Adis Ouest" en clair

Strategie : detecter les patterns `[DE|du|de la|de l'] <Nom propre>`
juste apres un placeholder d'adresse, OU les patterns `<Mot> Ouest /
Est / Nord / Sud` (toponymie regionale).
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Pattern 1 : fragment "DE <NOM_PROPRE>" apres un placeholder
# d'adresse. Le NOM doit faire >=3 lettres et commencer par une
# majuscule.
_FRAG_AFTER_ADDR = re.compile(
    r"(?:\[(?:ADDR|ORG|SITE)_?\d*\]|\[(?:ADDR|ORG)\])"
    r"[\s\-/]{0,3}"
    r"(?P<value>"
    r"(?:DE|DU|DES|D['’])\s+"
    r"[A-ZÀ-Ý][A-ZÀ-Ý\-'’]{2,30}"
    r"(?:\s+[A-ZÀ-Ý][A-ZÀ-Ý\-'’]{2,30}){0,2}"
    r")\b",
    re.UNICODE,
)

# Pattern 2 : toponymie regionale composee finissant par un point
# cardinal en majuscule (rare en mot commun). "Val de Moine Ouest" /
# "Industrie Ouest" / "Loire Ouest".
_TOPONYM_CARDINAL = re.compile(
    r"\b(?P<value>"
    r"[A-ZÀ-Ý][a-zà-ÿ'’\-]{2,20}"
    r"(?:\s+(?:de\s+|du\s+|des\s+|la\s+|le\s+|d['’]))?"
    r"[A-ZÀ-Ý][a-zà-ÿ'’\-]{2,20}"
    r"(?:\s+[A-ZÀ-Ý][a-zà-ÿ'’\-]{2,20})?"
    r"\s+(?:Ouest|Est|Nord|Sud|OUEST|EST|NORD|SUD)"
    r")\b"
)

# Mots banaux qui peuvent suivre [ADDR] mais ne sont pas des fragments
# d'adresse PII (laissés en clair).
_NOT_A_FRAGMENT = frozenset({
    "DE LIVRAISON",
    "DE FACTURATION",
    "DE COMMANDE",
    "DE PAIEMENT",
    "DE REGLEMENT",
    "DU CLIENT",
    "DE SITE",
    "DE VENTE",
    "DE TRANSPORT",
    "DE GARANTIE",
})


def recognize_address_fragment(text: str, score: float = 0.78) -> list[Span]:
    """Detecte les fragments d'adresse residuels (toponymie post-token).

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Liste de Span de type LOCATION.
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()

    # Pattern 1 : DE <NOM PROPRE> apres [ADDR]
    for m in _FRAG_AFTER_ADDR.finditer(text):
        value = m.group("value").strip()
        if value.upper() in _NOT_A_FRAGMENT:
            continue
        start, end = m.span("value")
        if (start, end) in seen:
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="LOCATION",
                text=value,
                score=score,
                recognizer="AddressFragmentRegex",
            )
        )

    # Pattern 2 : toponymie composee + point cardinal
    for m in _TOPONYM_CARDINAL.finditer(text):
        value = m.group("value").strip()
        # Filtre noise : si commence par mot non-propre comme
        # "Notre Ouest", "Bureau Ouest" - laisse en clair.
        first = value.split()[0].lower()
        if first in {"notre", "votre", "leur", "bureau", "agence",
                     "service", "departement", "direction"}:
            continue
        start, end = m.span("value")
        if (start, end) in seen:
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="LOCATION",
                text=value,
                score=score * 0.95,
                recognizer="AddressFragmentRegex",
            )
        )

    return spans
