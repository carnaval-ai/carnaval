# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Moteur GLiNER : NER zero-shot pour les entites PII.

Wrapper minimaliste autour de la lib `gliner`. Pas de Presidio entre les deux.

Premier appel : telechargement du modele depuis HuggingFace (~500 Mo).
Appels suivants : modele cache en RAM (~1 Go).
"""

from __future__ import annotations

from typing import Optional

from carnaval.core.span import Span

DEFAULT_MODEL = "urchade/gliner_multi_pii-v1"

# Labels par defaut a chercher (le modele est zero-shot, on lui passe les
# noms d'entites qu'on veut detecter).
DEFAULT_LABELS = (
    "person",
    "email",
    "phone number",
    "address",
    "street address",
    "postal code",
    "city",
    "organization",
    "company",
    "vat number",
    "tax identification number",
)

# Mapping labels GLiNER -> entity_type carnaval
LABEL_TO_ENTITY_TYPE = {
    "person": "PERSON",
    "email": "EMAIL",
    "phone number": "PHONE",
    "address": "LOCATION",
    "street address": "LOCATION",
    "postal code": "LOCATION",
    "city": "LOCATION",
    "organization": "ORGANIZATION",
    "company": "ORGANIZATION",
    "vat number": "VAT",
    "tax identification number": "VAT",
}


_MODEL: Optional[object] = None


def _load_model(model_name: str = DEFAULT_MODEL):
    """Charge le modele paresseusement (premier appel = telechargement)."""
    global _MODEL
    if _MODEL is None:
        try:
            from gliner import GLiNER  # type: ignore
        except ImportError as e:
            raise ImportError(
                "Le package 'gliner' n'est pas installe. " "Lance : pip install gliner"
            ) from e
        _MODEL = GLiNER.from_pretrained(model_name)
    return _MODEL


def is_available() -> bool:
    """Verifie si la lib gliner est installable. N'instancie pas le modele."""
    try:
        import gliner  # noqa: F401

        return True
    except ImportError:
        return False


# GLiNER tronque les textes longs (limite interne ~384 tokens). Pour qu'aucune
# entite n'echappe a l'analyse, on decoupe le texte en tranches sous cette
# limite puis on realigne les positions sur le texte complet.
_GLINER_CHUNK_CHARS = 800


def _split_into_chunks(
    text: str, limit: int = _GLINER_CHUNK_CHARS
) -> list[tuple[int, str]]:
    """Decoupe `text` en tranches de `limit` caracteres au plus.

    La coupe recule jusqu'au dernier saut de ligne (a defaut, espace) pour ne
    casser ni un mot ni une entite. Renvoie des couples (offset, tranche),
    `offset` etant la position de la tranche dans le texte d'origine.
    """
    chunks: list[tuple[int, str]] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + limit, n)
        if end < n:
            cut = text.rfind("\n", i, end)
            if cut <= i:
                cut = text.rfind(" ", i, end)
            if cut > i:
                end = cut
        chunks.append((i, text[i:end]))
        i = end
    return chunks


def recognize_with_gliner(
    text: str,
    labels: tuple[str, ...] | list[str] = DEFAULT_LABELS,
    threshold: float = 0.4,
    model_name: str = DEFAULT_MODEL,
) -> list[Span]:
    """Lance GLiNER et convertit la sortie en Spans carnaval.

    Le texte est decoupe en tranches sous la limite interne de GLiNER puis
    analyse tranche par tranche : aucune entite n'est perdue dans les longs
    documents. Les positions sont realignees sur le texte complet.

    Args:
        text: texte source.
        labels: noms des entites a chercher (zero-shot, modifiable a la volee).
        threshold: seuil de confiance minimal [0,1].
        model_name: nom du modele HuggingFace.

    Returns:
        Liste de Span (eventuellement vide).
    """
    if not text or not text.strip():
        return []

    model = _load_model(model_name)
    label_list = list(labels)

    spans: list[Span] = []
    for offset, chunk in _split_into_chunks(text):
        for ent in model.predict_entities(chunk, label_list, threshold=threshold):
            label = ent["label"]
            entity_type = LABEL_TO_ENTITY_TYPE.get(label, label.upper())
            start = offset + int(ent["start"])
            end = offset + int(ent["end"])
            spans.append(
                Span(
                    start=start,
                    end=end,
                    entity_type=entity_type,
                    text=text[start:end],
                    score=float(ent["score"]),
                    recognizer="GLiNER",
                    metadata={"gliner_label": label},
                )
            )
    return spans
