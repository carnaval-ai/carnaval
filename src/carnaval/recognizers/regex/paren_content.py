# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer du contenu entre parentheses dans les designations produit.

Vecteur d'attaque red-team v2 V11 (finition) : le client final dans
un commentaire de ligne produit ("PINCEAU (A2569 - Renault G)") est
partiellement tokenise ("Renault" devient [ORG_1]) mais le `G` final
ou le code "A2569" survivent. L'attaquant recompose la chaine
supply : emetteur -> destinataire -> client final.

Strategie : masquer TOUT le contenu entre parentheses lorsque celui-ci
contient au moins un mot avec une majuscule de 3+ chars (indicateur de
nom propre / acronyme). Le span couvre les parentheses incluses.

Anti-faux-positifs :
  - parentheses contenant uniquement chiffres / unites ("(jour)",
    "(3 m)", "(5 kg)") - laissees en clair (metier)
  - parentheses < 4 chars - laissees ("(1)", "(a)")
  - parentheses contenant des sigles courts isoles ("(USB)", "(IP67)",
    "(SAS)", "(EUR)") - laissees car sigles produit/standard, pas PII
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Pattern : contenu entre parentheses, 4-120 chars.
_PAREN_PATTERN = re.compile(r"\(([^)\n]{4,120})\)")

# Sigles techniques/metiers a NE PAS masquer (acronymes produit
# standardises). Tous courts (<=6 chars).
_TECHNICAL_ACRONYMS = frozenset({
    "USB", "USB-C", "USB-A", "USB2", "USB3", "USB-3",
    "PWM", "PNP", "NPN", "PLC", "API", "IO", "I/O",
    "IP54", "IP55", "IP65", "IP66", "IP67", "IP68", "IP69",
    "RoHS", "REACH", "ATEX", "IECEx", "UL", "CSA", "CE",
    "DC", "AC", "RGB", "LED", "OLED", "LCD", "TFT",
    "PCB", "PCBA", "SMT", "BGA", "QFN", "DIP",
    "SCH", "FR4", "FR-4",
    "SAS", "SARL", "SA", "GmbH", "Ltd", "LLC", "Inc", "SpA",
    "PME", "PMI", "ETI",
    "EUR", "USD", "GBP", "CHF", "JPY", "CNY", "RMB",
    "HT", "TTC", "TVA", "VAT", "GST",
    "PME", "PMI", "ASCII", "UTF", "JSON", "XML", "CSV", "PDF",
    "MAX", "MIN", "STD", "STDARD", "PRO", "EU",
    "HP", "FR", "DE", "EN", "ES", "IT", "PT", "NL", "BE",
    "CH", "US", "USA", "UK", "JP", "CN", "KR", "TR", "PL",
    "CZ", "BG", "IT", "ES", "PT", "DE",
    "OK", "OKAY",
    "PCS", "PCE", "KG", "G", "MG", "L", "ML", "M", "MM", "CM",
    "KM", "M3", "L/MIN",
    "RAL", "DIN", "ISO", "EN", "NF", "AFNOR",
    "HZ", "KHZ", "MHZ", "V", "MV", "KV", "A", "MA", "W", "KW", "MW",
    "NEF", "NEUF",
    "NB", "NB.", "REF", "REF.",
    "Y", "N", "NIL",  # short single-letter answers
    "SAV", "SAR",
    "RG", "TG",  # rotation / translation
})


def _has_distinctive_capitalized_word(content: str) -> bool:
    """True si le contenu contient un mot avec une majuscule de 4+ chars
    qui n'est PAS dans la liste des acronymes techniques connus."""
    # Tokenise sur espaces / ponctuation
    tokens = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\-]+", content)
    for tok in tokens:
        # Acronyme connu : skip
        if tok in _TECHNICAL_ACRONYMS or tok.upper() in _TECHNICAL_ACRONYMS:
            continue
        # Mot debutant par majuscule, au moins 3 chars (titlecase ou CAPS).
        if len(tok) >= 3 and tok[0].isupper():
            # Si tout en majuscules ET <= 4 chars : probable acronyme
            # generique - on tolere (ex "AML" comme code interne fournisseur
            # est ambigu, mais MOINS distinctif qu'un mot title-case).
            # On ne masque que si :
            #   - tout en CAPS de 5+ chars (acronyme distinctif type
            #     "RENAULT", "STELLANTIS")
            #   - OU titlecase 4+ chars (nom propre type "Renault", "Bosch")
            if tok.isupper() and len(tok) >= 5:
                return True
            if not tok.isupper() and len(tok) >= 4:
                return True
    return False


def recognize_paren_content(text: str, score: float = 0.8) -> list[Span]:
    """Detecte le contenu entre parentheses contenant un mot distinctif.

    Le span couvre les parentheses ET leur contenu (pour que le
    masquage final soit propre : `(...)` -> `[COMMENT_n]`).

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Liste de Span de type COMMENT.
    """
    spans: list[Span] = []
    for m in _PAREN_PATTERN.finditer(text):
        inner = m.group(1)
        if not _has_distinctive_capitalized_word(inner):
            continue
        # Span couvre la parenthese ouvrante + contenu + fermante.
        spans.append(
            Span(
                start=m.start(), end=m.end(),
                entity_type="COMMENT",
                text=m.group(0),
                score=score,
                recognizer="ParenContentRegex",
            )
        )
    return spans
