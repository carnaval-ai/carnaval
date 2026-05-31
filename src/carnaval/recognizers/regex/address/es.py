# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers de direcciones espanolas y hispanoamericanas.

Cubre :
    Calle Mayor 5, 28013 Madrid
    Avenida Diagonal 350, Barcelona
    Plaza de Espana 1
    Apartado de Correos 100
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Codigo postal espanol : 5 chiffres (00000-52999) + ville
POSTAL_CITY_ES_PATTERN = re.compile(
    r"\b\d{5}[ \t]+" r"[A-ZÁÉÍÓÚÑ][A-Za-zàáéíóúñÁÉÍÓÚÑ \t\-'.]{2,60}"
)

# Rues ES : Calle / Avenida / Plaza / Paseo / Carretera / Camino / Ronda
STREET_ES_PATTERN = re.compile(
    r"\b(?:C/|Calle|Avenida|Avda|Avd|Plaza|Pza|Paseo|Po|"
    r"Carretera|Ctra|Camino|Cmno|Ronda|Travesia|Glorieta|Plazoleta)"
    r"\s+"
    r"(?:de\s|del\s|la\s|las\s|los\s|el\s)?"
    r"[\w][\w \t\-'.]{2,60}",
    re.IGNORECASE,
)

# Apartado de Correos
APARTADO_ES_PATTERN = re.compile(
    r"\b(?:Apartado(?:\s+de\s+Correos)?|Apdo)\s+\d{1,6}\b",
    re.IGNORECASE,
)

# Zones / parcs ES : Polígono Industrial, Parque Empresarial, Parque
# Tecnológico, Parque Industrial, Zona Industrial. Audit v6 symetrie.
ZONE_ES_PATTERN = re.compile(
    r"(?:(?i:\b(?:Pol[ií]gono[ \t]Industrial|Parque[ \t]Empresarial|"
    r"Parque[ \t]Tecnol[óo]gico|Parque[ \t]Industrial|"
    r"Zona[ \t]Industrial|Centro[ \t]Empresarial))"
    r"[ \t]+"
    r"(?:de[ \t]+|del[ \t]+|de[ \t]la[ \t]+)?"
    r"[A-ZÁÉÍÓÚÑ][\w \t\-'’/.]{2,60})"
)

# Edificios / torres ES : Edificio, Edif., Torre, Bloque, Pabellón.
BUILDING_ES_PATTERN = re.compile(
    r"(?:(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,20}[ \t]*-[ \t]*)?"
    r"(?i:\b(?:Edificio|Edif\.|Torre|Bloque|Pabell[óo]n|Nave|"
    r"Manzana))"
    r"[ \t]+"
    r"[A-ZÁÉÍÓÚÑ0-9][\w \t\-'’/.]{1,60})"
)


def recognize_zone_es(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        ZONE_ES_PATTERN, text, entity_type="LOCATION",
        recognizer="ZoneEsRegex", score=score,
    )


def recognize_building_es(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        BUILDING_ES_PATTERN, text, entity_type="LOCATION",
        recognizer="BuildingEsRegex", score=score,
    )


def recognize_address_es(text: str, score: float = 0.85) -> list[Span]:
    spans: list[Span] = []
    for pat, name in (
        (POSTAL_CITY_ES_PATTERN, "PostalCityEsRegex"),
        (STREET_ES_PATTERN, "StreetEsRegex"),
        (APARTADO_ES_PATTERN, "ApartadoEsRegex"),
        (ZONE_ES_PATTERN, "ZoneEsRegex"),
        (BUILDING_ES_PATTERN, "BuildingEsRegex"),
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
