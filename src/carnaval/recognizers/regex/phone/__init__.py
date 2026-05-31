# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Dispatcher multilingue pour la reconnaissance de numeros de telephone.

Usage :
    from carnaval.recognizers.regex.phone import recognize_phone
    spans = recognize_phone(text, {"fr", "de"})
"""

from __future__ import annotations

from typing import Callable

from carnaval.core.span import Span

from .be import recognize_phone_be
from .fr import recognize_phone_fr
from .de import recognize_phone_de
from .en import recognize_phone_en, recognize_phone_anglo_international
from .es import recognize_phone_es
from .it import recognize_phone_it
from .pt import recognize_phone_pt
from .international import recognize_phone_international

_RECOGNIZERS_BY_LANG: dict[str, Callable[[str], list[Span]]] = {
    "fr": recognize_phone_fr,
    "de": recognize_phone_de,
    "en": recognize_phone_en,
    "es": recognize_phone_es,
    "it": recognize_phone_it,
    "pt": recognize_phone_pt,
}


def recognize_phone(text: str, languages: set[str]) -> list[Span]:
    """Applique les recognizers telephones pour chaque langue active."""
    spans: list[Span] = []
    for lang in languages:
        reco = _RECOGNIZERS_BY_LANG.get(lang)
        if reco is not None:
            spans.extend(reco(text))
    return spans


__all__ = [
    "recognize_phone",
    "recognize_phone_be",
    "recognize_phone_fr",
    "recognize_phone_de",
    "recognize_phone_en",
    "recognize_phone_anglo_international",
    "recognize_phone_es",
    "recognize_phone_it",
    "recognize_phone_pt",
    "recognize_phone_international",
]
