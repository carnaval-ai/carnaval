# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer noms anglophones.

Couvre :
    Mr. John Smith
    Mrs. Jane Doe
    Ms Olivia Brown
    Dr. Patel
    Sir Anthony Hopkins
    To the attention of Mr Smith
    Contact: John Doe
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

TITLE_EN_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:Mr\.?|Mrs\.?|Ms\.?|Miss|Mister|Madam|Madame|Sir|Lady|"
    r"Dr\.?|Prof\.?|Rev\.?|Hon\.?)"
    r"\s+[A-Z][A-Za-z\-']{1,30}"
    r"(?:\s+[A-Z][A-Za-z\-']{1,30}){0,2}"
)

PERSON_CONTEXT_KEYWORDS_EN = (
    "contact",
    "attention",
    "addressed to",
    "regards",
    "salesperson",
    "representative",
    "rep:",
    "rep ",
    "account manager",
    "yours sincerely",
    "best regards",
    "from:",
    "to:",
)

_PERSON_CAPITALIZE_BIGRAM_EN = re.compile(r"\b[A-Z][a-z]{2,15}\s+[A-Z][a-z]{2,15}\b")


def recognize_title_en(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        TITLE_EN_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="TitleEnRegex",
        score=score,
    )


def recognize_contextual_person_en(text: str, score: float = 0.75) -> list[Span]:
    spans: list[Span] = []
    window = 40
    for m in _PERSON_CAPITALIZE_BIGRAM_EN.finditer(text):
        start = m.start()
        before = text[max(0, start - window) : start].lower()
        if any(kw in before for kw in PERSON_CONTEXT_KEYWORDS_EN):
            spans.append(
                Span(
                    start=start,
                    end=m.end(),
                    entity_type="PERSON",
                    text=m.group(0),
                    score=score,
                    recognizer="ContextualPersonEnRegex",
                )
            )
    return spans


def recognize_names_en(text: str) -> list[Span]:
    return recognize_title_en(text) + recognize_contextual_person_en(text)
