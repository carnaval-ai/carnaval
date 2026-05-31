# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers IBAN (longueur par pays + checksum mod 97) et BIC.

L'IBAN n'est pas detecte en modelisant sa structure en blocs de 4 : un IBAN
imprime est souvent coupe par l'extraction PDF (blocs colles, saut de ligne
au milieu, espacement irregulier). On repere le code pays, on collecte le
nombre exact de caracteres attendu pour ce pays en ignorant tout espacement,
puis on valide le checksum mod 97.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Longueur officielle de l'IBAN par pays (ISO 13616).
_IBAN_LENGTHS = {
    "AD": 24, "AE": 23, "AT": 20, "BE": 16, "BG": 22, "CH": 21, "CY": 28,
    "CZ": 24, "DE": 22, "DK": 18, "EE": 20, "ES": 24, "FI": 18, "FR": 27,
    "GB": 22, "GR": 27, "HR": 21, "HU": 28, "IE": 22, "IS": 26, "IT": 27,
    "LI": 21, "LT": 20, "LU": 20, "LV": 21, "MC": 27, "MT": 31, "NL": 18,
    "NO": 15, "PL": 28, "PT": 25, "RO": 24, "SE": 24, "SI": 19, "SK": 24,
    "SM": 27, "TR": 26,
}

# Debut d'IBAN : 2 lettres (code pays) + 2 chiffres (cle de controle).
# Un espacement entre les deux est tolere (artefact d'extraction PDF).
_IBAN_START = re.compile(r"[A-Z]{2}[ \t]?\d{2}")

# Caracteres d'espacement admis A L'INTERIEUR d'un IBAN imprime.
_IBAN_SEP = frozenset(" \t\r\n")

# BIC ISO 9362. Bordures `(?<![A-Z0-9])`/`(?![A-Z0-9])` plutot que `\b` :
# le `\b` echoue quand le BIC est colle a un caractere `_` (cf. "BNPAFRPPXXX____"
# en pied de page apres un IBAN tronque). `_` etant `\w` en regex Python,
# `\b` est faux ; ici on borne strictement sur lettres et chiffres.
BIC_PATTERN = re.compile(
    r"(?<![A-Z0-9])[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?(?![A-Z0-9])"
)
# Le contexte BIC inclut aussi les libelles bancaires usuels qui accompagnent
# souvent un BIC sans qu'il soit explicitement annonce "BIC:" ou "SWIFT:" :
# "Règlement : VIREMENT SG - SOGEFRPP", "Domiciliation BNP Paribas BNPAFRPP".
BIC_CONTEXT = (
    "BIC", "SWIFT", "B.I.C",
    "VIREMENT", "REGLEMENT", "RÈGLEMENT", "DOMICILIATION", "IBAN", "RIB",
)


def validate_iban_checksum(text: str) -> bool:
    """Validation IBAN par mod 97 = 1."""
    cleaned = "".join(c for c in text.upper() if c.isalnum())
    if len(cleaned) < 15 or len(cleaned) > 34:
        return False
    rearranged = cleaned[4:] + cleaned[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def _collect_iban(text: str, start: int, length: int) -> tuple[str | None, int]:
    """Collecte `length` caracteres alphanumeriques a partir de `start`.

    Les espacements internes (espace, tab, saut de ligne) sont ignores : un
    IBAN coupe par l'extraction PDF reste capture. Tout autre caractere
    termine la collecte. Un exces d'espacement (> length) interrompt :
    on ne traverse pas du texte hors IBAN.

    Returns:
        (chaine_iban, position_de_fin) si `length` caracteres collectes,
        sinon (None, start).
    """
    chars: list[str] = []
    seps = 0
    i = start
    n = len(text)
    while i < n and len(chars) < length:
        c = text[i]
        if c.isascii() and c.isalnum():
            chars.append(c)
        elif c in _IBAN_SEP:
            seps += 1
            if seps > length:
                return None, start
        else:
            break  # caractere etranger : fin de l'IBAN potentiel
        i += 1
    if len(chars) == length:
        return "".join(chars), i
    return None, start


# Libelles bancaires qui, places juste avant une sequence ressemblant a un
# IBAN, suffisent a confirmer l'intention "ceci EST un IBAN" - meme si le
# checksum mod 97 est invalide. Cas frequent : IBAN fictif d'un AR de test,
# IBAN saisi a la main avec une typo, ou OCR ayant deforme un caractere.
# Sans ce fallback, l'IBAN reste en clair dans le texte anonymise et fuit.
_IBAN_CONTEXT_PREFIXES = (
    "IBAN", "I.B.A.N", "RIB", "R.I.B",
    "COMPTE", "ACCOUNT", "KONTO", "KONTONUMMER",
    "REFERENCE BANCAIRE", "REFERENCES BANCAIRES",
    # ES / IT / PT
    "CUENTA", "CUENTA BANCARIA", "BANCO",
    "CONTO", "CONTO CORRENTE",
    "CONTA", "CONTA BANCARIA",
    # TR : "Banka Bilgileri" (informations bancaires), "Hesap" (compte),
    # "Hesap Numarasi" (numero de compte). Compare en upper().
    "HESAP", "HESAP NUMARASI",
    "BANKA BILGILERI", "BANKA",
    # CZ / SK : "Bankovní spojení" (coordonnees bancaires), "Číslo
    # účtu" (numero de compte). Compare en upper() apres deaccent
    # (le `.upper()` Python sur "í" donne "Í").
    "BANKOVNI SPOJENI", "BANKOVNÍ SPOJENÍ",
    "CISLO UCTU", "ČÍSLO ÚČTU",
    "UCET", "ÚČET",
    # CN / JP : noms de banque et libelles "compte" en ideogrammes.
    # NB : la Chine et le Japon n'utilisent pas l'IBAN ; ces libelles
    # sont conserves pour homogeneite quand un AR mentionne un IBAN
    # europeen dans un contexte chinois/japonais.
    "银行账号", "银行账户", "账号", "账户", "开户行",   # CN
    "口座番号", "口座", "銀行口座", "振込先",          # JP
    # BG : "Банка", "Сметка", "Банкова сметка", "IBAN" (deja couvert).
    # On compare en upper() cyrillique : "банка".upper() == "БАНКА".
    "БАНКА", "СМЕТКА", "БАНКОВА СМЕТКА", "БАНКОВИ ДАННИ",
)
_IBAN_CONTEXT_WINDOW = 30  # caracteres


def _has_iban_context(text: str, start: int, window: int = _IBAN_CONTEXT_WINDOW) -> bool:
    """True si un libelle bancaire explicite precede le candidat dans la
    fenetre `window`. Compare en majuscules pour ignorer la casse."""
    before = text[max(0, start - window): start].upper()
    return any(kw in before for kw in _IBAN_CONTEXT_PREFIXES)


def recognize_iban(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les IBAN.

    Pour chaque debut `XX##`, collecte la longueur attendue pour le pays
    puis valide le checksum mod 97. Le span couvre l'IBAN tel qu'imprime,
    espacement interne compris.

    Fallback contextuel : si le checksum est invalide MAIS qu'un libelle
    `IBAN` / `RIB` / `Compte` / equivalent multilingue est dans les
    `_IBAN_CONTEXT_WINDOW` caracteres precedents, on masque quand meme
    avec un score reduit. Cela couvre les IBAN fictifs (AR de test), les
    typos de saisie, et les caracteres deteriores par l'OCR. Mieux vaut
    un faux positif sur un nombre identifie comme bancaire qu'une fuite
    silencieuse d'un IBAN reel.
    """
    spans: list[Span] = []
    for m in _IBAN_START.finditer(text):
        country = m.group(0)[:2]
        length = _IBAN_LENGTHS.get(country)
        if length is None:
            continue
        candidate, end = _collect_iban(text, m.start(), length)
        if candidate is None:
            continue
        if validate_iban_checksum(candidate):
            local_score = score
        elif _has_iban_context(text, m.start()):
            local_score = max(0.6, score - 0.15)
        else:
            continue
        spans.append(
            Span(
                start=m.start(),
                end=end,
                entity_type="IBAN",
                text=text[m.start():end],
                score=local_score,
                recognizer="IbanRegex",
            )
        )
    return spans


def _has_bic_context(text: str, start: int, end: int, window: int = 30) -> bool:
    """True si un mot-cle BIC/SWIFT est a proximite, ou si le match commence
    par BIC (textes parasites colles type 'BICAAAAFR2XXXX')."""
    matched = text[start:end].upper()
    if matched.startswith(("BIC", "SWIFT")):
        return True
    before = text[max(0, start - window) : start].upper()
    after = text[end : end + window].upper()
    return any(kw in before or kw in after for kw in BIC_CONTEXT)


# Mots francais / anglais en majuscules de longueur 8 qui ressemblent
# a un BIC mais n'en sont pas. Sans ce filtre, "VIREMENT" / "MATERIEL"
# se font masquer en BIC, ce qui est cosmetique mais salissant.
_BIC_NOISE_WORDS: frozenset[str] = frozenset({
    "VIREMENT", "MATERIEL", "BORDEREAU", "REFERENCE", "REFERENCES",
    "PROTOCOLE", "ACOMPTE", "FACTURES", "FACTURE",
    "DOMICILE", "ETRANGER", "DELIVREE", "DELIVREES",
    "BORDEREAUX", "COMPTABLE",
})


def recognize_bic(text: str, score: float = 0.7) -> list[Span]:
    """BIC : ne produit un Span que si BIC/SWIFT est proche.

    Sans contexte, le pattern matcherait n'importe quel mot de 8+ majuscules.
    Filtre additionnel : un BIC qui est en realite un mot francais/anglais
    courant en majuscules (VIREMENT, MATERIEL...) est rejete - c'est un
    faux positif structurel du pattern ISO 9362 vu de loin.

    Detection elargie : un BIC qui SUIT IMMEDIATEMENT un IBAN (separe
    par tiret, virgule, slash, espace) est conserve meme sans libelle
    explicite "BIC:". Cas tres frequent : "RIB : FR76 ... - NORDFRPP".
    """
    spans: list[Span] = []
    iban_spans = recognize_iban(text)
    for m in BIC_PATTERN.finditer(text):
        if m.group(0) in _BIC_NOISE_WORDS:
            continue
        if _has_bic_context(text, m.start(), m.end()):
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    entity_type="BIC",
                    text=m.group(0),
                    score=score,
                    recognizer="BicRegex",
                )
            )
            continue
        # Pas de mot-cle BIC explicite : on regarde si un IBAN se termine
        # juste avant (au plus 5 caracteres : un separateur tiret/slash
        # eventuellement espacement).
        if any(0 <= m.start() - iban.end <= 5 for iban in iban_spans):
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    entity_type="BIC",
                    text=m.group(0),
                    score=max(0.6, score - 0.1),
                    recognizer="BicRegex",
                )
            )
    return spans
