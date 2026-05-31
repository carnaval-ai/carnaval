# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer telephones France (+33 / 0X).

Formats couverts :
    02.41.34.85.15
    +33 2 41 33 75 75
    + 33 (0)4 43 24 00 00     (indicatif espace, prefixe (0))
    0 825 02 30 35            (numeros de service, groupes irreguliers)
    0241414242               (colle, y compris a du texte : "0241414242N°")
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# Telephone FR = 10 chiffres (0 + 9), ou indicatif international + 9 chiffres.
# - (?<!\d) / (?!\d) : bornes sur les chiffres, pas sur les mots. Capte un
#   numero colle a du texte ("0241414242N°", frequent apres extraction PDF)
#   sans pour autant couper une suite de chiffres plus longue (reference).
# - separateurs (espace, point, tiret) admis a toute position : gere les
#   formats irreguliers ("0 825 02 30 35", "+ 33 (0)...").
# - le 1er chiffre national est 1-9 : ecarte les codes type "0000105276".
# Quatre formes d'indicatif acceptees :
#   `+33`           (canonique)
#   `0033`          (international avec "00" au lieu de "+")
#   `33 (0)`        (preformat presence de "(0)" obligatoire ; sans + ni 00)
#   `0`             (national, 10 chiffres au total)
#
# Cas hybride frequent : "0033 02 43 44 02 48" ou "+33 02 43..." -
# l'utilisateur cumule par erreur le prefixe international ET le 0
# national. On accepte un `0?[\s.\-]?` optionnel apres les variantes
# internationales pour absorber ce 0 supplementaire ; le `[1-9]` qui
# suit garantit qu'on ne consomme pas le 1er chiffre du numero quand
# le format est canonique.
# Principe architectural R1 : un numero de telephone ne traverse JAMAIS
# un saut de ligne. Les separateurs internes sont LIMITES a [ \t.\-] (pas
# `\s` qui inclut `\n`). Bug v7 IFM : `\s` consommait `\n` et faisait
# matcher "0" + "9.2024\n0010" comme "09.2024\n0010" en faux phone.
_SEP_INTERNAL = r"[ \t.\-]?"
_PREFIX = (
    r"(?:"
    rf"\+{_SEP_INTERNAL}33{_SEP_INTERNAL}(?:\(0\){_SEP_INTERNAL})?0?{_SEP_INTERNAL}"
    rf"|00{_SEP_INTERNAL}33{_SEP_INTERNAL}(?:\(0\){_SEP_INTERNAL})?0?{_SEP_INTERNAL}"
    rf"|33{_SEP_INTERNAL}\(0\){_SEP_INTERNAL}"
    rf"|0{_SEP_INTERNAL}"
    r")"
)
PHONE_FR_PATTERN = re.compile(
    r"(?<!\d)" + _PREFIX + rf"[1-9](?:{_SEP_INTERNAL}\d){{8}}(?!\d)"
)

# Garde-fou : rejette explicitement les sequences qui matchent aussi
# le format date `\d{2}\.\d{2}\.\d{4}` (date FR/EN) ou `\d{2}/\d{2}/\d{4}`.
# Bug v7 IFM : "19.09.2024" etait capture comme un phone car le `0` du
# pattern absorbait "0" de "09".
_DATE_LOOKALIKE = re.compile(
    r"^\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}$"
)

# Format degrade : 9 chiffres consecutifs SANS le 0 initial. Frequent
# en OCR de PDF (Lyreco "Fax : 143115490" pour "01 43 11 54 90", le 0
# initial perdu). Pour limiter les faux positifs (9 chiffres = potentielle
# reference produit), on EXIGE un libelle telephonique explicite avant.
# Les libelles couvrent les memes langues que le pipeline (FR/EN/ES/PT/
# IT/DE/PL/TR/CZ/CN/JP/BG) pour cohérence avec la detection des numeros.
PHONE_FR_LABELED_PATTERN = re.compile(
    r"(?ui)(?:"
    r"\bT[ée]l(?:[ée]phone)?\b|\bPhone\b|\bFax\b|\bMobile\b|\bGSM\b"
    r"|\bMob\.?|\bTel\.?|\bTelefon\b|\bTelefono\b|\bTel[ée]fono\b"
    r"|\bTel[ée]fone\b|\bM[óo]vil\b|\bTlf\b|\bCellulare\b|\bCelular\b"
    r"|\bMobil\b|\bKom\.?"
    r"|电话|電話|传真|傳真|手机|手機|FAX|携帯"
    r"|\bтел\.?|\bтелефон\b|\bфакс\b"
    r")\s*[.:：]?\s*"
    r"(?<!\d)"
    r"(?P<value>[1-9]\d{8})"
    r"(?!\d)"
)


def _is_date_lookalike(s: str) -> bool:
    """True si la sequence ressemble a une date (jj.mm.aaaa)."""
    return bool(_DATE_LOOKALIKE.match(s.strip()))


def recognize_phone_fr(text: str, score: float = 0.85) -> list[Span]:
    # Garde-fou R1 : filtre les matches qui sont en realite des dates.
    spans = [
        s for s in regex_to_spans(
            PHONE_FR_PATTERN,
            text,
            entity_type="PHONE",
            recognizer="PhoneFrRegex",
            score=score,
        )
        if not _is_date_lookalike(s.text)
    ]
    # Pattern degrade : 9 chiffres precedes d'un libelle explicite.
    for m in PHONE_FR_LABELED_PATTERN.finditer(text):
        from carnaval.core.span import Span
        start, end = m.span("value")
        if any(s.start == start and s.end == end for s in spans):
            continue
        spans.append(
            Span(
                start=start, end=end,
                entity_type="PHONE",
                text=m.group("value"),
                score=score * 0.95,
                recognizer="PhoneFrRegex",
            )
        )
    return spans
