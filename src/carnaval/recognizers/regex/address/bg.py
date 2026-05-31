# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers d'adresses bulgares (alphabet cyrillique).

Couvertures :
    гр. София, ул. Витоша 5
    бул. България 88
    с. Бистрица, общ. Самоков
    ж.к. Младост, бл. 12, ет. 3, ап. 5
    Код : 1000 София
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Code postal BG : 4 chiffres + ville (caracteres cyrilliques).
# Plage Unicode : U+0400-U+04FF = cyrillique. On accepte aussi
# l'apostrophe interne (rare en BG mais courant en transcription).
POSTAL_CITY_BG_PATTERN = re.compile(
    r"\b\d{4}[ \t]+"
    r"[А-Я][Ѐ-ӿ \t\-'.]{2,60}"
)

# Rues BG : ул. (улица), бул. (булевард), пл. (площад),
# жк / ж.к. (жилищен комплекс), кв. (квартал), бл. (блок),
# гр. (град = ville), с. (село = village), общ. (община).
STREET_BG_PATTERN = re.compile(
    r"(?:ул\.|бул\.|пл\.|ж\.к\.|жк\.|кв\.|бл\.|гр\.|с\.|общ\.)"
    r"\s*"
    r"[А-Яа-я\d][Ѐ-ӿ\d \t\-'.,№]{2,80}"
)

# Suffixes adresse : ет. (etage), ап. (apartement), вх. (entree)
# avec un numero. Souvent en fin d'adresse complete.
APARTMENT_BG_PATTERN = re.compile(
    r"(?:ет\.|вх\.|ап\.)\s*\d+(?:[\s,]*(?:ет\.|вх\.|ап\.)\s*\d+){0,2}"
)


def recognize_address_bg(text: str, score: float = 0.85) -> list[Span]:
    spans: list[Span] = []
    for pat, name in (
        (POSTAL_CITY_BG_PATTERN, "PostalCityBgRegex"),
        (STREET_BG_PATTERN, "StreetBgRegex"),
        (APARTMENT_BG_PATTERN, "ApartmentBgRegex"),
    ):
        spans.extend(
            regex_to_spans(
                pat,
                text,
                entity_type="LOCATION",
                recognizer=name,
                score=score,
            )
        )
    return spans
