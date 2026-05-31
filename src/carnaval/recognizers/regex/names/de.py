# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer noms allemands.

Couvre les formes typiques :
    Herr Schmidt
    Frau Dr. Muller
    Prof. Dr. med. Hans Schneider
    Sehr geehrter Herr Schmidt
    Ansprechpartner: Klaus Weber
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Titres : Herr, Frau, Dr., Prof., Dipl.-Ing., etc.
TITLE_DE_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:Sehr\s+geehrter?\s+)?"
    r"(?:Herr|Frau|Dr\.?|Prof\.?|Dipl\.\-?Ing\.?|Dipl\.\-?Kfm\.?|"
    r"Mag\.?|Ing\.?|Med\.?|Hr\.?|Fr\.?)"
    r"(?:\s+(?:Dr\.?|Prof\.?|med\.?|jur\.?|rer\.?\s?nat\.?))*"
    r"\s+[A-ZÄÖÜ][A-Za-zäöüÄÖÜß\-]{1,30}"
    r"(?:\s+[A-ZÄÖÜ][A-Za-zäöüÄÖÜß\-]{1,30}){0,2}"
)

# Mots-cles de contexte (apres lesquels apparait un nom) : "Ansprechpartner: X"
PERSON_CONTEXT_KEYWORDS_DE = (
    "ansprechpartner",
    "kontakt",
    "bearbeiter",
    "zustandig",
    "verantwortlich",
    "mitarbeiter",
    "vertrieb",
    "verkaufer",
    # Fonctions de direction (corporate)
    "geschäftsführer",
    "geschaftsfuhrer",
    "vorstand",
    "vorsitzender",
    "aufsichtsrat",
    "aufsichtsrats",
    "prokurist",
    "direktor",
    "leiter",
    "leitung",
    "abteilungsleiter",
    # Fonctions commerciales
    "kundenbetreuer",
    "ihr berater",
)

# Pattern : 2 a 4 mots capitalises consecutifs, le dernier pouvant
# inclure un tiret pour noms composes (Stegmaier-Hermle).
_PERSON_CAPITALIZE_NGRAM_DE = re.compile(
    r"\b[A-ZÄÖÜ][a-zäöüß]{2,15}" r"(?:[\s\-][A-ZÄÖÜ][a-zäöüß]{2,15}){1,3}" r"\b"
)

# Mot capitalize seul (pour les noms de famille isoles dans une liste).
_PERSON_SINGLE_LASTNAME_DE = re.compile(
    r"\b[A-ZÄÖÜ][a-zäöüß]{3,25}" r"(?:-[A-ZÄÖÜ][a-zäöüß]{3,25})?" r"\b"
)


def recognize_title_de(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        TITLE_DE_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="TitleDeRegex",
        score=score,
    )


_KEYWORDS_LOWER_SET: set[str] = {k.lower() for k in PERSON_CONTEXT_KEYWORDS_DE}

# Mots courants allemands NON-noms qui peuvent etre Capitalize et tomber
# dans le ngram (articles, prepositions, mots fonctionnels frequents).
_DE_COMMON_NON_NAMES: set[str] = {
    "der",
    "die",
    "das",
    "den",
    "des",
    "dem",
    "und",
    "oder",
    "von",
    "zu",
    "mit",
    "an",
    "in",
    "auf",
    "sitz",
    "gesellschaft",
    "registergericht",
    "amtsgericht",
    "deutschland",
    "österreich",
    "schweiz",
    "frankreich",
    "geschäftsführer",
    "geschaftsfuhrer",
    "geschäftsführerin",
    "vorstand",
    "vorsitzender",
    "vorsitzende",
    "aufsichtsrat",
    "aufsichtsrats",
    "prokurist",
    "direktor",
    "leiter",
    "leitung",
    "abteilungsleiter",
    "mitarbeiter",
    "bearbeiter",
    "kundenbetreuer",
    "ansprechpartner",
    "kontakt",
}


def _is_word_a_name(word: str) -> bool:
    """Heuristique : True si le mot ressemble a un nom de personne.

    Filtre :
      - Mots-cles de contexte (Geschäftsführer, Vorsitzender, ...)
      - Articles / prepositions DE
      - Mots fonctionnels frequents en lettres majuscules natives
    """
    lw = word.lower()
    if lw in _DE_COMMON_NON_NAMES:
        return False
    if lw in _KEYWORDS_LOWER_SET:
        return False
    return True


def _is_context_present(text: str, position: int, window: int = 120) -> bool:
    """Renvoie True si un mot-cle de contexte PERSON est present dans la
    fenetre `window` caracteres avant `position`.
    """
    before = text[max(0, position - window) : position].lower()
    return any(kw in before for kw in _KEYWORDS_LOWER_SET)


def _split_ngram_around_non_names(
    match_text: str,
    match_start: int,
) -> list[tuple[int, int, str]]:
    """Decoupe un ngram capture par le pattern pour exclure les mots qui
    ne sont pas des noms de personnes (mots-cles, articles...).

    Returns:
        Liste de (start, end, text) pour chaque sous-segment de mots
        consecutifs valides de longueur >= 2.
    """
    # On parcourt les mots et leurs offsets dans match_text
    parts: list[tuple[int, str]] = []
    i = 0
    while i < len(match_text):
        # skip separators
        while i < len(match_text) and match_text[i] in " \t-":
            i += 1
        if i >= len(match_text):
            break
        start = i
        while i < len(match_text) and match_text[i] not in " \t":
            i += 1
        parts.append((start, match_text[start:i]))

    # Grouper les mots consecutifs qui SONT des noms
    segments: list[tuple[int, int, str]] = []
    current: list[tuple[int, str]] = []
    for offset, word in parts:
        if _is_word_a_name(word):
            current.append((offset, word))
        else:
            if len(current) >= 2:
                seg_start = match_start + current[0][0]
                last_offset, last_word = current[-1]
                seg_end = match_start + last_offset + len(last_word)
                seg_text = match_text[current[0][0] : last_offset + len(last_word)]
                segments.append((seg_start, seg_end, seg_text))
            current = []
    if len(current) >= 2:
        seg_start = match_start + current[0][0]
        last_offset, last_word = current[-1]
        seg_end = match_start + last_offset + len(last_word)
        seg_text = match_text[current[0][0] : last_offset + len(last_word)]
        segments.append((seg_start, seg_end, seg_text))
    return segments


def recognize_contextual_person_de(text: str, score: float = 0.75) -> list[Span]:
    """Detecte les noms de personnes apres un mot-cle de contexte.

    Strategie :
      1. Trouver les ngrams capitalize 2-4 mots dans le texte.
      2. Pour chaque ngram, decouper en sous-segments en excluant les
         mots-cles fonctionnels DE (Geschäftsführer, Vorsitzender,
         Aufsichtsrats, der, die, des...) qui sont Capitalize mais
         ne sont PAS des noms.
      3. Garder les sous-segments dont au moins un mot-cle de contexte
         est present dans la fenetre 120 chars avant.

    NB : on ne fait pas de single-lastname (mots isoles) pour DE car
    trop de faux positifs sur les noms communs capitalises.
    """
    spans: list[Span] = []

    for m in _PERSON_CAPITALIZE_NGRAM_DE.finditer(text):
        # Decouper le ngram autour des mots non-noms
        segments = _split_ngram_around_non_names(m.group(0), m.start())
        for seg_start, seg_end, seg_text in segments:
            if _is_context_present(text, seg_start):
                spans.append(
                    Span(
                        start=seg_start,
                        end=seg_end,
                        entity_type="PERSON",
                        text=seg_text,
                        score=score,
                        recognizer="ContextualPersonDeRegex",
                    )
                )

    return spans


def recognize_names_de(text: str) -> list[Span]:
    return recognize_title_de(text) + recognize_contextual_person_de(text)
