# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer des "en-tetes commerciaux" atypiques.

Deux patterns frequents sur les AR fournisseurs echappent aux
recognizers standards :

1. **Acronymes pointes isoles sur leur ligne** : `J.E.L`, `M.E.D`,
   `T.O.M`. Ces sigles servent de bandeau visuel en haut du document.
   GLiNER les manque (mots tres courts, format atypique) et org_suffix
   demande un suffixe juridique. Resultat : l'acronyme du fournisseur
   reste en clair.

2. **Marques avec suffixe symbole** : `polymères+`, `Adidas®`,
   `Coca-Cola™`. Le `+`/`®`/`™` indique un nom commercial mais GLiNER
   ne les detecte pas systematiquement, surtout si le mot principal
   est en minuscules.

On capture ces deux familles via deux patterns courts, en EXIGEANT que
le candidat soit ISOLE sur sa ligne (bord ligne -> bord ligne, eventuellement
entoure de blancs / ponctuation legere). Cette contrainte d'isolement
ecarte les acronymes integres dans la prose (`U.S.A.`, `C.G.V.`,
`art. R.123-1`) et les marques mentionnees dans une phrase.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# 1) Acronyme pointe : au moins 2 lettres en majuscules separees par
#    des points. Le dernier point est optionnel.
_DOTTED_ACRONYM = (
    r"[A-Z](?:\.[A-Z]){1,5}\.?"
)

# 2) Marque avec suffixe symbole : un mot d'au moins 3 caracteres
#    (minuscules ou majuscules, accents permis, tirets internes admis)
#    suivi DIRECTEMENT d'un symbole commercial : + / R en exposant / TM.
_BRAND_SUFFIX = (
    r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{2,}[+®™]"
)

# Pattern global : un des deux acronymes en debut de ligne, eventuellement
# precede / suivi de blancs et de petite ponctuation (| - = + parentheses).
# Le sigle DOIT etre isole (bord ligne) pour eviter les faux positifs.
_COMPANY_HEADER_PATTERN = re.compile(
    rf"(?:^|\n)\s*[|=\-]*\s*(?P<acr>{_DOTTED_ACRONYM}|{_BRAND_SUFFIX})"
    rf"(?=\s*(?:[|\-=]|\n|$))"
)

# Acronymes pointes a NE PAS masquer (faux positifs courants).
_ACRONYM_WHITELIST = frozenset({
    "U.S.A.", "U.S.A", "U.K.", "U.K",
    "C.G.V.", "C.G.V",
    "T.V.A.", "T.V.A",
    "R.C.S.", "R.C.S",
    "S.A.S.", "S.A.S", "S.A.R.L.", "S.A.R.L", "S.A.", "S.A",
    "E.U.", "E.U",
    "P.J.", "P.J",
    "C.G.A.", "C.G.A",
    "P.S.", "P.S",
    "N.B.", "N.B",
})


def recognize_company_header(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les acronymes pointes ou marques a suffixe symbole isoles.

    Le Span produit est de type ORGANIZATION pour beneficier de la
    propagation et de la coherence des placeholders standards.
    """
    spans: list[Span] = []
    for m in _COMPANY_HEADER_PATTERN.finditer(text):
        start, end = m.span("acr")
        value = m.group("acr")
        if value in _ACRONYM_WHITELIST:
            continue
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="ORGANIZATION",
                text=value,
                score=score,
                recognizer="CompanyHeaderRegex",
            )
        )
    return spans
