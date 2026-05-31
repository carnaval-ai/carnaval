# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers d'adresses francaises.

Complement de GLiNER : capture les adresses isolees que GLiNER rate.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Marqueurs forts qu'on est dans une zone d'adresse francaise. Quand l'un
# de ces marqueurs est present dans une fenetre de +/- 3 lignes autour
# d'un nombre 5-chiffres isole, ce nombre est tres probablement un code
# postal francais (cas du pied de page d'AR avec adresse fragmentee en
# colonne : "DRANCY\n93700\nFRANCE", "ST BARTHELEMY D ANJOU\n49180").
_ADDRESS_CONTEXT_MARKERS = re.compile(
    r"(?i)\b(?:FRANCE|FRANCAIS|CEDEX|C[ée]dex"
    # Voies / zones
    r"|RUE|BOULEVARD|AVENUE|IMPASSE|ALL[ÉE]E|CHEMIN|ROUTE|PLACE|QUAI|COURS"
    r"|BD|BLD|BLVD|AV"
    r"|PARC\s+D['’]?ACTIVITE|Z\.?\s?I\.?|Z\.?\s?A\.?C?\.?|ZONE\s+INDUSTRIELLE"
    # Boite postale
    r"|B\.?P\.?\s*\d|C\.?S\.?\s*\d|BO[ÎI]TE\s+POSTALE"
    # Pied de page typique
    r"|SIRET|SIREN|R\.?C\.?S\.?|N°\s*TVA|APE|NAF)\b"
)

# Pattern d'un code postal francais isole : exactement 5 chiffres, bornes
# non-chiffres, pas de virgule (ecarte les montants type "12345,67"),
# pas de tiret/slash/lettre (ecarte les refs alphanumeriques type
# "AF/24487", "AB-12345", "E02-139G-K18").
# Le 1er chiffre 0-9 (les CP FR valides vont de 01000 a 98999).
_POSTAL_CODE_ISOLATED_PATTERN = re.compile(
    r"(?<![\w./,€-])\b(?P<cp>[0-9]{5})\b(?![\w./,€-])"
)


def _has_address_context(text: str, pos: int, window_lines: int = 3) -> bool:
    """True si une fenetre de `window_lines` lignes autour de `pos`
    contient un marqueur d'adresse fort.

    Le marqueur peut etre dans les lignes voisines (haut ou bas) ou
    sur la meme ligne avant/apres. La fenetre limite a 3 lignes evite
    de matcher un nombre 5 chiffres a 50 lignes d'une adresse.
    """
    # Trouver la ligne courante et les +/- window_lines
    line_starts = [pos]
    cursor = pos
    for _ in range(window_lines):
        nl = text.rfind("\n", 0, cursor)
        if nl < 0:
            break
        cursor = nl
        line_starts.append(nl)
    line_starts.sort()
    window_start = line_starts[0]
    cursor = pos
    for _ in range(window_lines + 1):
        nl = text.find("\n", cursor + 1)
        if nl < 0:
            cursor = len(text)
            break
        cursor = nl
    window_end = cursor
    return bool(_ADDRESS_CONTEXT_MARKERS.search(text[window_start:window_end]))


# Code postal 5 chiffres + ville (majuscules OU mixed case).
# - 1er char apres l'espace : DOIT etre majuscule (filtre faux positifs)
# - Suite : minuscules + accentues + tirets + apostrophes acceptes pour
#   couvrir "Le Bourget-du-Lac", "Saint-Etienne", "Cédex"...
# - [ \t]* (pas \s) pour ne pas franchir un retour ligne
POSTAL_CITY_PATTERN = re.compile(
    r"\b\d{5}[ \t]*[A-Z]"
    r"[A-Za-zéèêëàâäîïôöùûüçÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ \t\-'.]{2,60}\b"
)

# Mots de jargon commercial : s'ils apparaissent dans le "nom de ville"
# capture, c'est une ligne de poste / total prise pour une adresse, pas une
# vraie commune. Aucun de ces mots n'entre dans un nom de commune FR.
_POSTAL_CITY_STOPWORDS = frozenset(
    {
        "frais", "transport", "emballage", "remise", "total", "commande",
        "facture", "quantite", "montant", "escompte", "designation",
        "reference", "livraison", "eur", "euros", "franco", "forfait",
        "minimum", "acompte", "contribution",
        # Termes bancaires : "00037 Domiciliation" (apres un SIRET 14 chiffres
        # type "950 622 878 00037 Domiciliation:") n'est pas un code postal,
        # et ce match-la evinçait le SIRET en resolution.
        "domiciliation", "rib", "iban", "swift", "bic",
    }
)


def _is_plausible_postal_city(captured: str) -> bool:
    """Rejette un match « CP + ville » dont la ville contient un mot de
    jargon commercial (ligne de poste / total prise pour une adresse)."""
    words = re.split(r"[ \t\-']+", captured.lower())
    return not any(w in _POSTAL_CITY_STOPWORDS for w in words)

# Boite postale (BP, B.P., CS) - accepte espace ou non entre prefixe
# et numero (audit v5-bis : "BP101" sans espace en clair). Tolere aussi
# le tiret optionnel BP-12345.
BP_PATTERN = re.compile(
    r"\b(?:B\.?P\.?|C\.?S\.?)[ \t\-]*\d{2,6}\b",
    re.IGNORECASE,
)

# Zones d'activite francaises - accepte Z.I., Z.I, ZAC, ZA, ZA Oceane, etc.
# VL1 (audit v5-bis) : ajout des variantes ZA et Z.A. (sans C) qui etaient
# manquantes (la regex initiale exigeait soit ZAC soit ZI). Bug U+2019
# (apostrophe typographique '’') corrige dans le suffixe (auparavant
# seule l'apostrophe ASCII U+0027 etait acceptee, ce qui coupait le
# matching sur "ZAC X- 449 rue de l'Avenir").
# Inclut aussi les noms de technopoles connues (Technolac, Sophia-Antipolis...)
ZONE_PATTERN = re.compile(
    # Alternative 1 : prefixes PARC/ZONE/ZAC/ZI (IGNORECASE via (?i:))
    # avec liaison "de/du/des" toleree, et nom propre suivant qui DOIT
    # commencer par une majuscule (pour eviter "tour de table" mais
    # accepter "Pissaloup", "Stalingrad", etc.).
    r"(?:(?i:\b(?:PARC[ \t]D['’ ]ACTIVIT[EÉé]?[Ss]?|"
    r"PARC[ \t]ACTIVIT[EÉé]?[Ss]?|"
    r"Z\.?\s?A\.?\s?C\.?|Z\.?\s?A\.?|Z\.?\s?I\.?|"
    r"ZONE[ \t]INDUSTRIELLE|ZONE[ \t]ARTISANALE|"
    r"ZONE[ \t]D['’ ]ACTIVIT[EÉé]?[Ss]?|"
    r"TECHNOPOLE|TECHNOPARC))"
    r"[ \t]*-?[ \t]*"
    r"(?i:de[ \t]+|du[ \t]+|des[ \t]+|d['’][ \t]*)?"
    r"[A-ZÀ-Ý\d][\w \t\-'’/.]{2,80})"
    r"|"
    # Alternative 2 : prefixes IMMEUBLE/BATIMENT/TOUR/RESIDENCE/etc.
    # Ces mots sont courants en francais (Tour de table, Tour de France,
    # Villa la nuit...), donc PAS de liaison "de/du" toleree, et le nom
    # propre suivant DOIT commencer par une majuscule franche (case-
    # sensitive a ce niveau pour discriminer "Tour Eiffel" vs "tour de
    # table").
    # Prefixe optionnel : "Arboretum-Bâtiment Cèdre" = parc nomme suivi
    # d'un tiret puis Bâtiment + nom.
    r"(?:(?:[A-ZÀ-Ý][a-zéèàâäîïôöùûüç]{3,20}[ \t]*-[ \t]*)?"
    r"(?i:\b(?:IMMEUBLE|Imm\.|"
    r"B[âa]TIMENT|B[âa]T\.?|"
    r"TOUR|"
    r"R[ée]SIDENCE|"
    r"VILLA|"
    r"PAVILLON|"
    r"ARBORETUM))"
    r"[ \t]+"
    r"[A-ZÀ-Ý][\w \t\-'’/.]{1,60})"
    r"|"
    # Technopoles nommees (Savoie Technolac, Sophia-Antipolis, etc.)
    r"(?:\b[A-Z][A-Za-zéèêëàâäîïôöùûüç]{2,20}"
    r"(?:[\s\-][A-Z][A-Za-zéèêëàâäîïôöùûüç]{2,20})?"
    r"[\s\-](?i:Technolac)\b)"
    r"|(?:\b(?i:Sophia)[\s\-](?i:Antipolis)\b)"
    # Volontairement PAS de flag global IGNORECASE pour preserver le
    # discrimine "Tour" vs "tour" sur le nom propre.
)

# Rue / boulevard / avenue ... + nom : matche les adresses isolees sans code postal.
# Numero + (virgule ou espace) + type voie + nom de la rue.
# Exemples couverts :
#   126 RUE DE STALINGRAD
#   30 Boulevard de la Republique
#   155, avenue du Faucigny
#   126,RUE DE STALINGRAD       (sans espace apres virgule)
STREET_PATTERN_WITH_NUMBER = re.compile(
    r"\b\d{1,4}\s*,?\s*(?:bis|ter|quater)?\s*"
    r"(?:rue|boulevard|bd|bld|blvd|avenue|av|impasse|allée|allee|"
    r"chemin|route|place|quai|cours)\s+"
    r"(?:de\s|du\s|des\s|d['’]|la\s|le\s|l['’])?"
    r"[\w][\w \t\-'’./]{2,60}\b",
    re.IGNORECASE,
)

# Cas ou la rue est sur une ligne SEULE (sans numero precedent) :
#   Rue de la Gare
#   Boulevard de la Republique
#   Avenue des Champs-Elysees
STREET_PATTERN_WITHOUT_NUMBER = re.compile(
    r"\b(?:Rue|Boulevard|BLD|BLVD|Avenue|Impasse|Allée|Allee|Chemin|Route|"
    r"Place|Quai|Cours)\s+"
    r"(?:(?:de|du|des|la|le|l['’]|d['’])\s+){0,2}"
    r"[A-Z][\w \t\-'’./]{2,60}\b"
)

# Cas particulier : texte parasite ou tous les mots sont colles.
# Exemples : "126RUEDESTALINGRAD", "RuedelaGare".
STREET_GLUED_PATTERN = re.compile(
    r"\b\d{0,4}\s*"
    r"(?:rue|boulevard|bd|avenue|impasse|allee|chemin|route|place|quai|cours)"
    r"(?:de|du|des|d[a-z]?|la|le|l[a-z]?)?"
    r"[a-z]{2,40}",
    re.IGNORECASE,
)


def recognize_postal_city_fr(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        POSTAL_CITY_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="PostalCityFrRegex",
        score=score,
        validator=_is_plausible_postal_city,
    )


def recognize_postal_code_isolated_fr(text: str, score: float = 0.8) -> list[Span]:
    """Detecte un code postal francais ISOLE (sans ville accolee).

    Cas typique : pied d'AR extrait colonne par colonne du PDF, ou
    l'adresse est fragmentee verticalement :

        DRANCY
        93700
        FRANCE

    Le pattern POSTAL_CITY classique exige "CP + espace + ville" sur la
    meme ligne et rate ce cas. Ce recognizer detecte le CP seul a
    condition qu'une ligne adjacente (+/- 3) contienne un marqueur
    d'adresse fort (FRANCE, CEDEX, RUE, BP, SIRET, etc.). C'est la
    garantie qu'on n'est pas sur un nombre 5-chiffres metier (numero
    de commande, reference article) mais bien dans une zone d'adresse.
    """
    spans: list[Span] = []
    for m in _POSTAL_CODE_ISOLATED_PATTERN.finditer(text):
        cp = m.group("cp")
        # CP francais valide : 1er chiffre 0-9, 2eme chiffre [0-9].
        # Les CP commencent par 01-98 (sauf cas DOM/TOM en 97/98).
        # On rejette le "00000" et autres improbables tres simplement.
        if cp == "00000":
            continue
        if not _has_address_context(text, m.start()):
            continue
        spans.append(
            Span(
                start=m.start("cp"), end=m.end("cp"),
                entity_type="LOCATION",
                text=cp,
                score=score,
                recognizer="PostalCodeIsolatedFrRegex",
            )
        )
    return spans


def recognize_bp(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les references de boite postale (BP 70226, B.P. 100, CS 12345)."""
    return regex_to_spans(
        BP_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="BpRegex",
        score=score,
    )


def recognize_zone_fr(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        ZONE_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="ZoneFrRegex",
        score=score,
    )


def recognize_street_fr(text: str, score: float = 0.85) -> list[Span]:
    spans = regex_to_spans(
        STREET_PATTERN_WITH_NUMBER,
        text,
        entity_type="LOCATION",
        recognizer="StreetFrRegex",
        score=score,
    )
    spans += regex_to_spans(
        STREET_PATTERN_WITHOUT_NUMBER,
        text,
        entity_type="LOCATION",
        recognizer="StreetFrRegex",
        score=score - 0.05,
    )
    spans += regex_to_spans(
        STREET_GLUED_PATTERN,
        text,
        entity_type="LOCATION",
        recognizer="StreetGluedRegex",
        score=score - 0.05,
    )
    return spans


# NOTE v6 : `recognize_incoterm_location` est desormais dans le module
# universel `carnaval.recognizers.regex.incoterm_location` car les
# Incoterms sont une convention ICC mondiale, applicable a TOUTES les
# langues. Le pipeline l'appelle independamment du dispatcher
# multilingue de adresses.


def recognize_address_fr(text: str) -> list[Span]:
    """Aggregateur FR (sans IncotermLocation : universel, voir module dedie)."""
    return (
        recognize_postal_city_fr(text)
        + recognize_postal_code_isolated_fr(text)
        + recognize_zone_fr(text)
        + recognize_street_fr(text)
        + recognize_bp(text)
    )
