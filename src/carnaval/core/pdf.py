# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Extraction PDF -> texte, en preservant l'ordre visuel des blocs.

Utilise PyMuPDF en mode `blocks` avec `sort=True` : les blocs visuels sont
restitues haut -> bas, gauche -> droite, dans l'ordre de lecture humaine.
Cette extraction "layout-aware" est la fondation du pipeline. Sans elle :

- les pieds de page s'intercalent avant l'en-tete de la page suivante ;
- les tokens visuellement separes se retrouvent colles ("ANJOU49180",
  "0241414242N° tel client") ;
- les cellules d'un tableau se fragmentent dans le desordre.

Le pipeline aval (recognizers, allow_list, table_body) consomme du texte
ligne par ligne et beneficie immediatement d'un ordre coherent.

Format de sortie - le "contrat" :

    [PAGE 1]
    <bloc 1 strippe>
    <bloc 2 strippe>
    ...

    [PAGE 2]
    ...

Chaque page utile est precedee d'un marqueur `[PAGE n]` (n = numero
1-based dans le PDF d'origine). Les blocs au sein d'une page sont
separes par `\\n` ; les pages entre elles par une ligne vide. Les blocs
images (`block_type == 1`) sont ignores.

Primitives exposees :
    - `extract_blocks_from_page(page)` : bas niveau, page deja ouverte
      via PyMuPDF. Reutilisable par d'autres extracteurs (typiquement
      Eureka, qui veut filtrer les pages de CGV avant d'agreger).
    - `extract_text_from_pdf(pdf_path)` : haut niveau, le PDF complet en
      une passe avec marqueurs `[PAGE n]`. C'est ce que consomme
      `run_anonymization_from_pdf`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pymupdf  # alias historique : fitz

if TYPE_CHECKING:
    # Import seulement pour le typage ; evite un cout au runtime.
    from pymupdf import Page  # noqa: F401


def extract_blocks_from_page(page: "pymupdf.Page") -> list[str]:
    """Extrait les blocs visuels d'UNE page deja ouverte par PyMuPDF.

    Primitive bas niveau partageable entre extracteurs : utiliser cette
    fonction (et NON `page.get_text(...)` directement) garantit que tous
    les producteurs de texte qui alimentent Carnaval respectent la meme
    convention - ordre visuel haut->bas / gauche->droite, blocs textuels
    uniquement, strip des espaces.

    Args:
        page: instance `pymupdf.Page` (le caller gere l'ouverture du
            document et sa fermeture).

    Returns:
        Liste de blocs textuels nettoyes, dans l'ordre de lecture. Liste
        vide si la page n'a aucun bloc texte exploitable.
    """
    blocks = page.get_text("blocks", sort=True)
    cleaned_blocks: list[str] = []
    for block in blocks:
        # PyMuPDF renvoie (x0, y0, x1, y1, text, block_no, block_type)
        if len(block) < 7:
            continue
        if block[6] != 0:  # 0 = texte, 1 = image
            continue
        cleaned = (block[4] or "").strip()
        if cleaned:
            cleaned_blocks.append(cleaned)
    return cleaned_blocks


def extract_text_from_pdf(pdf_path: Path | str) -> str:
    """Extrait le texte d'un PDF en respectant l'ordre visuel des blocs.

    Args:
        pdf_path: chemin du PDF a lire.

    Returns:
        Texte concatene, format documente dans le module.

    Raises:
        FileNotFoundError: si le PDF n'existe pas.
    """
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(f"PDF introuvable : {p}")

    doc = pymupdf.open(p)
    try:
        pages_texts: list[str] = []
        for index, page in enumerate(doc, start=1):
            lines = extract_blocks_from_page(page)
            if lines:
                pages_texts.append(f"[PAGE {index}]\n" + "\n".join(lines))
        return "\n\n".join(pages_texts)
    finally:
        doc.close()
