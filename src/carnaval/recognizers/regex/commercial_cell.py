# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de noms dans cellules tabulaires (Commercial / Acheteur / ...).

Vecteur d'attaque red-team v2 VN2 : un nom de personne en MAJUSCULES
dans une cellule "Commercial: DUBUT" ou "Acheteur: MARTINET" passe
au travers du tokeniseur PERSON classique car :
- pas de titre civil avant (M. / Mr / Mme)
- pas de pattern "Prenom Nom"
- pas de contexte personne adjacent

Strategie : detecter les libelles de cellule (Commercial, Acheteur,
Contact, Suivi par, etc.) et tokeniser le contenu QUI SUIT - soit sur
la meme ligne soit sur la ligne immediatement suivante (cas tableau
serialise PDF).
"""

from __future__ import annotations

import re

from carnaval.core.span import Span


# Libelles de cellule qui contiennent une personne (multilingue).
_PERSON_CELL_LABEL = (
    r"(?:"
    # FR
    r"Commercial(?:e)?(?:\s+\([eE]\))?"
    r"|Vendeur"
    r"|Acheteur"
    r"|Acheteuse"
    r"|Contact(?:\s+commercial)?"
    r"|Suivi\s+par"
    r"|Suivie?\s+par"
    r"|G[ée]r[ée]\s+par"
    r"|R[ée]ceptionnaire"
    r"|Signataire"
    r"|Demandeur"
    r"|Responsable(?:\s+(?:commercial|qualit[ée]|secteur|client))?"
    r"|Repr[ée]sentant"
    r"|À\s+l['’]attention\s+de"
    r"|A\s+l['’]attention\s+de"
    r"|[ÀA]\s+l['’]\s*att\.?"
    r"|Att(?:n)?\.?\s+de"
    r"|Assistant(?:e)?(?:\s+commercial(?:e)?)?"
    r"|Interlocuteur(?:\s+client)?"
    r"|Affaire\s+suivie\s+par"
    r"|Dossier\s+suivi\s+par"
    # EN
    r"|Sales\s+(?:rep|representative|contact)"
    r"|Account\s+manager"
    r"|Buyer"
    r"|Purchaser"
    r"|Contact\s+person"
    r"|Attention(?:\s+of)?"
    r"|Attn\.?"
    # DE
    r"|Ansprechpartner"
    r"|Vertrieb(?:smitarbeiter)?"
    r"|Ihre\s+Ansprechpartner"
    # ES
    r"|Vendedor"
    r"|Comercial"
    r"|Atenci[óo]n\s+de"
    # IT
    r"|Venditore"
    r"|Commerciale"
    r")"
)

# Valeur : nom de personne. Peut etre :
#   - tout en MAJUSCULES (DUBUT, MARTINET, KLEE)
#   - Title case (Dubut Pierre, M. Martinet)
#   - 1 ou 2 mots
# Refuse les libelles vides ("Commercial:") ou les telephones / emails.
_PERSON_CELL_VALUE = (
    r"(?P<value>"
    r"[A-ZÀ-Ý][A-ZÀ-Ý\-'’]{1,30}"           # CAPS uniquement (DUBUT)
    r"(?:\s+[A-ZÀ-Ý][A-ZÀ-Ýa-zà-ÿ\-'’]{1,30}){0,2}"  # +1-2 tokens
    r"|[A-ZÀ-Ý][a-zà-ÿ\-'’]{2,30}"             # Title case (Dubut)
    r"(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ\-'’]{1,30}){0,2}"
    r")"
)

# Pattern complet : libelle + separateur + valeur.
# Separateur tolerant : `: \n -` etc. mais pas trop large.
# On admet aussi le saut de ligne (layout tableau) avec une fenetre
# courte (5 chars max).
_PATTERN = re.compile(
    rf"(?u)\b{_PERSON_CELL_LABEL}"
    rf"\s*[:.\-]?\s*"
    rf"{_PERSON_CELL_VALUE}"
    rf"\b"
)


# Mots banaux a NE PAS prendre pour nom (libelles de section, mots
# techniques, mots vides en CAPS).
_NOT_A_NAME = frozenset({
    # Sections / champs documents
    "NON", "OUI", "YES", "NO",
    "TBD", "TBA", "NA", "NIL", "VOID",
    "STANDARD", "PREMIUM", "PRO", "BASIC",
    "VRAI", "FAUX", "TRUE", "FALSE",
    # Sections AR
    "CONDITIONS", "LIVRAISON", "FACTURATION", "PAIEMENT", "TVA",
    "TOTAL", "HT", "TTC", "NET", "BRUT", "REMISE",
    # Telephones / refs numeriques tronquees (rare car valeur attend
    # une lettre initiale)
    # Civilites (deja masquees ailleurs)
    "MONSIEUR", "MADAME", "MADEMOISELLE",
    # Mots metier
    "CHIMIE", "HYGIENE", "MAINTENANCE", "PRODUCTION",
    "QUALITE", "ACHATS", "VENTES", "ADV",
    # Pays / regions parfois dans cellules
    "FRANCE", "BELGIQUE", "ALLEMAGNE", "ITALIE", "ESPAGNE",
    "NORD", "SUD", "EST", "OUEST",
    # Sentinelles de mode
    "DAP", "EXW", "FCA", "CPT", "DDP", "FOB",
    "INCOTERM", "INCOTERMS",
    # Valeurs vides courantes
    "VIREMENT", "CHEQUE", "TRAITE",
})


def recognize_commercial_cell(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les noms de personne dans cellules tabulaires.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Liste de Span de type PERSON.
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()
    for m in _PATTERN.finditer(text):
        value = m.group("value")
        # Premier token de la valeur, normalise CAPS.
        first_word = value.split()[0].upper().strip(".,;:-_'")
        if first_word in _NOT_A_NAME:
            continue
        start, end = m.span("value")
        if (start, end) in seen:
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="PERSON",
                text=value,
                score=score,
                recognizer="CommercialCellRegex",
            )
        )
    return spans
