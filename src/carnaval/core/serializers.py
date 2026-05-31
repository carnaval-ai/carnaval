# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Serialisation d'un MaskedDocument vers plusieurs formats standards.

Formats supportes :
    txt    : texte anonymise brut
    json   : {text, entities[], meta}
    jsonl  : 1 entite par ligne (streaming)
    xml    : equivalent du JSON en XML
    conll  : tokens + tags BIO (entrainement NER)
    html   : visualisation colorisee inline
"""

from __future__ import annotations

import html as html_lib
import json
from typing import Any
from xml.etree import ElementTree as ET

from carnaval.core.span import Span
from carnaval.stages.documents import MaskedDocument

# Palette de couleurs deterministe par entity_type (pour HTML)
_HTML_COLOR_PALETTE = {
    "PERSON": "#FFB3BA",
    "EMAIL": "#BFFCC6",
    "PHONE": "#BAE1FF",
    "ORGANIZATION": "#FFFFBA",
    "ORG_SINGLETON": "#FFDFBA",
    "LOCATION": "#E0BBE4",
    "URL": "#D0F4DE",
    "IBAN": "#A0C4FF",
    "BIC": "#A0C4FF",
    "SIRET": "#FFD6A5",
    "SIREN": "#FFD6A5",
    "VAT": "#FFD6A5",
}


# ----------------------------------------------------------------------
# TXT
# ----------------------------------------------------------------------


def to_txt(doc: MaskedDocument) -> str:
    """Renvoie simplement le texte anonymise (avec placeholders)."""
    return doc.anonymized_text


# ----------------------------------------------------------------------
# JSON
# ----------------------------------------------------------------------


def _span_to_entity_dict(span: Span) -> dict[str, Any]:
    return {
        "start": span.start,
        "end": span.end,
        "type": span.entity_type,
        "placeholder": span.metadata.get("placeholder"),
        "score": round(span.score, 3),
        "recognizer": span.recognizer,
    }


def to_json(doc: MaskedDocument) -> str:
    """Renvoie le document anonymise en JSON {text, entities[], meta}."""
    payload = {
        "anonymized_text": doc.anonymized_text,
        "language": doc.language,
        "entities": [_span_to_entity_dict(s) for s in doc.spans],
        "by_category": doc.by_category,
        "source": str(doc.source_path),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------
# JSONL
# ----------------------------------------------------------------------


def to_jsonl(doc: MaskedDocument) -> str:
    """1 entite par ligne au format JSON."""
    lines = [json.dumps(_span_to_entity_dict(s), ensure_ascii=False) for s in doc.spans]
    return "\n".join(lines) + ("\n" if lines else "")


# ----------------------------------------------------------------------
# XML
# ----------------------------------------------------------------------


def to_xml(doc: MaskedDocument) -> str:
    """Equivalent du JSON, en XML."""
    root = ET.Element("carnavalResult")
    ET.SubElement(root, "anonymizedText").text = doc.anonymized_text
    ET.SubElement(root, "language").text = doc.language
    ET.SubElement(root, "source").text = str(doc.source_path)

    by_cat = ET.SubElement(root, "byCategory")
    for cat, count in sorted(doc.by_category.items()):
        node = ET.SubElement(by_cat, "category", {"name": cat})
        node.text = str(count)

    entities = ET.SubElement(root, "entities")
    for s in doc.spans:
        attrs = {
            "start": str(s.start),
            "end": str(s.end),
            "type": s.entity_type,
            "placeholder": s.metadata.get("placeholder", ""),
            "score": str(round(s.score, 3)),
            "recognizer": s.recognizer,
        }
        ET.SubElement(entities, "entity", attrs)

    # Indentation lisible
    ET.indent(root, space="  ", level=0)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        root, encoding="unicode"
    )


# ----------------------------------------------------------------------
# CoNLL / BIO (standard NER training)
# ----------------------------------------------------------------------


def to_conll(doc: MaskedDocument) -> str:
    """Format CoNLL-2003 / BIO.

    Chaque ligne : `token TAG`. Une ligne vide separe les phrases.
    Tokenisation simple basee sur les espaces. Le tag BIO suit la convention :
        B-TYPE : premier token de l'entite
        I-TYPE : tokens suivants
        O      : hors entite
    """
    text = doc.original_text
    spans = sorted(doc.spans, key=lambda s: s.start)
    output_lines: list[str] = []

    i = 0
    span_idx = 0
    n = len(text)

    while i < n:
        # Skip whitespace
        if text[i].isspace():
            if text[i] == "\n":
                output_lines.append("")  # separateur de phrase
            i += 1
            continue

        # Trouver la fin du token (jusqu'au prochain whitespace)
        j = i
        while j < n and not text[j].isspace():
            j += 1

        token = text[i:j]
        tag = "O"

        # Trouver le span qui couvre ce token (le cas echeant)
        while span_idx < len(spans) and spans[span_idx].end <= i:
            span_idx += 1
        if span_idx < len(spans):
            sp = spans[span_idx]
            if sp.start <= i < sp.end:
                # Le token est dans le span. B- si on est sur le 1er token,
                # I- sinon. Critere : i == sp.start ou non.
                tag = ("B-" if i == sp.start else "I-") + sp.entity_type

        output_lines.append(f"{token} {tag}")
        i = j

    return "\n".join(output_lines) + "\n"


# ----------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------


def to_html(doc: MaskedDocument) -> str:
    """Visualisation HTML : texte original avec spans colorises selon entity_type."""
    text = doc.original_text
    spans = sorted(doc.spans, key=lambda s: s.start)

    parts: list[str] = []
    cursor = 0
    for s in spans:
        if cursor < s.start:
            parts.append(html_lib.escape(text[cursor : s.start]))
        color = _HTML_COLOR_PALETTE.get(s.entity_type, "#EEEEEE")
        ph = s.metadata.get("placeholder", "")
        parts.append(
            f'<span style="background-color: {color}; padding: 2px 4px; '
            f'border-radius: 3px;" title="{html_lib.escape(s.entity_type)} '
            f'-> {html_lib.escape(ph)}">'
            f"{html_lib.escape(text[s.start:s.end])}"
            f"</span>"
        )
        cursor = s.end
    if cursor < len(text):
        parts.append(html_lib.escape(text[cursor:]))

    body = "".join(parts).replace("\n", "<br>\n")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="fr">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        f"  <title>carnaval - {html_lib.escape(doc.source_path.name)}</title>\n"
        "  <style>\n"
        "    body { font-family: monospace; padding: 20px; max-width: 1200px; }\n"
        "    .legend { margin-bottom: 16px; }\n"
        "    .legend span { display: inline-block; margin-right: 8px; }\n"
        "    pre { white-space: pre-wrap; word-wrap: break-word; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>carnaval - {html_lib.escape(doc.source_path.name)}</h1>\n"
        f"  <p>Langue : <b>{doc.language}</b> | "
        f"Entites detectees : <b>{len(doc.spans)}</b></p>\n"
        '  <div class="legend">\n'
        + "    "
        + " ".join(
            f'<span style="background-color: {c};">{t}</span>'
            for t, c in sorted(_HTML_COLOR_PALETTE.items())
        )
        + "\n  </div>\n"
        f"  <pre>{body}</pre>\n"
        "</body>\n</html>\n"
    )
