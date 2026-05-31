# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers de enderecos portugueses / brasileiros.

Cobertura :
    Av. 5 de Outubro 146, 2 Andar
    Rua Augusta 100, 1100-053 Lisboa
    Praca do Comercio
    Apartado 1234
    01310-100 Sao Paulo, SP, Brasil
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Codigo postal Portugal : 4 digitos - 3 digitos (1100-053).
POSTAL_CITY_PT_PATTERN = re.compile(
    r"\b\d{4}[-\s]?\d{3}[ \t]+"
    r"[A-ZÁÉÍÓÚÃÕÇ][A-Za-zàáâãéêíóôõúçÁÉÍÓÚÃÕÇ \t\-'.]{2,60}"
)

# CEP Bresil : 5 digitos - 3 digitos (01310-100)
CEP_BR_PATTERN = re.compile(
    r"\b\d{5}-\d{3}[ \t]+" r"[A-ZÁÉÍÓÚÃÕÇ][A-Za-zàáâãéêíóôõúçÁÉÍÓÚÃÕÇ \t\-'.]{2,60}"
)

# Rues PT : Rua, Avenida, Av., Travessa, Largo, Praca, Estrada, Alameda
STREET_PT_PATTERN = re.compile(
    r"\b(?:Rua|R\.|Avenida|Av\.|Av|Travessa|Largo|Praca|Praça|"
    r"Estrada|Alameda|Beco|Calcada|Rotunda|Loteamento)"
    r"\s+"
    r"(?:de\s|do\s|da\s|dos\s|das\s|d['’])?"
    r"[\w][\w \t\-'’.,]{2,80}",
    re.IGNORECASE,
)

# Apartado postal
APARTADO_PT_PATTERN = re.compile(
    r"\bApartado\s+\d{1,6}\b",
    re.IGNORECASE,
)

# Zones / parques PT : Zona Industrial, Parque Industrial, Parque
# Empresarial, Parque Tecnológico, Centro Empresarial. Audit v6.
ZONE_PT_PATTERN = re.compile(
    r"(?:(?i:\b(?:Zona[ \t]Industrial|Parque[ \t]Industrial|"
    r"Parque[ \t]Empresarial|Parque[ \t]Tecnol[óo]gico|"
    r"Centro[ \t]Empresarial|Polo[ \t]Industrial))"
    r"[ \t]+"
    r"(?:de[ \t]+|do[ \t]+|da[ \t]+|dos[ \t]+|das[ \t]+|d['’][ \t]*)?"
    r"[A-ZÁÉÍÓÚÃÕÇ][\w \t\-'’/.]{2,60})"
)

# Edificios / torres PT : Edifício, Edif., Torre, Bloco, Pavilhão.
BUILDING_PT_PATTERN = re.compile(
    r"(?:(?:[A-ZÁÉÍÓÚÃÕÇ][a-záéíóúãõç]{3,20}[ \t]*-[ \t]*)?"
    r"(?i:\b(?:Edif[íi]cio|Edif\.|Torre|Bloco|Pavilh[ãa]o))"
    r"[ \t]+"
    r"[A-ZÁÉÍÓÚÃÕÇ0-9][\w \t\-'’/.]{1,60})"
)


def recognize_zone_pt(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        ZONE_PT_PATTERN, text, entity_type="LOCATION",
        recognizer="ZonePtRegex", score=score,
    )


def recognize_building_pt(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        BUILDING_PT_PATTERN, text, entity_type="LOCATION",
        recognizer="BuildingPtRegex", score=score,
    )


def recognize_address_pt(text: str, score: float = 0.85) -> list[Span]:
    spans: list[Span] = []
    for pat, name in (
        (POSTAL_CITY_PT_PATTERN, "PostalCityPtRegex"),
        (CEP_BR_PATTERN, "CepBrRegex"),
        (STREET_PT_PATTERN, "StreetPtRegex"),
        (APARTADO_PT_PATTERN, "ApartadoPtRegex"),
        (ZONE_PT_PATTERN, "ZonePtRegex"),
        (BUILDING_PT_PATTERN, "BuildingPtRegex"),
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
