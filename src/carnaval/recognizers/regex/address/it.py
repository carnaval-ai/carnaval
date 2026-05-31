# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers di indirizzi italiani.

Coperture :
    Via Roma 12, 20121 Milano
    Viale della Liberta 5
    Piazza Duomo 1
    Corso Vittorio Emanuele 100
    Casella Postale 1234
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# CAP italien : 5 chiffres + ville
POSTAL_CITY_IT_PATTERN = re.compile(
    r"\b\d{5}[ \t]+" r"[A-Z][A-Za-zàèéìòùÀÈÉÌÒÙ \t\-'.]{2,60}"
)

# Rues IT : Via / Viale / Piazza / Corso / Vicolo / Largo / Strada / Lungomare
STREET_IT_PATTERN = re.compile(
    r"\b(?:Via|Viale|V\.le|Piazza|Pza|P\.za|Corso|C\.so|"
    r"Vicolo|V\.lo|Largo|L\.go|Strada|Lungomare|Lungotevere|"
    r"Riva|Salita|Calle)"
    r"\s+"
    r"(?:di\s|del\s|della\s|delle\s|degli\s|dei\s|d['’])?"
    r"[\w][\w \t\-'’.]{2,60}",
    re.IGNORECASE,
)

# Casella Postale (BP)
CASELLA_POSTALE_IT_PATTERN = re.compile(
    r"\b(?:Casella\s+Postale|C\.?\s?P\.?)\s+\d{1,6}\b",
    re.IGNORECASE,
)

# Zones / parcs IT : Zona Industriale, Centro Direzionale, Parco
# Industriale, Parco Tecnologico, Distretto Industriale. Audit v6.
ZONE_IT_PATTERN = re.compile(
    r"(?:(?i:\b(?:Zona[ \t]Industriale|Zona[ \t]Artigianale|"
    r"Centro[ \t]Direzionale|Centro[ \t]Commerciale|"
    r"Parco[ \t]Industriale|Parco[ \t]Tecnologico|"
    r"Distretto[ \t]Industriale|Polo[ \t]Industriale))"
    r"[ \t]+"
    r"(?:di[ \t]+|del[ \t]+|della[ \t]+|delle[ \t]+|d['’][ \t]*)?"
    r"[A-ZÀ-Ý][\w \t\-'’/.]{2,60})"
)

# Edifici / torri IT : Palazzo, Torre, Edificio, Blocco, Padiglione.
BUILDING_IT_PATTERN = re.compile(
    r"(?:(?:[A-ZÀ-Ý][a-zàèéìòù]{3,20}[ \t]*-[ \t]*)?"
    r"(?i:\b(?:Palazzo|Pal\.|Torre|Edificio|Edif\.|Blocco|"
    r"Padiglione|Capannone))"
    r"[ \t]+"
    r"[A-ZÀ-Ý0-9][\w \t\-'’/.]{1,60})"
)


def recognize_zone_it(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        ZONE_IT_PATTERN, text, entity_type="LOCATION",
        recognizer="ZoneItRegex", score=score,
    )


def recognize_building_it(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        BUILDING_IT_PATTERN, text, entity_type="LOCATION",
        recognizer="BuildingItRegex", score=score,
    )


def recognize_address_it(text: str, score: float = 0.85) -> list[Span]:
    spans: list[Span] = []
    for pat, name in (
        (POSTAL_CITY_IT_PATTERN, "PostalCityItRegex"),
        (STREET_IT_PATTERN, "StreetItRegex"),
        (CASELLA_POSTALE_IT_PATTERN, "CasellaPostaleItRegex"),
        (ZONE_IT_PATTERN, "ZoneItRegex"),
        (BUILDING_IT_PATTERN, "BuildingItRegex"),
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
