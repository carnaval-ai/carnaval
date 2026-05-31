# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer nomi italiani.

Copertura :
    Sig. Rossi
    Sig.ra Maria Bianchi
    Dott. Mario Verdi
    Dr.ssa Anna Romano
    Avv. Giuseppe Conti
    Egr. Sig. Paolo Marini
    Alla cortese attenzione del Sig. Rossi
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

TITLE_IT_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:Sig\.?|Sig\.?ra|Sig\.?na|Sigg\.?|Egr\.?|"
    r"Dott\.?|Dr\.?|Dott\.?ssa|Dr\.?ssa|Prof\.?|Prof\.?ssa|"
    r"Avv\.?|Ing\.?|Arch\.?|Geom\.?|Rag\.?)"
    r"(?:\s+(?:Sig\.?|Dott\.?|Dr\.?))*"
    r"\s+[A-Z][A-Za-zàèéìòù\-']{1,30}"
    r"(?:\s+[A-Z][A-Za-zàèéìòù\-']{1,30}){0,2}"
)

PERSON_CONTEXT_KEYWORDS_IT = (
    "contatto",
    "attenzione",
    "alla cortese attenzione",
    "responsabile",
    "incaricato",
    "commerciale",
    "venditore",
    "cordiali saluti",
    "da:",
    "a:",
    "rif:",
)

_PERSON_CAPITALIZE_BIGRAM_IT = re.compile(
    r"\b[A-Z][a-zàèéìòù]{2,15}\s+[A-Z][a-zàèéìòù]{2,15}\b"
)


def recognize_title_it(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        TITLE_IT_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="TitleItRegex",
        score=score,
    )


def recognize_contextual_person_it(text: str, score: float = 0.75) -> list[Span]:
    spans: list[Span] = []
    window = 40
    for m in _PERSON_CAPITALIZE_BIGRAM_IT.finditer(text):
        start = m.start()
        before = text[max(0, start - window) : start].lower()
        if any(kw in before for kw in PERSON_CONTEXT_KEYWORDS_IT):
            spans.append(
                Span(
                    start=start,
                    end=m.end(),
                    entity_type="PERSON",
                    text=m.group(0),
                    score=score,
                    recognizer="ContextualPersonItRegex",
                )
            )
    return spans


def recognize_names_it(text: str) -> list[Span]:
    return recognize_title_it(text) + recognize_contextual_person_it(text)
