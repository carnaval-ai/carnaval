# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer "nom de banque par contexte".

Quand GLiNER manque un nom de banque qui suit le libelle `Banque :` ou
`Bank :`, le nom du teneur de compte fournisseur reste en clair :

    Banque : Société Marseillaise de Crédit          <- fuite

On capture explicitement le pattern `Banque\\s*:\\s*<nom>` (FR / EN /
DE / multilingue minimal). Seul le nom est masque ; le libelle reste en
clair pour la lisibilite du document anonymise.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelles ancrant un nom de banque.
_LABEL = (
    r"(?:"
    r"Banque|Banco|Bank|Banca|Bancaria"
    r"|Domiciliation\s+bancaire|Domiciliation"
    r"|Coordonn[ée]es\s+bancaires"
    # PT / ES bank details labels
    r"|Dados\s+banc[áa]rios|Datos\s+bancarios"
    r"|Detalhes\s+banc[áa]rios|Detalles\s+bancarios"
    # IT / DE
    r"|Dati\s+bancari|Coordinate\s+bancarie"
    r"|Bankverbindung|Bankdaten"
    # TR : "Banka", "Banka Bilgileri" (infos bancaires), "Hesap"
    r"|Banka(?:\s+Bilgileri)?"
    r"|Hesap(?:\s+Bilgileri)?"
    # CZ / SK : "Bankovní spojení" (coordonnees bancaires), "Číslo
    # účtu" (numero de compte), "Účet" (compte).
    r"|Bankovn[íi]\s+spojen[íi]"
    r"|[ČC][íi]slo\s+[úu][čc]tu"
    r"|[ÚU][čc]et"
    # CN / JP : libelles ideogrammes pour banque / coordonnees /
    # ouverture de compte / virement.
    r"|开户行|银行账户|银行账号|账户名|账户"
    r"|振込先|銀行口座|口座番号"
    # BG : Банка / Банкова сметка / Банкови данни (cyrillique).
    r"|[Бб]анка"
    r"|[Бб]анкова\s+сметка"
    r"|[Бб]анкови\s+данни"
    r"|[Сс]метка"
    r")"
)

# Nom de banque : 2 a 6 tokens, chacun en majuscule initiale, tolere les
# minuscules pour les particules (de / la / du / le / et / & / etc.).
# Le pattern s'arrete au premier caractere non textuel (saut de ligne,
# tiret avec espace, parenthese, virgule suivie de fin de ligne).
_NAME_TOKEN = r"[A-ZÉÈÀÂÊÎÔÛÇ][\wÀ-ÿ\-'’\.]*"
_PARTICLE = r"(?:de|du|des|la|le|les|et|à|au|aux|d[’'])"
_NAME = (
    rf"{_NAME_TOKEN}"
    rf"(?:\s+(?:{_PARTICLE}|{_NAME_TOKEN}|&)){{1,8}}"
)

# Pattern : libelle + : + nom (sans depasser la ligne).
_BANK_PATTERN = re.compile(
    rf"(?:^|\n)\s*{_LABEL}\s*[:\-]\s*(?P<bank>{_NAME})"
)

# Pattern alternatif : nom de banque DANS LE FLUX (sans label en
# debut de ligne). Cas typique : "BIC: BESCPTPL - Novo Banco, agencia
# Coimbra" - le mot "Banco" est noyau du nom, encadre par des mots
# commencant par une majuscule. Couvre :
#   - "Novo Banco" (modificateur avant), "Deutsche Bank", "Banco
#     Santander", "Banca Generali", "Ziraat Bankasi" (TR)
#   - composes plus longs : "Credit Mutuel Bank"
# Le pattern exige AU MOINS un autre mot autour du noyau pour eviter
# de masquer "Banco" / "Bank" tout court (un libelle vide).
# "Bankasi/Bankası" : forme genitive turque "banque de X".
_BANK_CORE = r"(?:Banco|Banca|Bank|Banque|Banka|Bankas[ıi]|银行|銀行)"
_BANK_BEFORE = r"(?:[A-Z][A-Za-zÀ-ÿ\-]+\s+){1,2}"
_BANK_AFTER = r"(?:\s+[A-Z][A-Za-zÀ-ÿ\-]+){1,3}"
_BANK_INLINE_PATTERN = re.compile(
    rf"(?<![A-Za-z])"
    rf"(?P<bank>{_BANK_BEFORE}{_BANK_CORE}|{_BANK_CORE}{_BANK_AFTER})"
    rf"(?![A-Za-z])"
)

# Pattern alternatif CJK : nom de banque chinois/japonais construit
# autour du noyau ideographique 银行 (simplifie chinois) / 銀行
# (traditionnel chinois + japonais). En CJK pas de separateurs de
# mots : on capture les ideogrammes contigus juste avant le noyau
# (1 a 8 caracteres dont kanji + katakana + ASCII pour les noms
# hybrides type "三菱UFJ銀行"). Pas de stopwords ici - les libelles
# de section CJK qui se terminent par 银行/銀行 sont rares (presque
# toujours un nom de banque).
_BANK_INLINE_CJK_PATTERN = re.compile(
    r"(?P<bank>"
    # 1-8 caracteres parmi : Han Unified (一-鿿), Hiragana (ぁ-ゖ),
    # Katakana (ァ-ヺ), ASCII majuscules + chiffres, pour les noms
    # hybrides du type "三菱UFJ銀行" ou "みずほ銀行".
    r"[一-鿿ぁ-ゖァ-ヺA-Z0-9]{1,8}(?:银行|銀行)"
    r")"
)
# Mots qui pourraient preceder "Banco/Bank" mais ne forment PAS un nom
# (libelles ordinaires, faux positifs). En lowercase normalise.
_BANK_INLINE_STOPWORDS = frozenset({
    "the", "le", "la", "el", "los", "las", "ein", "eine", "der", "die", "das",
    "this", "our", "your", "his", "her", "their", "any", "some", "every",
    "from", "to", "for", "with", "by", "in", "on", "at",
    "outra", "nossa", "vossa",  # PT articles
    "otra", "nuestra", "vuestra",  # ES
    "autre", "votre", "notre",  # FR
})

# Suiveurs qui ne sont pas un nom de banque (ex: "Banque : à compléter").
_STOP_FOLLOWERS = frozenset({
    "a", "à", "voir", "see", "todo", "non", "renseigner", "completer",
    "completar", "siehe",
})


def recognize_bank_by_context(text: str, score: float = 0.8) -> list[Span]:
    """Detecte un nom de banque suivant un libelle `Banque:` / `Bank:` / etc.

    Args:
        text: texte source.
        score: confiance du recognizer.

    Returns:
        Liste de Spans `ORGANIZATION` (type generique : un nom de banque
        EST une organisation, et l'utilisation du type ORGANIZATION permet
        a la propagation et au mecanisme de placeholders existants de le
        traiter comme un nom propre standard).
    """
    spans: list[Span] = []
    for m in _BANK_PATTERN.finditer(text):
        start, end = m.span("bank")
        name = m.group("bank").strip()
        if not name:
            continue
        first_token = name.split()[0]
        if first_token.lower() in _STOP_FOLLOWERS:
            continue
        # On ajuste la fin du span : si le nom contient un saut de ligne
        # capture par hasard, on tronque (le regex est ancre sur la ligne
        # mais on garde une ceinture).
        nl = name.find("\n")
        if nl != -1:
            name = name[:nl].rstrip()
            end = start + len(name)
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="ORGANIZATION",
                text=name,
                score=score,
                recognizer="BankByContextRegex",
            )
        )
    # Pattern inline : nom de banque sans libelle dedie (Novo Banco,
    # Deutsche Bank, Banco Santander...).
    for m in _BANK_INLINE_PATTERN.finditer(text):
        start, end = m.span("bank")
        name = m.group("bank").strip()
        if not name:
            continue
        first_token = name.split()[0].lower()
        if first_token in _BANK_INLINE_STOPWORDS:
            continue
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="ORGANIZATION",
                text=name,
                score=max(0.6, score - 0.1),
                recognizer="BankByContextRegex",
            )
        )
    # Pattern CJK distinct : noms de banque a base d'ideogramme
    # 银行 / 銀行. Pas de split de tokens en CJK (pas de blanc).
    for m in _BANK_INLINE_CJK_PATTERN.finditer(text):
        start, end = m.span("bank")
        name = m.group("bank").strip()
        if not name:
            continue
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="ORGANIZATION",
                text=name,
                score=max(0.6, score - 0.1),
                recognizer="BankByContextRegex",
            )
        )
    return spans
