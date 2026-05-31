# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de numeros de suivi colis (tracking transporteur).

Detecte les numeros de tracking qui, laisses en clair, permettent
a un attaquant d'interroger directement le portail public du
transporteur pour obtenir :
    - l'adresse de livraison reelle
    - le statut et l'historique d'acheminement
    - parfois le nom du signataire

Vecteur d'attaque red-team : un seul N° de tracking en clair contourne
l'anonymisation, meme si le destinataire est correctement masque dans
le document.

Strategie : deux niveaux complementaires.

1. Patterns par transporteur (signature de format forte, faible faux
   positif).
2. Pattern par libelle contextuel ("N° suivi", "Tracking number",
   "Suivi colis"...) : capture la valeur quelle que soit sa forme.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span


# === Patterns par transporteur (signature de format) ===

# DHL Express : 10 chiffres (waybill number).
_DHL_PATTERN = re.compile(
    r"(?i)\bDHL\b[\s.:#\-]{0,15}(?P<v>\d{10})\b"
)

# UPS : "1Z" + 16 chars alphanumeriques (1Z999AA10123456784).
_UPS_PATTERN = re.compile(
    r"\b(?P<v>1Z[A-Z0-9]{16})\b"
)

# Chronopost / Colissimo / La Poste : 13 caracteres, prefixe alpha 2
# lettres (XX) + 9 chiffres + 2 lettres (FR / BE / DE...).
_CHRONOPOST_PATTERN = re.compile(
    r"\b(?P<v>[A-Z]{2}\d{9}[A-Z]{2})\b"
)

# FedEx : 12 ou 15 chiffres (selon le service).
_FEDEX_PATTERN = re.compile(
    r"(?i)\bFedEx\b[\s.:#\-]{0,15}(?P<v>\d{12,15})\b"
)

# GLS : 11 chiffres ou 14 chiffres pour ParcelShop.
_GLS_PATTERN = re.compile(
    r"(?i)\bGLS\b[\s.:#\-]{0,15}(?P<v>\d{11}(?:\d{3})?)\b"
)

# DPD : 14 chiffres.
_DPD_PATTERN = re.compile(
    r"(?i)\bDPD\b[\s.:#\-]{0,15}(?P<v>\d{14})\b"
)

# TNT (avant fusion FedEx) : 9 ou 12 chiffres.
_TNT_PATTERN = re.compile(
    r"(?i)\bTNT\b[\s.:#\-]{0,15}(?P<v>\d{9,12})\b"
)

# Schenker / DB Schenker : numero LSC (10 chiffres) ou STT (8 chiffres).
_SCHENKER_PATTERN = re.compile(
    r"(?i)\bSchenker\b[\s.:#\-]{0,15}(?P<v>\d{8,12})\b"
)


_CARRIER_PATTERNS = [
    (_DHL_PATTERN, "DHL"),
    (_UPS_PATTERN, "UPS"),
    (_CHRONOPOST_PATTERN, "Chronopost/Colissimo"),
    (_FEDEX_PATTERN, "FedEx"),
    (_GLS_PATTERN, "GLS"),
    (_DPD_PATTERN, "DPD"),
    (_TNT_PATTERN, "TNT"),
    (_SCHENKER_PATTERN, "Schenker"),
]


# === Pattern par libelle contextuel (universel multilingue) ===

# Libelles de tracking, 12 langues.
_TRACKING_LABEL = (
    r"(?:"
    # FR
    r"N[°o]\s*(?:de\s+)?suivi"
    r"|N[°o]\s*suivi"
    r"|Num[ée]ro\s+(?:de\s+)?suivi"
    r"|R[ée]f[ée]rence\s+(?:de\s+)?(?:suivi|colis|exp[ée]dition)"
    r"|Suivi\s+(?:colis|exp[ée]dition)?"
    r"|Tracking"
    r"|N[°o]\s*(?:de\s+)?colis"
    r"|N[°o]\s*BL"  # bon de livraison
    r"|N[°o]\s*exp[ée]dition"
    # EN
    r"|Tracking\s*(?:number|n[°o]\.?|ID|code|reference)"
    r"|Track(?:ing)?\s*N[°o]\.?"
    r"|Waybill\s*(?:number|n[°o]\.?)?"
    r"|Shipment\s*(?:number|ID|reference)"
    r"|AWB\s*(?:number|n[°o]\.?)?"  # air waybill
    # DE
    r"|Sendungsnummer|Sendungs-Nr\.?|Track-Nummer|Versandnummer"
    r"|Frachtbrief(?:nummer)?"
    # ES
    r"|N[°ºo]\s*(?:de\s+)?seguimiento"
    r"|N[úu]mero\s+de\s+seguimiento"
    # IT
    r"|N[°o]\.?\s*(?:di\s+)?spedizione"
    r"|N[°o]\.?\s*tracking"
    r"|Codice\s+spedizione"
    # PT
    r"|N[°ºo]\.?\s*(?:de\s+)?rastreamento"
    r"|N[°ºo]\.?\s*expedi[çc][ãa]o"
    # CN (simplifie + traditionnel)
    r"|快递单?号|追踪号|物流单号|運單號|物流追蹤"
    # JP
    r"|追跡番号|配送番号|送り状番号"
    # PL
    r"|Numer\s+(?:przesy[łl]ki|[śs]ledzenia)"
    # CZ
    r"|[ČC][íi]slo\s+z[áa]silky"
    # TR
    r"|Takip\s+(?:no|numaras[ıi])"
    r"|Kargo\s+(?:takip\s+)?no"
    # BG (cyrillique)
    r"|Номер\s+за\s+проследяване"
    r"|Товарителница"
    r")"
)

_TRACKING_LABELED_PATTERN = re.compile(
    rf"(?ui){_TRACKING_LABEL}\s*[:#.\-]?\s*"
    rf"(?P<v>[A-Z0-9]{{6,30}}(?:[\s\-/][A-Z0-9]{{2,8}}){{0,3}})"
)


def recognize_tracking(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les numeros de suivi de transporteur.

    Combine 2 strategies :
        1. Patterns specifiques par transporteur (DHL/UPS/FedEx/etc.)
        2. Pattern par libelle ("N° suivi", "Tracking number"...)

    La 2e strategie est plus permissive sur la valeur (n'importe quel
    code alphanumerique 6-30 chars) car le libelle ancre la semantique.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Spans de type TRACKING (placeholder `[TRACKING_n]`).
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()

    # Strategie 1 : signature de format par transporteur.
    for pat, carrier in _CARRIER_PATTERNS:
        for m in pat.finditer(text):
            start, end = m.span("v")
            if (start, end) in seen:
                continue
            seen.add((start, end))
            spans.append(
                Span(
                    start=start, end=end,
                    entity_type="TRACKING",
                    text=m.group("v"),
                    score=score,
                    recognizer="TrackingRegex",
                    metadata={"carrier": carrier},
                )
            )

    # Strategie 2 : libelle contextuel + valeur (toute forme).
    for m in _TRACKING_LABELED_PATTERN.finditer(text):
        start, end = m.span("v")
        if (start, end) in seen:
            continue
        # Filtre : doit contenir au moins 4 chiffres (rejette les libelles
        # textuels purs comme "Tracking ENABLED").
        value = m.group("v")
        if sum(1 for c in value if c.isdigit()) < 4:
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="TRACKING",
                text=value,
                score=score * 0.95,
                recognizer="TrackingRegex",
            )
        )

    return spans
