# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer nomes portugueses / brasileiros."""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

TITLE_PT_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:Sr\.?|Sra\.?|Srta\.?|Dr\.?|Dra\.?|"
    r"Eng\.?|Engª|Prof\.?|Profª|"
    r"Dom|Dona|D\.)"
    r"\s+[A-ZÁÉÍÓÚÃÕÇ][A-Za-zàáâãéêíóôõúç\-']{1,30}"
    r"(?:\s+[A-ZÁÉÍÓÚÃÕÇ][A-Za-zàáâãéêíóôõúç\-']{1,30}){0,3}"
)

PERSON_CONTEXT_KEYWORDS_PT = (
    "contato",
    "contacto",
    "atencao",
    "atencao de",
    "responsavel",
    "encarregado",
    "vendedor",
    "comercial",
    "atenciosamente",
    "cumprimentos",
    "de:",
    "para:",
)

_PERSON_CAPITALIZE_BIGRAM_PT = re.compile(
    r"\b[A-ZÁÉÍÓÚÃÕÇ][a-zàáâãéêíóôõúç]{2,15}\s+"
    r"[A-ZÁÉÍÓÚÃÕÇ][a-zàáâãéêíóôõúç]{2,15}\b"
)


def recognize_title_pt(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        TITLE_PT_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="TitlePtRegex",
        score=score,
    )


def recognize_contextual_person_pt(text: str, score: float = 0.75) -> list[Span]:
    spans: list[Span] = []
    window = 40
    for m in _PERSON_CAPITALIZE_BIGRAM_PT.finditer(text):
        start = m.start()
        before = text[max(0, start - window) : start].lower()
        if any(kw in before for kw in PERSON_CONTEXT_KEYWORDS_PT):
            spans.append(
                Span(
                    start=start,
                    end=m.end(),
                    entity_type="PERSON",
                    text=m.group(0),
                    score=score,
                    recognizer="ContextualPersonPtRegex",
                )
            )
    return spans


def recognize_names_pt(text: str) -> list[Span]:
    return recognize_title_pt(text) + recognize_contextual_person_pt(text)
