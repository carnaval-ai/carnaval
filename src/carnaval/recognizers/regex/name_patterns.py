# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Shim de retro-compatibilite.

Ce module a ete deplace vers `carnaval.recognizers.regex.names.fr`.

DEPRECATED : preferer
    from carnaval.recognizers.regex.names import recognize_names
"""

from carnaval.recognizers.regex.names.fr import (  # noqa: F401
    CIVILITE_PATTERN,
    NAME_COMMA_PATTERN,
    PERSON_CONTEXT_KEYWORDS,
    PRENOM_NOM_GLUED_PATTERN,
    PRENOM_NOM_PATTERN,
    recognize_civilite,
    recognize_contextual_person,
    recognize_name_comma,
    recognize_name_patterns,
    recognize_prenom_nom,
    recognize_prenom_nom_glued,
)
