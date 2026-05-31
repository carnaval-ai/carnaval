# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Signaux legaux en pied de document : code APE, capital social.

Vecteurs d'attaque red-team (audit P2) :
    V4 - Code APE / NAF : "APE 4669B", "NAF 2562B". Restreint le secteur
         d'activite a un code precis. Combine avec une raison sociale ou
         un capital, identifie l'entreprise dans son segment.
    V7 - Capital social : "capital de 1 100 000 €". Le montant exact du
         capital est une donnee publique recoupable via les registres
         entreprises. Combine a un APE ou un SIREN partiel, identifie
         l'entreprise a quelques candidats voire un seul.

Strategie : capture par libelle contextuel ferme. Le libelle "APE" ou
"capital" est tres specifique et le faux positif est quasi nul.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span


# === V4 - Code APE / NAF ===

# Format APE/NAF francais : 4 chiffres + 1 lettre (ex 4669B, 4662Z,
# 3319Z, 2562B, 2815Z, 2894Z). Libelle obligatoire pour eviter de
# matcher un code postal voisin.
_APE_PATTERN = re.compile(
    r"(?i)(?:APE|NAF|Code\s+(?:APE|NAF))"
    r"\s*[:.\-/]?\s*"
    r"(?P<value>\d{4}\s?[A-Z])"
    r"(?!\d)"
)

# Audit v3 VNN4 : APE en suffixe d'abreviation post-SIRET. Cas observe
# (Keyence) : "N°Siret : [SIRET_1].[ORG] : 4669B" - le code 4669B reste
# en clair apres l'abréviation `N.APE` mal interprétée par GLiNER.
# Pattern : 4 chiffres + 1 lettre AVEC un contexte SIRET/SIREN/RCS
# dans une fenetre de +/- 3 lignes (sinon risque de matcher un code
# postal voisin ou une reference produit).
_APE_ORPHAN_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?P<value>\d{4}\s?[A-Z])(?![A-Z0-9])"
)

_APE_CONTEXT_MARKERS = re.compile(
    r"(?i)\b(?:SIRET|SIREN|RCS|N\.?\s*APE|N\.?\s*NAF|TVA\s+intracom)"
)


def _has_ape_context(text: str, pos: int, window_lines: int = 3) -> bool:
    """True si un libelle fiscal (SIRET/SIREN/RCS/APE/NAF) est present
    dans une fenetre de +/- window_lines lignes autour de pos."""
    cursor = pos
    for _ in range(window_lines):
        nl = text.rfind("\n", 0, cursor)
        if nl < 0:
            cursor = 0
            break
        cursor = nl
    window_start = cursor
    cursor = pos
    for _ in range(window_lines + 1):
        nl = text.find("\n", cursor + 1)
        if nl < 0:
            cursor = len(text)
            break
        cursor = nl
    window_end = cursor
    return bool(_APE_CONTEXT_MARKERS.search(text[window_start:window_end]))


def recognize_ape_code(text: str, score: float = 0.92) -> list[Span]:
    """Detecte les codes APE/NAF francais.

    Deux strategies :
    1. Libelle ancre direct ("APE 4669B", "NAF 2811Z").
    2. Recuperation post-abreviation (audit v3 VNN4) : code 4 chiffres
       + 1 lettre isole, valide par contexte SIRET/SIREN/RCS dans
       +/- 3 lignes - couvre les cas ou l'abreviation `N.APE` a ete
       tokenisée et laisse le code APE orphelin.
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()

    # Strategie 1 : libelle ancre direct
    for m in _APE_PATTERN.finditer(text):
        start, end = m.span("value")
        if (start, end) in seen:
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="APE_CODE",
                text=m.group("value"),
                score=score,
                recognizer="ApeCodeRegex",
            )
        )

    # Strategie 2 : code orphelin + contexte fiscal a proximite
    for m in _APE_ORPHAN_PATTERN.finditer(text):
        start, end = m.span("value")
        if (start, end) in seen:
            continue
        if not _has_ape_context(text, start):
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="APE_CODE",
                text=m.group("value"),
                score=score * 0.9,
                recognizer="ApeCodeRegex",
            )
        )

    return spans


# === V7 - Capital social ===

# Pattern : "capital" / "capital social" / "au capital" suivi d'un
# montant numerique (chiffres + separateurs espace/virgule/point) +
# optionnel "EUR" / "€" / "Euros".
# Multilingue : capital / Stammkapital / capitale sociale / capital
# social (ES/PT) / spolkowy / kapital.
_CAPITAL_PATTERN = re.compile(
    r"(?ui)(?:"
    # FR : "au capital", "au capital social", "au capital de",
    # "au capital social de" + variantes
    r"au\s+capital(?:\s+social)?(?:\s+de)?"
    r"|capital(?:\s+social)?(?:\s+de)?"
    # EN (audit v3 R1) : "share capital of X €" / "with a share capital"
    r"|(?:share\s+capital|company\s+capital)(?:\s+of)?"
    # DE
    r"|Stamm-?kapital(?:\s+von)?"
    r"|Grundkapital(?:\s+von)?"
    # IT
    r"|capitale\s+sociale(?:\s+di)?"
    # PT (capital social comme FR/ES, deja couvert)
    # PL
    r"|kapita[łl]\s+(?:zak[łl]adowy|sp[óo][łl]ki)"
    # CZ
    r"|z[áa]kladn[íi]\s+kapit[áa]l"
    # TR
    r"|sermayesi|kuruluş\s+sermayesi"
    r")"
    # Separateur entre libelle et valeur. Format tabulaire eclate
    # observe (auditeur v2 VN4) : "Capital\n450 000\n€\n" sur 3 lignes.
    # Borne 30 chars max empeche de matcher un nombre distant non-lie.
    # Audit v3 R2 : on accepte aussi "€" / "EUR" devant le montant
    # ("au capital de € 240.000") - ajout de `€EUR` aux chars autorises.
    r"[^A-Za-z\d]{0,30}"
    r"(?P<value>"
    # Avec separateurs de milliers : "1 100 000", "1.100.000",
    # "1,100,000". Separateur restreint a `[ \t.,]` (PAS `\s` qui
    # inclut `\n`) - sinon le pattern absorbe la ligne suivante
    # (cas observe : "450 000\n57645004300038" matchait "450 000\n576"
    # en grignotant le SIRET de la ligne suivante).
    r"\d{1,3}(?:[ \t.,]\d{3})+(?:[,.]\d{1,2})?"
    # Sans separateurs : "518500", "7622" (au moins 4 chiffres
    # consecutifs - garde-fou contre des montants ridiculement petits).
    r"|\d{4,}(?:[,.]\d{1,2})?"
    r")"
    r"\s*(?:€|EUR(?:OS?)?|euros?|EURO?|PLN|CZK|TL)?"
)


# === Numero d'enregistrement WEEE ===
# Identifiant fiscal d'entreprise pour les dechets electriques (UE).
# Format observe : "WEEE-Reg.-Nr. DE 23055661". Identifie l'emetteur
# via le registre EAR (Allemagne) ou equivalents nationaux.
_WEEE_PATTERN = re.compile(
    r"(?i)WEEE[-\s]*(?:Reg\.?[-\s]*Nr\.?)?"
    r"\s*[:.]?\s*"
    r"(?P<value>[A-Z]{2}\s?\d{6,10})"
)


def recognize_weee(text: str, score: float = 0.92) -> list[Span]:
    """Detecte les numeros d'enregistrement WEEE (dechets electriques UE)."""
    spans: list[Span] = []
    for m in _WEEE_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="VAT",
                text=m.group("value"),
                score=score,
                recognizer="WeeeRegex",
            )
        )
    return spans


def recognize_capital(text: str, score: float = 0.9) -> list[Span]:
    """Detecte le montant du capital social en mention legale."""
    spans: list[Span] = []
    for m in _CAPITAL_PATTERN.finditer(text):
        start, end = m.span("value")
        value = m.group("value").strip()
        # Au moins 4 chiffres pour eviter de matcher des nombres courts
        # ("au capital de 1") improbables.
        if sum(1 for c in value if c.isdigit()) < 4:
            continue
        spans.append(
            Span(
                start=start, end=end,
                entity_type="CAPITAL",
                text=value,
                score=score,
                recognizer="CapitalRegex",
            )
        )
    return spans
