# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers fiscaux francais : SIREN, SIRET, N TVA intracom.

Conventions :
- SIREN : 9 chiffres (formate par triplets autorise)
- SIRET : 14 chiffres = SIREN + NIC 5 chiffres
- N TVA FR : "FR" + 2 cle + 9 SIREN
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# SIRET 14 chiffres avec separateurs optionnels
SIRET_PATTERN = re.compile(r"\b\d{3}[\s.\-]?\d{3}[\s.\-]?\d{3}[\s.\-]?\d{5}\b")

# SIREN 9 chiffres - (?<!\d) et (?!\d) au lieu de \b strict pour :
# - eviter de matcher 9 chiffres au milieu d'un nombre plus long (commande SAP)
# - mais accepter "RCSChambery308950211" (lettre adjacente OK)
SIREN_PATTERN = re.compile(r"(?<!\d)\d{3}[\s.\-]?\d{3}[\s.\-]?\d{3}(?!\d)")

# N TVA intracom FR : majuscules strictes
VAT_FR_PATTERN = re.compile(r"\bFR\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b")

# Mots-cles imposes a proximite pour valider un SIREN. Sans contexte, un
# numero de 9 chiffres peut etre un numero d'AR fournisseur (faux positif).
SIREN_CONTEXT_KEYWORDS = (
    "SIREN",
    "RCS",
    "RC ",
    "RC.",
    "B.",
    "B ",
    "REGISTRE",
)


def _has_siren_context(text: str, start: int, end: int, window: int = 30) -> bool:
    """True si un mot-cle SIREN/RCS est dans la fenetre AVANT ou APRES le match.

    Couvre les deux formats observes :
    - "SIREN : 308950211"           (mot-cle avant)
    - "315 735 456 RCS NANTES"      (mot-cle apres)
    """
    before = text[max(0, start - window) : start].upper()
    after = text[end : end + window].upper()
    return any(kw in before or kw in after for kw in SIREN_CONTEXT_KEYWORDS)


def recognize_siret(text: str, score: float = 0.9) -> list[Span]:
    return regex_to_spans(
        SIRET_PATTERN,
        text,
        entity_type="SIRET",
        recognizer="SiretRegex",
        score=score,
    )


def recognize_siren(text: str, score: float = 0.7) -> list[Span]:
    """SIREN : exige un mot-cle SIREN/RCS/B. a proximite pour valider."""
    spans: list[Span] = []
    for m in SIREN_PATTERN.finditer(text):
        if not _has_siren_context(text, m.start(), m.end()):
            continue
        spans.append(
            Span(
                start=m.start(),
                end=m.end(),
                entity_type="SIREN",
                text=m.group(0),
                score=score,
                recognizer="SirenRegex",
            )
        )
    return spans


def recognize_vat_fr(text: str, score: float = 0.95) -> list[Span]:
    return regex_to_spans(
        VAT_FR_PATTERN,
        text,
        entity_type="VAT",
        recognizer="VatFrRegex",
        score=score,
    )


def recognize_all_fiscal_fr(text: str) -> list[Span]:
    """Aggregateur : SIRET + SIREN + TVA en un appel."""
    return recognize_siret(text) + recognize_siren(text) + recognize_vat_fr(text)
