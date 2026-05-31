# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Detection de langue via lingua-language-detector.

Wrapper minimal. Renvoie un code ISO 'fr'/'en'/'de'/'ja' ou 'unknown'.
"""

from __future__ import annotations

from typing import Optional

from lingua import Language, LanguageDetectorBuilder

_SUPPORTED = (Language.FRENCH, Language.ENGLISH, Language.GERMAN, Language.JAPANESE)
_DETECTOR: Optional[object] = None


def _get_detector():
    """Charge le detecteur paresseusement (premier appel = chargement modeles)."""
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = (
            LanguageDetectorBuilder.from_languages(*_SUPPORTED)
            .with_preloaded_language_models()
            .build()
        )
    return _DETECTOR


def detect_language(text: str) -> str:
    """Detecte la langue d'un texte.

    Args:
        text: contenu textuel a analyser.

    Returns:
        'fr', 'en', 'de', 'ja' ou 'unknown'.
    """
    if not text or not text.strip():
        return "unknown"

    sample = text[:5000]
    lang = _get_detector().detect_language_of(sample)
    if lang is None:
        return "unknown"
    mapping = {
        Language.FRENCH: "fr",
        Language.ENGLISH: "en",
        Language.GERMAN: "de",
        Language.JAPANESE: "ja",
    }
    return mapping.get(lang, "unknown")
