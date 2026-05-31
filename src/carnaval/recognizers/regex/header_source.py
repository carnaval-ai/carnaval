# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer pour les headers de provenance ajoutes par les extracteurs PDF.

Format typique :
    # Fichier source: nom_du_pdf.pdf

Le nom de fichier contient souvent le nom du fournisseur en clair. On masque
tout ce qui suit ': ' jusqu'a la fin de ligne.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

HEADER_SOURCE_PATTERN = re.compile(r"#\s*Fichier source:\s*([^\r\n]+)")


def recognize_header_source(text: str, score: float = 0.95) -> list[Span]:
    """Detecte la valeur apres '# Fichier source: '."""
    spans: list[Span] = []
    for m in HEADER_SOURCE_PATTERN.finditer(text):
        # On capture seulement le groupe 1 (la valeur, pas le prefixe)
        spans.append(
            Span(
                start=m.start(1),
                end=m.end(1),
                entity_type="LOCATION",
                text=m.group(1),
                score=score,
                recognizer="HeaderSourceRegex",
            )
        )
    return spans
