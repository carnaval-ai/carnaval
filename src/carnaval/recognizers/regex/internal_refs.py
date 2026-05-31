# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Reference interne au fournisseur : BL, RMA, AR, SC, Cde, etc.

Vecteur d'attaque red-team V9 : les numeros internes du fournisseur
(bon de livraison, retour marchandise, accuse reception interne...)
sont specifiques et opposables. Permettent :
    - d'identifier le fournisseur s'il intercepte le document
    - de pivoter vers d'autres documents si l'attaquant en collecte
      plusieurs

Strategie : detection par libelle contextuel ferme + format alphanum
court. Exemples observes :
    "BL-25-00229"          (bon de livraison)
    "RMA-24/00189"         (retour marchandise)
    "SC00072539"           (sales confirmation)
    "AR-2024-001"          (accuse de reception)
    "CC25030026PZ"         (confirmation commande)
    "AFH/070EHZ/Q29890"    (numero d'affaire)
"""

from __future__ import annotations

import re

from carnaval.core.span import Span


# Pattern : libelle + valeur. La valeur est alphanumerique avec tirets,
# slashes ou points, 4 a 20 caracteres, contenant au moins 1 chiffre.
_INTERNAL_REF_PATTERN = re.compile(
    r"(?i)"
    # Libelles : BL, RMA, AR, SC, CC, Cde, no de Cde, etc.
    # Bordure de mot devant pour eviter de matcher dans un mot ("ARRIVE").
    r"(?<![A-Za-z])"
    r"(?:"
    # Bon de livraison
    r"BL(?:\s*N[°o]\.?)?"
    r"|Bon\s+de\s+livraison(?:\s*N[°o]\.?)?"
    # Retour marchandise
    r"|RMA(?:\s*N[°o]\.?)?"
    # Accuse de reception interne — LES LABELS SUIVANTS sont AUTO-REFERENTIELS
    # dans un document AR (ils designent le document lui-meme, pas une fuite).
    # Ils ne sont actifs que si le document n'est PAS un AR (cas mail, contrat
    # qui mentionne un AR tiers). Cf. filtre `_is_self_referent` ci-dessous.
    r"|AR(?:\s*N[°o]\.?)?"
    r"|Accus[ée]\s+(?:de\s+)?r[ée]ception(?:\s*N[°o]\.?)?"
    # Sales confirmation / Confirmation commande
    r"|SC(?:\s*N[°o]\.?)?"
    r"|CC(?:\s*N[°o]\.?)?"
    r"|Confirmation\s+(?:de\s+)?commande(?:\s*N[°o]\.?)?"
    # Notre commande / Notre reference fournisseur
    r"|Notre\s+(?:r[ée]f[ée]rence|n[°o]|cde)"
    r"|Nos?\s+r[ée]f\.?"
    # Numero d'affaire / dossier
    r"|N[°o]\s*(?:d['’])?affaire"
    r"|R[ée]f[ée]rence\s+(?:affaire|dossier)"
    r"|Affaire\s+N[°o]\.?"
    r"|Dossier\s+(?:n[°o]\.?|de\s+r[ée]f)"
    # EN
    r"|Order\s+ack(?:nowledgement)?"
    r"|Delivery\s+note"
    r"|Confirmation\s+(?:number|n[°o]\.?)"
    # DE
    r"|Auftragsbest[äa]tigung(?:\s*Nr\.?)?"
    r"|Lieferschein(?:\s*Nr\.?)?"
    # ES
    r"|Albar[áa]n(?:\s+n[°ºo]\.?)?"
    r"|Confirmaci[óo]n\s+pedido"
    r")"
    r"\s*[:.\-/#]?\s*"
    # Valeur : alphanum + separateurs, 4-25 chars, >=1 chiffre.
    r"(?P<value>[A-Z0-9][A-Z0-9\-/]{3,24})"
    r"(?![A-Za-z0-9])"
)


def _has_at_least_one_digit(s: str) -> bool:
    return any(c.isdigit() for c in s)


# Detection AR : si le document contient l'un de ces libelles caracteristiques,
# c'est un AR/Confirmation et les numeros internes qui suivent les libelles
# auto-referentiels ne sont pas a anonymiser (donnees metier du document).
_AR_DOC_HEADER_LABELS = re.compile(
    r"(?:"
    r"Accus[ée]\s+(?:de\s+)?r[ée]ception"
    r"|Confirmation\s+(?:de\s+)?commande"
    r"|Auftragsbest[äa]tigung"
    r"|Order\s+confirmation"
    r"|Acknowledgment\s+of\s+order"
    r"|Sales\s+confirmation"
    r"|Confirmaci[óo]n\s+(?:de\s+)?pedido"
    r"|Conferma\s+d['']?ordine"
    r"|Confirma[çc][ãa]o\s+(?:de\s+)?encomenda"
    r"|Potwierdzenie\s+zam[oó]wienia"
    r"|Siparis\s+onayi"
    r"|注文\s*確認|チュウモン\s*カクニン"
    r")",
    re.IGNORECASE,
)


def _is_self_referent_ar_document(text: str) -> bool:
    """True si le document est un AR/Confirmation : presence d'un libelle
    caracteristique en en-tete (top 2000 chars). Couvre les layouts
    complexes (en-tete CGV/RCS de 500+ chars avant le titre)."""
    header = text[:2000] if len(text) > 2000 else text
    return bool(_AR_DOC_HEADER_LABELS.search(header))


def recognize_internal_ref(text: str, score: float = 0.88) -> list[Span]:
    """Detecte les references internes au fournisseur.

    Comportement v8 : si le document est lui-meme un AR/Confirmation
    (libelle detecte en en-tete), on n'anonymise PAS les valeurs qui
    suivent les libelles auto-referentiels (AR, Accuse de reception,
    SC, Confirmation de commande, Auftragsbestaetigung). Ces valeurs
    sont des donnees metier extractibles, pas de la PII.
    """
    is_self_ref = _is_self_referent_ar_document(text)
    spans: list[Span] = []
    for m in _INTERNAL_REF_PATTERN.finditer(text):
        value = m.group("value")
        if not _has_at_least_one_digit(value):
            continue
        # Filtre : valeur ne doit pas etre uniquement un mot du
        # vocabulaire (rare car >=1 chiffre exige, mais garde-fou).
        # Si le doc est un AR auto-referentiel, on regarde le label qui
        # precede : si c'est un label auto-referentiel, on skip.
        if is_self_ref:
            # Le match commence par le libelle. On verifie si ce libelle
            # est dans la liste auto-referentielle.
            label_start = m.start()
            label_zone = text[label_start:m.start("value")].rstrip()
            if re.match(
                r"(?i)\s*(?:AR(?:\s*N[°o]\.?)?"
                r"|Accus[ée]\s+(?:de\s+)?r[ée]ception(?:\s*N[°o]\.?)?"
                r"|SC(?:\s*N[°o]\.?)?"
                r"|CC(?:\s*N[°o]\.?)?"
                r"|Confirmation\s+(?:de\s+)?commande(?:\s*N[°o]\.?)?"
                r"|Auftragsbest[äa]tigung(?:\s*Nr\.?)?"
                r"|Confirmaci[óo]n\s+pedido)\s*[:.\-/#]?\s*$",
                label_zone,
            ):
                continue  # auto-referentiel, skip
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="INTERNAL_REF",
                text=value,
                score=score,
                recognizer="InternalRefRegex",
            )
        )
    return spans
