# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Telephones avec prefix international explicite (`+XX`).

Un telephone qui commence par `+` suivi d'un indicatif pays est une PII
quelle que soit la langue du document : on l'attrape independamment du
dispatcher par langue. Cela couvre notamment :

  - les AR EN qui sont detectes comme "fr" parce qu'ils contiennent
    des noms / villes francais ;
  - les AR multilingues (FR/EN sur le meme document) ;
  - les blocs de signature en bas de page contenant un telephone
    d'un autre pays.

Le pattern n'inclut PAS les numeros nationaux sans `+` (ex `06 12 34
56 78`) : ceux-ci restent dispatches par langue car ambigus sans
prefix international (un `06...` peut etre FR, BE, voire un n° de
reference produit).
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Codes pays internationaux supportes. Triees par longueur decroissante
# pour que le regex matche d'abord les +351 / +352 / +353 avant +35.
# Liste etablie a partir des principaux pays clients industriels (UE
# + UK + US + Canada + Amerique latine + Asie principales).
_COUNTRY_CODES = (
    # 3 chiffres (Portugal, Pologne, Pays nordiques, etc.)
    "351", "352", "353", "354", "356", "357", "358", "359",
    "370", "371", "372", "373", "374", "375", "376", "377", "378",
    "380", "381", "382", "383", "385", "386", "387", "389",
    "420", "421", "423",
    # 2 chiffres (Europe principale + Asie + Amerique latine)
    "30", "31", "32", "33", "34", "36", "39",
    "40", "41", "43", "44", "45", "46", "47", "48", "49",
    "51", "52", "53", "54", "55", "56", "57", "58",
    "60", "61", "62", "63", "64", "65", "66",
    "81", "82", "84", "86", "90", "91", "92", "93", "94", "95", "98",
    # 1 chiffre (US/CA)
    "1", "7",
)
_COUNTRY_CODES_RE = "|".join(sorted(_COUNTRY_CODES, key=len, reverse=True))

# Telephone international : `+` (eventuellement espace) + code pays +
# 6 a 13 chiffres significatifs avec separateurs admis (espace, tiret,
# point, saut de ligne, parenthese). Le 1er chiffre nat est 1-9 (pas
# de 0 redondant apres +XX).
PHONE_INTERNATIONAL_PATTERN = re.compile(
    r"(?<!\d)"
    rf"\+\s?(?:{_COUNTRY_CODES_RE})"
    # Entre l'indicatif pays et le premier chiffre national :
    # 0 a 3 separateurs (espace, tiret, point, parenthese fermante,
    # saut de ligne). Cas typique "(+48) 22..." : on a `) ` (2 chars).
    r"[\s\-.()\n]{0,3}(?:\(0\)[\s\-.]?)?"
    r"[1-9](?:[\s\-.()\n]?\d){5,13}"
    r"(?!\d)"
)


def recognize_phone_international(text: str, score: float = 0.85) -> list[Span]:
    """Capture les telephones avec prefix `+XX` international (toute langue).

    Branche en UNIVERSEL : appele quelle que soit la langue detectee. Ne
    duplique pas les patterns nationaux dispatches par langue - le
    dedup se fait au resolve via les chevauchements.
    """
    return regex_to_spans(
        PHONE_INTERNATIONAL_PATTERN,
        text,
        entity_type="PHONE",
        recognizer="PhoneInternationalRegex",
        score=score,
    )
