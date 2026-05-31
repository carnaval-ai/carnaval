# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer email (RFC 5322 simplifie)."""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Un email peut etre scinde par un saut de ligne : l'extraction PDF renvoie
# a la ligne une adresse trop longue. On tolere donc un \n interne dans le
# DOMAINE. Le ".TLD" final borne le match : il evite d'avaler la ligne
# suivante quand ce n'est pas la suite de l'adresse.
#
# La partie locale, elle, n'admet PAS de \n : la tolerer revenait a happer
# le dernier token de la ligne precedente ("...28 25 08 15\nd.ranchy@..."
# capturait "15\nd.ranchy@..."), un fragment de telephone qui evincait
# ensuite le vrai span PHONE en resolution.
EMAIL_PATTERN = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+"
    r"@[a-zA-Z0-9.\-]+(?:\n[a-zA-Z0-9.\-]+)?\.[a-zA-Z]{2,}\b"
)


def recognize_email(text: str, score: float = 0.95) -> list[Span]:
    """Detecte les adresses email."""
    return regex_to_spans(
        EMAIL_PATTERN,
        text,
        entity_type="EMAIL",
        recognizer="EmailRegex",
        score=score,
    )
