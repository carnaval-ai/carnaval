# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Dispatcher multilingue pour la reconnaissance de noms de personnes.

Usage :
    from carnaval.recognizers.regex.names import recognize_names
    spans = recognize_names(text, {"fr", "de"})
"""

from __future__ import annotations

from typing import Callable

from carnaval.core.span import Span

from .fr import recognize_name_patterns as recognize_names_fr
from .de import recognize_names_de
from .en import recognize_names_en
from .es import recognize_names_es
from .it import recognize_names_it
from .pt import recognize_names_pt
from .bg import recognize_names_bg

_RECOGNIZERS_BY_LANG: dict[str, Callable[[str], list[Span]]] = {
    "fr": recognize_names_fr,
    "de": recognize_names_de,
    "en": recognize_names_en,
    "es": recognize_names_es,
    "it": recognize_names_it,
    "pt": recognize_names_pt,
    "bg": recognize_names_bg,
}


def recognize_names(text: str, languages: set[str]) -> list[Span]:
    """Applique les recognizers noms pour chaque langue active."""
    spans: list[Span] = []
    for lang in languages:
        reco = _RECOGNIZERS_BY_LANG.get(lang)
        if reco is not None:
            spans.extend(reco(text))
    return spans


__all__ = [
    "recognize_names",
    "recognize_names_fr",
    "recognize_names_de",
    "recognize_names_en",
    "recognize_names_es",
    "recognize_names_it",
    "recognize_names_pt",
    "recognize_names_bg",
]
