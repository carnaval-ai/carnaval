# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de noms bulgares (cyrillique).

Couvertures :
    г-н Иванов
    г-жа Мария Петрова
    г-ца Стоянова
    господин Чен (nom translittere)
    госпожа Лиан Лиюн

Les noms cyrilliques sont en alphabet bulgare (А-Я / а-я). Pour les
noms etrangers translitteres (chinois -> Цай, Чен, Лиан), on accepte
le meme alphabet.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Civilites bulgares + nom propre cyrillique.
# Couvre les formes abregees (г-н, г-жа, г-ца) et completes
# (господин, госпожа, госпожица).
# Nom : 1 a 3 mots commencant par une majuscule cyrillique [А-Я] ou
# tout en majuscules (cas des noms de famille en CAPS, frequent en BG).
TITLE_BG_PATTERN = re.compile(
    r"(?<![А-Яа-я])"
    r"(?:г-н|г-жа|г-ца|господин|госпожа|госпожица)"
    r"(?:\s+(?:г-н|г-жа|г-ца|господин|госпожа|госпожица))*"
    r"\s+[А-Я][А-Яа-я\-']{1,30}"
    # Au plus 1 token supplementaire (= max 2 mots de nom). 3+ tokens
    # aspirent souvent un mot non-PII (ex: "г-н Цай ГУОЦЯН Сметка" ou
    # "г-н Чен Лиу Банкa"). Les noms BG a 3 prenoms sont rares dans
    # un contexte AR.
    r"(?:\s+[А-Я][А-Яа-я\-']{1,30}){0,1}"
)


PERSON_CONTEXT_KEYWORDS_BG = (
    "контакт",                      # contact
    "лице за връзка",                # personne a contacter
    "представител",                  # representant
    "отговорник",                   # responsable
    "продавач",                     # vendeur
    "купувач",                      # acheteur
    "до:",                          # a: (entete email)
    "от:",                          # de:
    "с уважение",                   # cordialement
    "поздрави",                     # salutations
    "управител",                    # gerant / directeur
    "директор",                     # directeur
    "ръководител",                  # responsable / chef
)

_PERSON_CAPITALIZE_BIGRAM_BG = re.compile(
    r"\b[А-Я][а-я]{2,20}\s+[А-Я][а-я]{2,20}\b"
)


def recognize_title_bg(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        TITLE_BG_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="TitleBgRegex",
        score=score,
    )


def recognize_contextual_person_bg(text: str, score: float = 0.75) -> list[Span]:
    spans: list[Span] = []
    window = 40
    for m in _PERSON_CAPITALIZE_BIGRAM_BG.finditer(text):
        start = m.start()
        before = text[max(0, start - window) : start].lower()
        if any(kw in before for kw in PERSON_CONTEXT_KEYWORDS_BG):
            spans.append(
                Span(
                    start=start,
                    end=m.end(),
                    entity_type="PERSON",
                    text=m.group(0),
                    score=score,
                    recognizer="ContextualPersonBgRegex",
                )
            )
    return spans


def recognize_names_bg(text: str) -> list[Span]:
    return recognize_title_bg(text) + recognize_contextual_person_bg(text)
