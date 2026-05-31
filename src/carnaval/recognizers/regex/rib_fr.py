# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer RIB francais (releve d'identite bancaire).

Un RIB = code banque (5) + code guichet (5) + numero de compte (11) + cle
RIB (2), soit 23 caracteres. Il est detecte lorsqu'il suit le libelle
"RIB" ; la cle de controle (mod 97) valide le candidat et ecarte les faux
positifs - par exemple "Cle RIB : 19" suivi d'autre chose ne forme pas un
RIB valide et n'est donc pas retenu.

Le RIB peut aussi etre presente eclate en champs etiquetes (Code Banque,
Code Guichet, N° de Compte, Cle RIB) ; `recognize_rib_fr_fields` masque
alors la valeur de chaque champ a partir de son libelle.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelle "RIB" isole (pas au milieu d'un mot).
_RIB_LABEL = re.compile(r"(?i)(?<![A-Za-z])RIB(?![A-Za-z])")

# Espacement / ponctuation admis entre le libelle et le RIB, et a l'interieur.
# Inclut `/` : certains AR ecrivent le RIB groupes-separes par des slashs,
# par exemple "RIB: 17629/00001/00113692800/60".
_RIB_SEP = frozenset(" \t\r\n:#-./")

_RIB_LENGTH = 23  # 5 banque + 5 guichet + 11 compte + 2 cle


def _account_digit(c: str) -> int:
    """Convertit un caractere du numero de compte en chiffre (regle RIB)."""
    if c.isdigit():
        return int(c)
    c = c.upper()
    if "A" <= c <= "I":
        return ord(c) - 64
    if "J" <= c <= "R":
        return ord(c) - 73
    return ord(c) - 81  # S..Z


def validate_rib_key(rib: str) -> bool:
    """Valide la cle de controle d'un RIB de 23 caracteres (mod 97 == 0)."""
    if len(rib) != _RIB_LENGTH:
        return False
    if not rib[:10].isdigit() or not rib[21:].isdigit():
        return False
    banque = int(rib[0:5])
    guichet = int(rib[5:10])
    compte = int("".join(str(_account_digit(c)) for c in rib[10:21]))
    cle = int(rib[21:23])
    return (banque * 89 + guichet * 15 + compte * 3 + cle) % 97 == 0


def _collect_rib(text: str, after_label: int) -> tuple[str | None, int, int]:
    """Collecte 23 caracteres alphanumeriques apres le libelle, en ignorant
    l'espacement et la ponctuation de separation.

    Tolere un nom de banque (token de lettres) entre le libelle "RIB" et la
    sequence numerique : "RIB HSBC 30056..." est frequent. Le RIB francais
    commence toujours par des chiffres (code banque sur 5 chiffres), donc
    on saute les tokens purement alphabetiques tant qu'on n'a pas trouve
    le premier chiffre.

    Returns:
        (rib, debut, fin) si 23 caracteres collectes, sinon (None, 0, 0).
    """
    # Phase 1 : skipper les tokens alphabetiques (nom de banque inline)
    # jusqu'a rencontrer le 1er chiffre. On limite a 30 chars pour
    # eviter de derive : un RIB doit etre tres proche de son libelle.
    i = after_label
    n = len(text)
    scanned = 0
    while i < n and scanned < 30:
        c = text[i]
        if c.isdigit():
            break
        if c.isascii() and c.isalpha():
            # Token alphabetique (nom de banque) : on l'absorbe.
            i += 1
            scanned += 1
            continue
        if c in _RIB_SEP:
            i += 1
            scanned += 1
            continue
        # Autre caractere -> on s'arrete.
        return None, 0, 0
    if i >= n:
        return None, 0, 0

    # Phase 2 : collecte standard du RIB sur 23 caracteres alphanumeriques.
    chars: list[str] = []
    first: int | None = None
    seps = 0
    while i < n and len(chars) < _RIB_LENGTH:
        c = text[i]
        if c.isascii() and c.isalnum():
            if first is None:
                first = i
            chars.append(c)
        elif c in _RIB_SEP:
            seps += 1
            if seps > _RIB_LENGTH + 5:
                return None, 0, 0
        else:
            break
        i += 1
    if len(chars) == _RIB_LENGTH and first is not None:
        return "".join(chars), first, i
    return None, 0, 0


# Pattern de RIB structure (groupe banque/guichet/compte/cle separes) :
# detection sans dependre du libelle "RIB". Toutes les sequences qui
# *ressemblent* a un RIB sont remontees, le checksum mod 97 filtre les
# faux positifs (probabilite ~1/97 ≈ 1% qu'une sequence aleatoire passe).
#
# Deux formes courantes :
#   "30056 00153 01532083491 67"      groupes 5-5-11-2
#   "30003-02250-000 20000703/09"     groupes 5-5-3+8-2 (banque-guichet-
#                                      compte segmente-cle), separateurs
#                                      varies (./- /)
_RIB_STRUCTURED_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?P<rib>"
    r"\d{5}[\s\-./]{1,3}\d{5}[\s\-./]{1,3}"
    r"[\dA-Z]{11}[\s\-./]{1,3}\d{2}"
    r"|\d{5}[\s\-./]{1,3}\d{5}[\s\-./]{1,3}"
    r"\d{3}[\s\-./]\d{8}[\s\-./]{1,3}\d{2}"
    r")"
    r"(?!\d)"
)


def _emit_rib(
    spans: list[Span], seen: set[tuple[int, int]],
    start: int, end: int, raw: str, score: float,
) -> None:
    """Ajoute un span RIB s'il passe la validation par checksum et n'est
    pas deja present a la meme position (dedup entre strategies)."""
    if (start, end) in seen:
        return
    clean = "".join(c for c in raw if c.isalnum())
    if len(clean) != _RIB_LENGTH:
        return
    if not validate_rib_key(clean):
        return
    seen.add((start, end))
    spans.append(
        Span(
            start=start, end=end,
            entity_type="RIB",
            text=raw,
            score=score,
            recognizer="RibFrRegex",
        )
    )


def recognize_rib_fr(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les RIB francais. Deux strategies cumulatives :

    1. **Libelle ancre** : "RIB" trouve dans le texte, on collecte 23
       caracteres alphanumeriques apres (avec tolerance d'un nom de
       banque inline) et on valide la cle. Score nominal.

    2. **Signature de checksum** : sequence structuree (groupes 5-5-11-2
       ou variante segmentee) trouvee n'importe ou dans le texte. La cle
       de controle mod 97 elimine les ~99% de faux positifs (probabilite
       1/97 qu'une sequence aleatoire de 23 chiffres passe). Score plus
       eleve car la signature mathematique est elle-meme une preuve.

    Les deux strategies remontent dans une meme liste ; le S4 resolve
    deduplique les chevauchements (un RIB libelle ET structure ne
    produit qu'un seul span final).
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()

    # Strategie 1 : libelle "RIB" + 23 chars suivants
    for m in _RIB_LABEL.finditer(text):
        candidate, start, end = _collect_rib(text, m.end())
        if candidate is None:
            continue
        _emit_rib(spans, seen, start, end, text[start:end], score)

    # Strategie 2 : signature structuree + checksum (sans libelle)
    for m in _RIB_STRUCTURED_PATTERN.finditer(text):
        start, end = m.span("rib")
        _emit_rib(spans, seen, start, end, m.group("rib"), score * 1.1)

    return spans


# --- RIB eclate en champs etiquetes (forme non contigue) -----------------

# Libelles des composantes d'un RIB lorsqu'elles sont presentees separement.
_RIB_FIELD_LABELS = (
    r"code\s+banque|code\s+guichet"
    r"|n[°o]?\s*(?:de\s+)?compte|cl[ée]\s*rib"
)

# Libelle de champ suivi de sa valeur numerique (espacement interne tolere).
_RIB_FIELD = re.compile(
    r"(?i)(?:" + _RIB_FIELD_LABELS + r")\s*:?\s*(\d(?:[\d ]*\d)?)"
)


def recognize_rib_fr_fields(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les composantes d'un RIB presentees en champs etiquetes.

    Certains releves ecrivent le RIB eclate ("Code Banque: ... Code
    Guichet: ... N° de Compte: ... Cle RIB: ...") plutot qu'en chaine
    contigue : `recognize_rib_fr` ne le voit alors pas. Chaque libelle
    est tres specifique - la valeur numerique qui le suit est masquee.
    """
    spans: list[Span] = []
    for m in _RIB_FIELD.finditer(text):
        start, end = m.span(1)
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="RIB",
                text=text[start:end],
                score=score,
                recognizer="RibFrFieldsRegex",
            )
        )
    return spans
