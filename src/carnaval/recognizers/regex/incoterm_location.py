# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer universel : Incoterm + toponyme adjacent.

Les Incoterms (International Commercial Terms) sont une norme ICC
**universelle** (Incoterms 2010 / 2020). Le format `Incoterm + Ville`
est utilise dans TOUS les pays et TOUTES les langues. Le toponyme
adjacent identifie un point de transfert geographique, et donc le
fournisseur ou destinataire concerne.

Ce recognizer N'EST PAS dans address/<lang>.py car les Incoterms ne
sont pas une convention nationale ; il s'applique a tous les documents
quelle que soit la langue detectee.

Vecteur d'attaque red-team v5-bis VL2 : `FCA Stockach`, `DAP Lyon`,
`EXW Madrid` identifient le pays et la ville sans regex d'adresse
classique.

Strategie : conserver l'Incoterm en clair (info metier essentielle pour
l'IA aval : type de transfert, douane, responsabilites). Tokenise
uniquement le toponyme.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Liste Incoterms 2020 ICC + DAT (Incoterms 2010 encore observe).
# Source : ICC publication 723E, 2020.
_INCOTERM = (
    r"EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF|DAT"
)

# Toponyme : commence par majuscule, accepte accents et tiret (Saint-Etienne,
# Wien Hauptbahnhof, Frankfurt am Main). Jusqu'a 4 mots accoles.
_TOPONYM = (
    r"(?P<location>[A-ZÀ-Ÿ][A-Za-zÀ-ÿ\-']{2,}"
    r"(?:[ \t][A-ZÀ-Ÿa-z][A-Za-zÀ-ÿ\-']*){0,3})"
)

_INCOTERM_LOCATION_PATTERN = re.compile(
    rf"\b(?P<incoterm>{_INCOTERM})[ \t]+{_TOPONYM}(?![A-Za-z])"
)

# Mots qui suivent un Incoterm mais ne sont PAS un toponyme : on les
# filtre pour eviter les faux positifs.
_INCOTERM_NOT_LOCATION = frozenset({
    # FR
    "incoterms", "incoterm", "international", "commercial", "termes",
    "termes", "rendu", "rendue", "destination", "destinataire",
    "livraison", "livre", "livree", "transfert", "lieu", "place",
    "depart", "départ", "depart", "arrivée", "arrivee",
    "frais", "compris", "inclus", "exclu", "exclus",
    "franco", "transport", "transporteur",
    # EN
    "named", "shipping", "delivery", "loaded", "unloaded", "paid",
    "warehouse", "duty", "duties", "freight", "carrier", "free",
    "delivered", "destination", "place",
    # DE
    "geliefert", "verzollt", "unverzollt", "ware", "transport",
    "lieferung", "bestimmungsort", "frei",
    # ES
    "entregada", "puerto", "destino", "lugar", "franco",
    # IT
    "consegna", "destinazione", "luogo", "porto", "franco",
    # PT
    "entregue", "destino", "porto", "lugar", "franco",
})

# Mots-toponymes connus trop courts qu'on accepte malgre la limite >= 3
# (Rio, Bay, etc.) - laisser pour evolution future.
_INCOTERM_SHORT_TOPONYMS_OK: frozenset[str] = frozenset()


def recognize_incoterm_location(text: str, score: float = 0.85) -> list[Span]:
    """Tokenise le toponyme qui suit un Incoterm.

    Couvre toutes langues : FCA Stockach (DE), DAP Paris (FR), EXW
    Madrid (ES), DDP Lyon (FR), CPT Customer Site (EN), etc.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Spans LOCATION couvrant uniquement le toponyme (Incoterm
        preserve en clair).
    """
    spans: list[Span] = []
    for m in _INCOTERM_LOCATION_PATTERN.finditer(text):
        loc = m.group("location")
        # Filtre les mots-cles techniques Incoterm (pas un lieu).
        first_word = loc.split()[0].lower()
        if first_word in _INCOTERM_NOT_LOCATION:
            continue
        # Filtre les valeurs ALL CAPS courtes qui sont des codes (FOB CIF)
        # ou des sigles non-toponymiques (sauf liste autorisee).
        if (
            len(loc) <= 3
            and loc.isupper()
            and loc.lower() not in _INCOTERM_SHORT_TOPONYMS_OK
        ):
            continue
        spans.append(
            Span(
                start=m.start("location"), end=m.end("location"),
                entity_type="LOCATION",
                text=loc,
                score=score,
                recognizer="IncotermLocationRegex",
            )
        )
    return spans
