# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer URL et domaines."""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# TLD reconnus pour autoriser un "domaine nu" (sans http/https/www) :
# generiques + ccTLD des pays usuels. Sans cette liste, un mot quelconque
# `xxx.yy` (ex. `ref.du`, `art.no`) etait matche comme une URL.
_KNOWN_TLDS = (
    # generiques
    "com|org|net|info|biz|edu|gov|mil|int|app|tech|ai|io|co|me|tv|cc|"
    "name|pro|aero|coop|jobs|mobi|asia|cat|"
    # ccTLD europeens
    "fr|eu|de|es|it|pt|nl|be|ch|pl|tr|uk|cz|at|se|no|dk|fi|gr|hu|ie|"
    "lu|ro|bg|sk|si|lt|lv|ee|hr|is|mt|cy|li|mc|sm|va|al|ba|mk|me|rs|md|"
    # ccTLD ameriques / asie / oceanie / afrique
    "us|ca|mx|br|ar|cl|co|pe|ve|uy|py|bo|ec|"
    "jp|cn|kr|tw|hk|sg|in|id|th|my|ph|vn|pk|bd|lk|ae|sa|il|"
    "au|nz|"
    "za|eg|ma|tn|ng|ke|gh|ci|sn|"
    "ru|ua|by|kz"
)

# Deux formes acceptees :
#   (1) avec schema (http/https) ou prefixe `www.` : on fait confiance au
#       contexte, le TLD peut etre quelconque (`https://exotic.tld`).
#   (2) "domaine nu" (sans schema ni www) : on exige un TLD parmi la liste
#       connue ET un label d'au moins 3 caracteres (`globex.io` matche,
#       `ref.du` non).
# Le `(?![^\W\d_])` apres le TLD interdit qu'une lettre suive immediatement
# (cf. "H.TR" extrait a tort de "P.U.H.TRéférence" si on ne borne pas).
URL_PATTERN = re.compile(
    r"\b(?:"
    r"(?:https?://|www\.)"
    r"[a-zA-Z0-9][a-zA-Z0-9\-]{0,62}"
    r"(?:\.[a-zA-Z0-9\-]{2,})+"
    r"|"
    r"[a-zA-Z0-9][a-zA-Z0-9\-]{2,62}\.(?:" + _KNOWN_TLDS + r")"
    r")"
    r"(?![^\W\d_])"
    r"(?:/[^\s]*)?",
    re.IGNORECASE,
)


def recognize_url(text: str, score: float = 0.7) -> list[Span]:
    return regex_to_spans(
        URL_PATTERN,
        text,
        entity_type="URL",
        recognizer="UrlRegex",
        score=score,
    )
