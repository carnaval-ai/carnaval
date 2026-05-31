# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Etapes post-detect : transformations sur l'ensemble des spans deja
detectes, avant resolution (S4). Distinct des recognizers "primaires"
qui produisent independamment leurs spans depuis le texte.
"""

from carnaval.recognizers.post.org_line_expansion import expand_org_on_line
from carnaval.recognizers.post.person_line_expansion import expand_person_on_line

__all__ = ["expand_org_on_line", "expand_person_on_line"]
