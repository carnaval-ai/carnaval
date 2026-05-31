# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Dispatcher multilingue pour la reconnaissance d'adresses postales.

Usage :
    from carnaval.recognizers.regex.address import recognize_address
    spans = recognize_address(text, {"fr", "de"})
"""

from __future__ import annotations

from typing import Callable

from carnaval.core.span import Span

from .fr import recognize_address_fr
from .de import recognize_address_de
from .en import recognize_address_en
from .es import recognize_address_es
from .it import recognize_address_it
from .pt import recognize_address_pt
from .bg import recognize_address_bg

_RECOGNIZERS_BY_LANG: dict[str, Callable[[str], list[Span]]] = {
    "fr": recognize_address_fr,
    "de": recognize_address_de,
    "en": recognize_address_en,
    "es": recognize_address_es,
    "it": recognize_address_it,
    "pt": recognize_address_pt,
    "bg": recognize_address_bg,
}


def recognize_address(text: str, languages: set[str]) -> list[Span]:
    """Applique les recognizers adresses pour chaque langue active."""
    spans: list[Span] = []
    for lang in languages:
        reco = _RECOGNIZERS_BY_LANG.get(lang)
        if reco is not None:
            spans.extend(reco(text))
    return spans


__all__ = [
    "recognize_address",
    "recognize_address_fr",
    "recognize_address_de",
    "recognize_address_en",
    "recognize_address_es",
    "recognize_address_it",
    "recognize_address_pt",
    "recognize_address_bg",
]
