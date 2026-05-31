# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer nombres espanoles / latinoamericanos.

Cobertura :
    Sr. Garcia
    Sra. Maria Lopez
    D. Juan Perez            (Don)
    Dna. Ana Martinez        (Dona)
    Atencion: Carlos Sanchez
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

TITLE_ES_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:Sr\.?|Sra\.?|Srta\.?|Sres\.?|Don|Dn\.?|Dona|Dna\.?|"
    r"D\.|Da\.|Dr\.?|Dra\.?|Lic\.?|Ing\.?|Prof\.?)"
    r"\s+[A-ZÁÉÍÓÚÑ][A-Za-zàáéíóúñ\-']{1,30}"
    r"(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zàáéíóúñ\-']{1,30}){0,3}"
)

PERSON_CONTEXT_KEYWORDS_ES = (
    "contacto",
    "atencion",
    "atte",
    "atentamente",
    "responsable",
    "encargado",
    "vendedor",
    "comercial",
    "saludos cordiales",
    "de:",
    "para:",
)

_PERSON_CAPITALIZE_BIGRAM_ES = re.compile(
    r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,15}\s+" r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,15}\b"
)


def recognize_title_es(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        TITLE_ES_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="TitleEsRegex",
        score=score,
    )


def recognize_contextual_person_es(text: str, score: float = 0.75) -> list[Span]:
    spans: list[Span] = []
    window = 40
    for m in _PERSON_CAPITALIZE_BIGRAM_ES.finditer(text):
        start = m.start()
        before = text[max(0, start - window) : start].lower()
        if any(kw in before for kw in PERSON_CONTEXT_KEYWORDS_ES):
            spans.append(
                Span(
                    start=start,
                    end=m.end(),
                    entity_type="PERSON",
                    text=m.group(0),
                    score=score,
                    recognizer="ContextualPersonEsRegex",
                )
            )
    return spans


def recognize_names_es(text: str) -> list[Span]:
    return recognize_title_es(text) + recognize_contextual_person_es(text)
