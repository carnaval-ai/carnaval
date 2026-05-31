# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer ORGANIZATION par suffixe de forme juridique.

Detecte les noms d'entreprises a partir des suffixes de forme juridique
internationaux : GmbH, AG, KG, SE (DE) ; Ltd, LLC, Inc, Corp, PLC (EN) ;
SARL, SAS, SASU, SA, SE (FR) ; S.A., S.L., S.r.l., S.p.A., Lda. (autres).

Le pattern : 1-4 mots capitalises directement suivis du suffixe.
Exemples :
    SupplierOne GmbH
    example electronic gmbh
    CBI Business Services Lda.
    Globex Industries Ltd
    SupplierTwo Systems AG
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Suffixes de forme juridique (multi-langue). Tolere les variantes de casse
# et les points/abreviations. Le `\b` initial/final filtre les sous-chaines.
_LEGAL_SUFFIXES = (
    # Allemagne / Autriche / Suisse alemanique
    "GmbH",
    "AG",
    "AKTIENGESELLSCHAFT",
    "Aktiengesellschaft",
    "KG",
    "OHG",
    "GbR",
    "KGaA",
    "SE",
    # France
    "SARL",
    "SAS",
    "SASU",
    "SA",
    "SCI",
    "EURL",
    "SCS",
    "SNC",
    "S.A.S",
    "S.A.R.L",
    # Royaume-Uni / USA / Inde
    "Ltd",
    "LLC",
    "Inc",
    "Corp",
    "PLC",
    "LLP",
    "LP",
    "Limited",
    "Incorporated",
    "Corporation",
    # Espagne
    "S.A.",
    "S.L.",
    "S.A.U.",
    "SAU",
    # Italie
    "S.r.l.",
    "S.p.A.",
    "Snc",
    "Sas",
    # Portugal / Bresil
    "Lda.",
    "Lda",
    "S/A",
    "Unipessoal",
    # Pays-Bas
    "B.V.",
    "BV",
    "N.V.",
    "NV",
    # International
    "Holdings",
    "Holding",
    "Group",
    "Groupe",
    # Suffixes "business" sans forme juridique stricte mais tres
    # discriminants pour identifier une entreprise.
    "Services",
    "Solutions",
    "Systems",
    "Industries",
    "Technologies",
    "International",
    "Consulting",
    "Partners",
    "Enterprises",
)

# Pattern : 1 a 4 mots Capitalize + suffixe avec word boundaries strictes.
# Le suffixe peut etre case-insensitive (gmbh = GmbH).
_NAME_PART = r"[A-ZÄÖÜÉÈÀÂÊÎÔÛÇÑ][A-Za-zäöüéèàâêîôûçñÄÖÜÉÈÀÂÊÎÔÛÇÑ&\-'.]{1,30}"

# Trie par longueur decroissante : l'alternance regex n'est pas "longest
# match", il faut que "S.A.S" soit teste avant "S.A." pour ne pas couper.
_SUFFIX_ALT = "|".join(
    re.escape(s) for s in sorted(_LEGAL_SUFFIXES, key=len, reverse=True)
)

ORG_SUFFIX_PATTERN = re.compile(
    rf"\b{_NAME_PART}(?:[ \t\-]+{_NAME_PART}){{0,3}}[ \t]+(?i:{_SUFFIX_ALT})\b"
)


def recognize_org_suffix(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les noms d'entreprises par leur suffixe de forme juridique.

    Multilingue par construction : les suffixes couvrent FR/DE/EN/ES/IT/PT/NL.

    Score 0.85 : assez fort car le suffixe est tres discriminant, mais on
    laisse une marge pour les vrais negatifs (suite de mots Capitalize
    suivie accidentellement d'un mot court ressemblant a un suffixe).
    """
    spans: list[Span] = []
    for m in ORG_SUFFIX_PATTERN.finditer(text):
        spans.append(
            Span(
                start=m.start(),
                end=m.end(),
                entity_type="ORGANIZATION",
                text=m.group(0),
                score=score,
                recognizer="OrgSuffixRegex",
            )
        )
    return spans
