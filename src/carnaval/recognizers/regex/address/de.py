# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers d'adresses allemandes / autrichiennes / suisses.

Couvre les patterns typiques :
    Hauptstrasse 12, 70173 Stuttgart
    Robert-Koch-Strasse 5
    Marienplatz 8
    Postfach 100 800
    A-1010 Wien  /  CH-8001 Zurich  /  D-70173 Stuttgart
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# PLZ DE/AT/CH : 4-5 chiffres + Stadt.
# DE = 5 chiffres, AT/CH = 4 chiffres. Prefixe pays (A-, CH-, D-) accepte.
POSTAL_CITY_DE_PATTERN = re.compile(
    r"\b(?:[A-Z]-)?\d{4,5}[ \t]+" r"[A-ZÄÖÜ][A-Za-zäöüÄÖÜß \t\-'.]{2,60}"
)

# Rues DE : suffixe Strasse/Str./Platz/Weg/Allee/Gasse/Ring/Damm
# Compose ou simple : Hauptstrasse, Robert-Koch-Strasse, Marienplatz.
# On accepte les variantes orthographiques : strasse / straße / Straße
STREET_DE_PATTERN = re.compile(
    r"\b[A-ZÄÖÜ][A-Za-zäöüÄÖÜß\-]{2,40}"
    r"(?:strasse|straße|str\.|platz|weg|allee|gasse|ring|damm|ufer)"
    r"(?:\s+\d{1,4}[a-z]?)?",
    re.IGNORECASE,
)

# Postfach (BP allemand)
POSTFACH_DE_PATTERN = re.compile(
    r"\bPostfach\s+\d{2,6}(?:\s+\d{1,3})?",
    re.IGNORECASE,
)

# Zones / parcs DE : Gewerbegebiet, Industriegebiet, Industriepark, Gewerbepark.
# Suivi d'un nom propre (majuscule). Audit v6 symetrie multilingue.
ZONE_DE_PATTERN = re.compile(
    r"(?:(?i:\b(?:Gewerbegebiet|Industriegebiet|Industriepark|"
    r"Gewerbepark|Wirtschaftspark|Technologiepark))"
    r"[ \t]+"
    r"[A-ZÄÖÜ][\w \t\-'’/.]{2,60})"
)

# Batiments / tours DE : Gebäude, Geb., Haus, Turm, Hochhaus.
# Nom propre case-sensitive pour eviter les faux positifs.
BUILDING_DE_PATTERN = re.compile(
    r"(?:(?:[A-ZÄÖÜ][a-zäöüß]{3,20}[ \t]*-[ \t]*)?"
    r"(?i:\b(?:Geb[äa]ude|Geb\.|Haus|Turm|Hochhaus|"
    r"B[üu]ro(?:gebäude|geb\.)?|Bürohaus|Werk|Halle))"
    r"[ \t]+"
    r"[A-ZÄÖÜ][\w \t\-'’/.]{1,60})"
)


def recognize_postal_city_de(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        POSTAL_CITY_DE_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="PostalCityDeRegex",
        score=score,
    )


def recognize_street_de(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        STREET_DE_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="StreetDeRegex",
        score=score,
    )


def recognize_postfach_de(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        POSTFACH_DE_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="PostfachDeRegex",
        score=score,
    )


def recognize_zone_de(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        ZONE_DE_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="ZoneDeRegex",
        score=score,
    )


def recognize_building_de(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        BUILDING_DE_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="BuildingDeRegex",
        score=score,
    )


def recognize_address_de(text: str) -> list[Span]:
    """Aggregateur DE/AT/CH."""
    return (
        recognize_postal_city_de(text)
        + recognize_street_de(text)
        + recognize_postfach_de(text)
        + recognize_zone_de(text)
        + recognize_building_de(text)
    )
