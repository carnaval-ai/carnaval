# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer contextuel multilingue de LOCATION.

Detecte les patterns du type "<mot-cle> <Toponyme>" pour les langues FR, EN,
DE, ES, IT. Genere des spans LOCATION sans avoir besoin d'une deny list
exhaustive.

Exemples couverts :
    FR  "Agence de Bordeaux"       "Site de Quimperle"   "Usine de Cholet"
    EN  "Office in Manchester"     "Branch in Phoenix"
    DE  "Niederlassung Munchen"    "Werk Stuttgart"
    ES  "Oficina de Madrid"        "Sucursal de Barcelona"
    IT  "Sede di Milano"           "Filiale di Torino"

Le pattern est : <keyword> + (espace) + (preposition optionnelle) + <Mot
capitalise>. Score modere (0.7) car risque de faux positifs sur des suites
de mots capitalises non geographiques.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Mots-cles par langue + prepositions optionnelles entre le mot-cle et le toponyme.
# Cle = code langue ISO 639-1, valeur = dict {keywords, prepositions}.
_KEYWORDS_BY_LANG: dict[str, dict[str, tuple[str, ...]]] = {
    "fr": {
        "keywords": (
            "agence",
            "site",
            "bureau",
            "etablissement",
            "usine",
            "depot",
            "succursale",
            "implantation",
            "antenne",
            "filiale",
            "siege",
            "centre",
        ),
        "prepositions": ("de", "d'", "du", "des", "a"),
    },
    "en": {
        "keywords": (
            "office",
            "branch",
            "facility",
            "plant",
            "site",
            "warehouse",
            "location",
            "headquarters",
            "hq",
            "subsidiary",
            "depot",
        ),
        "prepositions": ("in", "of", "at"),
    },
    "de": {
        "keywords": (
            "niederlassung",
            "werk",
            "standort",
            "buro",
            "filiale",
            "zweigstelle",
            "hauptsitz",
            "geschaftsstelle",
            "lager",
        ),
        "prepositions": ("in", "bei", "zu"),
    },
    "es": {
        "keywords": (
            "oficina",
            "sucursal",
            "sede",
            "planta",
            "fabrica",
            "almacen",
            "filial",
            "delegacion",
        ),
        "prepositions": ("de", "en"),
    },
    "it": {
        "keywords": (
            "filiale",
            "sede",
            "ufficio",
            "stabilimento",
            "deposito",
            "magazzino",
            "sedi",
        ),
        "prepositions": ("di", "a", "in"),
    },
    "pt": {
        "keywords": (
            "agencia",
            "escritorio",
            "filial",
            "fabrica",
            "armazem",
            "sucursal",
            "delegacao",
            "sede",
        ),
        "prepositions": ("de", "do", "da", "em"),
    },
}


def _build_pattern(language: str) -> re.Pattern[str] | None:
    """Construit la regex compilee pour une langue donnee.

    NB : on n'utilise PAS re.IGNORECASE globalement car cela rendrait [A-Z]
    insensible et matcherait les mots en minuscules suivant le keyword
    ("Cholet pour" au lieu de "Cholet"). A la place, chaque keyword/prep
    est wrappe dans (?i:...) pour insensibilite locale.
    """
    spec = _KEYWORDS_BY_LANG.get(language)
    if not spec:
        return None

    # Alternance keywords avec insensibilite LOCALE a la casse
    keywords_alt = "|".join(f"(?i:{re.escape(k)})" for k in spec["keywords"])

    # Prepositions facultatives.
    # On distingue deux cas :
    #   - prep finissant par apostrophe (d') : pas d'espace apres
    #   - prep "normale" (de, du, in, of) : espace requis apres
    apostrophe_preps = [p for p in spec["prepositions"] if p.endswith("'")]
    normal_preps = [p for p in spec["prepositions"] if not p.endswith("'")]

    prep_parts: list[str] = []
    if normal_preps:
        normal_alt = "|".join(f"(?i:{re.escape(p)})" for p in normal_preps)
        prep_parts.append(rf"\s+(?:{normal_alt})\s+")  # de + espace + toponym
    if apostrophe_preps:
        apo_alt = "|".join(f"(?i:{re.escape(p)})" for p in apostrophe_preps)
        prep_parts.append(rf"\s+(?:{apo_alt})")  # d'Annecy : pas d'espace apres
    prep_parts.append(r"\s+")  # ou pas de prep, juste un espace

    prep_group = "(?:" + "|".join(prep_parts) + ")"

    # Toponyme : mot capitalise STRICT (sensible a la casse).
    # 1 a 3 mots capitalises, jusqu'a tirets/apostrophes a l'interieur d'un mot.
    toponym = (
        r"[A-Z][A-Za-zéèêëàâäîïôöùûüçÄÖÜß'\-]{2,30}"
        r"(?:[\s\-][A-Z][A-Za-zéèêëàâäîïôöùûüçÄÖÜß'\-]{2,30}){0,2}"
    )

    # Pattern complet : \b<keyword>\b <prep_group> <toponym>
    # On capture le toponyme (groupe 1).
    pattern = rf"\b(?:{keywords_alt})\b{prep_group}({toponym})"

    return re.compile(pattern)


# Cache : pattern compile par langue.
_PATTERN_CACHE: dict[str, re.Pattern[str] | None] = {}


def _get_pattern(language: str) -> re.Pattern[str] | None:
    if language not in _PATTERN_CACHE:
        _PATTERN_CACHE[language] = _build_pattern(language)
    return _PATTERN_CACHE[language]


def recognize_contextual_location(
    text: str,
    languages: set[str],
    score: float = 0.7,
) -> list[Span]:
    """Detecte les toponymes precedes d'un mot-cle de lieu.

    Args:
        text: texte a analyser.
        languages: ensemble des langues a appliquer (ex: {'fr', 'de'}).
        score: confiance par defaut. Modere car risque de faux positifs
            (un mot capitalise apres 'site' peut ne pas etre un lieu).

    Returns:
        Liste de Spans avec entity_type='LOCATION' et recognizer='ContextualLocationRegex'.
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()

    for lang in languages:
        pattern = _get_pattern(lang)
        if pattern is None:
            continue
        for m in pattern.finditer(text):
            # On masque le toponyme (groupe 1), pas le mot-cle
            start = m.start(1)
            end = m.end(1)
            if (start, end) in seen:
                continue
            seen.add((start, end))
            spans.append(
                Span(
                    start=start,
                    end=end,
                    entity_type="LOCATION",
                    text=m.group(1),
                    score=score,
                    recognizer="ContextualLocationRegex",
                )
            )

    return spans
