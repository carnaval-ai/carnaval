# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers d'adresses anglophones (UK, US, CA, AU).

Couvre :
    UK   123 High Street, London SW1A 1AA
         Flat 4, 25 King's Road
    US   1600 Pennsylvania Ave NW, Washington DC 20500
         123 Main St
    CA   M5V 3A8 Toronto
    AU   10 Smith St, Sydney NSW 2000
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# UK postcode : LETTRES + chiffres (SW1A 1AA, EC1A 1BB, M1 1AA).
POSTCODE_UK_PATTERN = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?[ ]\d[A-Z]{2}\b")

# US ZIP : 5 chiffres + optionnel -4
ZIP_US_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b(?!\s*\d)")

# Code postal canadien : A1A 1A1
POSTCODE_CA_PATTERN = re.compile(r"\b[A-Z]\d[A-Z][ ]?\d[A-Z]\d\b")

# Rues EN : street / st. / avenue / ave / boulevard / blvd / drive / dr /
#           road / rd / lane / ln / way / court / ct / square / sq / place / pl
STREET_EN_PATTERN = re.compile(
    r"\b\d{1,5}[a-z]?\s+"
    r"(?:[A-Z][A-Za-z\-']+\s+){1,3}"
    r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|"
    r"Lane|Ln|Way|Court|Ct|Square|Sq|Place|Pl|Parkway|Pkwy|Terrace|Ter|"
    r"Highway|Hwy|Crescent|Cres)\b\.?",
    re.IGNORECASE,
)

# PO Box
PO_BOX_PATTERN = re.compile(
    r"\b(?:P\.?\s?O\.?\s?Box|Post\s?Office\s?Box)\s+\d{1,6}\b",
    re.IGNORECASE,
)

# Zones / parcs EN : Business Park, Industrial Estate / Park, Trading
# Estate, Technology Park, Science Park, Office Park, Retail Park.
# Audit v6 symetrie multilingue.
ZONE_EN_PATTERN = re.compile(
    r"(?:(?i:\b(?:Business[ \t]Park|Industrial[ \t](?:Estate|Park|Zone)|"
    r"Trading[ \t]Estate|Technology[ \t]Park|Science[ \t]Park|"
    r"Office[ \t]Park|Retail[ \t]Park|Enterprise[ \t](?:Park|Zone)))"
    r"[ \t]+"
    r"[A-Z][\w \t\-'’/.]{2,60})"
    r"|"
    # Sens inverse : Nom + "Business Park" (UK style : "Edinburgh Park")
    r"(?:\b[A-Z][A-Za-z\-']{2,30}"
    r"(?:[ \t][A-Z][A-Za-z\-']+){0,2}"
    r"[ \t](?i:Business[ \t]Park|Industrial[ \t]Estate|"
    r"Trading[ \t]Estate|Technology[ \t]Park|Science[ \t]Park))"
)

# Batiments / tours EN : Building, Bldg, Tower, House, Block, Wing,
# Suite, Floor, Plaza, Centre. Nom propre case-sensitive.
BUILDING_EN_PATTERN = re.compile(
    r"(?:(?:[A-Z][a-z]{3,20}[ \t]*-[ \t]*)?"
    r"(?i:\b(?:Building|Bldg|Tower|House|Block|Wing|"
    r"Suite|Plaza|Centre|Center|Hall|Pavilion))"
    r"[ \t]+"
    r"[A-Z0-9][\w \t\-'’/.]{1,60})"
    r"|"
    # Sens inverse : "<Nom> Tower", "<Nom> House", "<Nom> Building"
    r"(?:\b[A-Z][A-Za-z\-']{2,30}"
    r"(?:[ \t][A-Z][A-Za-z\-']+){0,2}"
    r"[ \t](?i:Tower|House|Building|Plaza|Centre|Center))"
)


def recognize_zone_en(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        ZONE_EN_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="ZoneEnRegex",
        score=score,
    )


def recognize_building_en(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        BUILDING_EN_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="BuildingEnRegex",
        score=score,
    )


def recognize_address_en(text: str, score: float = 0.85) -> list[Span]:
    """Aggregateur EN (UK + US + CA + AU)."""
    spans: list[Span] = []
    for pat, name in (
        (POSTCODE_UK_PATTERN, "PostcodeUkRegex"),
        (ZIP_US_PATTERN, "ZipUsRegex"),
        (POSTCODE_CA_PATTERN, "PostcodeCaRegex"),
        (STREET_EN_PATTERN, "StreetEnRegex"),
        (PO_BOX_PATTERN, "PoBoxRegex"),
        (ZONE_EN_PATTERN, "ZoneEnRegex"),
        (BUILDING_EN_PATTERN, "BuildingEnRegex"),
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
