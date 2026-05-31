"""Tests unitaires du detecteur de langue."""

from __future__ import annotations

import pytest

from carnaval.core.language_detector import detect_language


class TestLanguageDetector:
    def test_french(self):
        text = "Bonjour, ceci est un texte en francais avec plusieurs mots."
        assert detect_language(text) == "fr"

    def test_english(self):
        text = "Hello, this is a sample English text with some words."
        assert detect_language(text) == "en"

    def test_german(self):
        text = "Guten Tag, dies ist ein Beispieltext auf Deutsch."
        assert detect_language(text) == "de"

    def test_japanese(self):
        text = "こんにちは、これは日本語のテキストです。"
        assert detect_language(text) == "ja"

    def test_empty(self):
        assert detect_language("") == "unknown"
        assert detect_language("   ") == "unknown"

    def test_none_returns_unknown(self):
        # Comportement gracieux : None est traite comme texte vide.
        assert detect_language(None) == "unknown"  # type: ignore[arg-type]
