# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de N° d'affaire / N° de dossier client.

Vecteur identifie par le client (Patrice, directive v4) : le N° d'affaire
ou N° de dossier est un identifiant interne deploying CLIENT qui designe
un dossier de commande / une affaire en cours. Differencie du N° de PO,
du code client, et du N° interne fournisseur.

Strategie : tokenisation uniquement quand un libelle FORMEL ancre la
valeur. Pas de detection par signature isolee (risque de faux positifs
sur des numeros metier non sensibles).

Exemples observes :
    "N° Affaire [ORG_5] : 32575"     (libelle direct)
    "Affaire suivie par"              (-> nom personne, deja couvert)
    "N° d'affaire : ABC-2025-1234"
    "Dossier n° 044178"
    "Réf dossier : DOS-MARDAN-2026-12"
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelles d'affaire / dossier (multilingue).
_AFFAIR_LABEL = (
    r"(?:"
    # FR
    r"N[°o]\s*(?:d['’]\s*)?affaire"
    r"|N[°o]\s+affaire"
    r"|R[ée]f\.?\s+(?:de\s+l['’]?)?affaire"
    r"|R[ée]f[ée]rence\s+(?:de\s+l['’]?)?affaire"
    r"|Affaire\s+N[°o]\.?"
    r"|Affaire\s+(?:n[°o]|reference)"
    r"|N[°o]\s*dossier"
    r"|N[°o]\s+de\s+dossier"
    r"|R[ée]f\.?\s+dossier"
    r"|R[ée]f[ée]rence\s+dossier"
    r"|Dossier\s+N[°o]\.?"
    r"|Dossier\s+n[°o]"
    # EN
    r"|Project\s+(?:n[°o]\.?|number|ref)"
    r"|Case\s+(?:n[°o]\.?|number)"
    r"|File\s+(?:n[°o]\.?|number|ref)"
    # DE
    r"|Projektnummer|Aktenzeichen"
    # ES
    r"|N[°ºo]\s+expediente"
    # IT
    r"|N[°o]\s+pratica"
    r")"
)

# Valeur : code alphanum 3-25 chars avec >=2 chiffres. Tolere les
# separateurs `-/_.` internes (DOS-MARDAN-2026-12).
_AFFAIR_VALUE = r"(?P<value>[A-Z0-9](?:[A-Z0-9\-/_.]){2,24})"

# Separateur entre libelle et valeur. Tolere jusqu'a 30 chars sans
# saut de ligne, avec possibilite d'un placeholder intermediaire
# ("N° Affaire [ORG_5] : 32575" : placeholder masquant le nom propre).
# Non-greedy pour s'arreter au premier numero candidat.
_AFFAIR_SEPARATOR = r"(?:\[[A-Z_]+(?:_\d+)?\]|[^\n])*?"
_AFFAIR_PATTERN = re.compile(
    rf"(?i){_AFFAIR_LABEL}\s*[:.#\-]?\s*{_AFFAIR_SEPARATOR}{_AFFAIR_VALUE}\b"
)


def _has_min_digits(value: str, minimum: int = 2) -> bool:
    return sum(1 for c in value if c.isdigit()) >= minimum


def recognize_affair_number(text: str, score: float = 0.88) -> list[Span]:
    """Detecte les N° d'affaire / dossier client (libelle formel obligatoire).

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Spans de type AFFAIR_NUMBER.
    """
    spans: list[Span] = []
    for m in _AFFAIR_PATTERN.finditer(text):
        value = m.group("value")
        if not _has_min_digits(value, 2):
            continue
        # Filtre noise courants
        if value.upper() in {"TVA", "VAT", "SIRET", "SIREN", "EUR", "USD",
                              "JOUR", "JOURS", "SEM", "JANV", "FEV", "AVR"}:
            continue
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="AFFAIR_NUMBER",
                text=value,
                score=score,
                recognizer="AffairNumberRegex",
            )
        )
    return spans
