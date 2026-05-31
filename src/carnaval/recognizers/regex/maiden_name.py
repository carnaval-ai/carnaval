# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer pour les noms de jeune fille / noms d'usage.

Le nom de naissance d'une personne (donne dans une formule type
"(nee X)", "(geboren X)", "born X") est une PII RGPD au meme titre que
le nom d'usage. GLiNER l'inclut rarement dans son span - probablement
parce que la civilite et le nom marital dominent la fenetre - et le nom
de jeune fille reste alors en clair entre parentheses.

On capture explicitement le pattern `(?:née|nee|born|geboren) <Nom>` :
seul le nom est remonte comme Span PERSON, le libelle reste en clair.

Couvre FR / EN / DE / ES / IT.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelle "ne sous le nom de".
#
# Cas FR : on EXIGE l'accent (`née`, `nee`) - sans cela le mot vide
# "NE" / "ne" de la prose francaise (verbe : "ne pas inclure", "ne sont
# pas") matcherait et masquerait des mots ordinaires en aval. Le `nee`
# sans accent reste accepte parce que les extractions PDF perdent souvent
# les diacritiques.
#
# Cas EN / DE / ES / IT : tokens distinctifs (born, geboren, nacida,
# nata), pas de risque de confusion avec un mot vide en majuscule.
_LABEL_FR = r"(?:n[ée]e|nee)"                          # case-sensitive
# IGNORECASE OK : tokens distinctifs sans collision avec mot vide.
# - TR : "kızlık soyadı" (nom de jeune fille) - on tolere k/K et i/ı.
# - CZ/SK : "rozená/rozený/rozené" (nee, masculin/feminin/neutre).
_LABEL_OTHER = (
    r"(?:born|geboren(?:e)?|nacida|nata"
    r"|k[ıi]zl[ıi]k\s+soyad[ıi]"
    r"|rozen[áaýyé]"
    # BG : моминско име / моминска фамилия (nom de jeune fille).
    # Caracteres cyrilliques, on liste les variantes Maj/min.
    r"|[Мм]оминск[оа]\s+(?:име|фамилия)"
    r"|[Мм]оминско\s+име)"
)

# Nom : commence par une majuscule, au moins 3 caracteres significatifs,
# puis eventuellement un 2e mot (nom compose ou particule + nom).
# Tolere apostrophes et tirets internes.
# Le 1er char doit etre une majuscule (latin etendu OU cyrillique [А-Я]),
# le reste accepte les minuscules cyrilliques [а-я] ainsi que la lettre
# bulgare "ъ" et "й". On garde le quantifieur original.
_NAME = (
    r"[A-ZА-Я][A-Za-zÀ-ÿА-Яа-яЁё\-'’]{2,}"
    r"(?:\s+[A-ZА-Я][A-Za-zÀ-ÿА-Яа-яЁё\-'’]{2,})?"
)

# Pattern :
#   bord gauche : debut de mot
#   libelle + un ou plusieurs blancs (au plus 3, pour eviter de traverser)
#   un nom propre
# Le pattern N'EXIGE PAS de parenthese autour : "née Belkhadra," sans
# parentheses est aussi capture. Mais le libelle DOIT etre precede d'un
# bord de mot (pas au milieu d'un mot comme "naissance" qui contient "ne").
#
# Deux passes pour gerer la case-sensitivity differente :
#  - FR (`née` / `nee`) : strict, pas de IGNORECASE
#  - autres langues : IGNORECASE
_MAIDEN_PATTERN_FR = re.compile(
    rf"(?<!\w){_LABEL_FR}\s{{1,3}}(?P<name>{_NAME})"
)
_MAIDEN_PATTERN_OTHER = re.compile(
    rf"(?<!\w){_LABEL_OTHER}\s{{1,3}}(?P<name>{_NAME})",
    re.IGNORECASE,
)

# Mots qui suivent parfois "nee" / "born" mais ne sont PAS un nom de
# personne. Cas typique : "ne le", "born on", "geboren am". Sans ce
# filtre, on captutrerait "le" / "on" / "am" comme nom.
_STOP_FOLLOWERS = frozenset({
    "le", "la", "les", "on", "in", "am", "el", "die", "der", "den",
    # parfois suivi par un mois textuel
    "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
    "aout", "septembre", "octobre", "novembre", "decembre",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "october", "november", "december",
})


def recognize_maiden_name(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les noms de jeune fille et noms de naissance.

    Le Span couvre uniquement le nom (pas le libelle "nee").

    Args:
        text: texte source.
        score: confiance du recognizer.

    Returns:
        Liste de Spans `PERSON` (meme type que les noms ordinaires : un
        nom de jeune fille EST un nom de personne, il doit etre
        traite et propage comme tel).
    """
    spans: list[Span] = []
    seen_starts: set[int] = set()
    for pattern in (_MAIDEN_PATTERN_FR, _MAIDEN_PATTERN_OTHER):
        for m in pattern.finditer(text):
            start, end = m.span("name")
            if start in seen_starts:
                continue
            name = m.group("name")
            # Ecarter les suiveurs non-nominaux (le / on / am / mois...).
            first_token = name.split()[0]
            if first_token.lower() in _STOP_FOLLOWERS:
                continue
            seen_starts.add(start)
            spans.append(
                Span(
                    start=start,
                    end=end,
                    entity_type="PERSON",
                    text=name,
                    score=score,
                    recognizer="MaidenNameRegex",
                )
            )
    return spans
