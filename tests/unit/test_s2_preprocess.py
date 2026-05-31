"""Tests etage 2 : Preprocess."""

from __future__ import annotations

from pathlib import Path

import pytest

from carnaval.stages.documents import RawDocument
from carnaval.stages.s2_preprocess import preprocess


def _raw(text: str) -> RawDocument:
    return RawDocument(source_path=Path("dummy.txt"), text=text)


class TestPreprocess:
    def test_detects_french(self):
        doc = _raw("Bonjour, ceci est un texte en francais.")
        out = preprocess(doc)
        assert out.language == "fr"

    def test_detects_english(self):
        doc = _raw("Hello, this is an English text.")
        out = preprocess(doc)
        assert out.language == "en"

    def test_force_language(self):
        doc = _raw("Texte ambigu")
        out = preprocess(doc, language="de")
        assert out.language == "de"

    def test_bom_removed(self):
        doc = _raw("﻿Hello")
        out = preprocess(doc)
        assert not out.text.startswith("﻿")

    def test_multi_spaces_collapsed(self):
        doc = _raw("Word    with        spaces")
        out = preprocess(doc, normalize_spaces=True)
        assert "    " not in out.text
        assert "Word with spaces" in out.text

    def test_cleanup_pipes_disabled_by_default(self):
        doc = _raw("Chi | mieBERTAUX")
        out = preprocess(doc)
        # Par defaut on ne touche pas aux pipes
        assert "Chi | mie" in out.text

    def test_cleanup_pipes_enabled(self):
        doc = _raw("Chi | mieBERTAUX")
        out = preprocess(doc, cleanup_pipes=True)
        assert "ChimieBERTAUX" in out.text

    def test_metadata_propagated(self):
        doc = RawDocument(
            source_path=Path("x.txt"),
            text="Bonjour",
            metadata={"size_bytes": 7},
        )
        out = preprocess(doc)
        assert out.metadata["size_bytes"] == 7
        assert "normalize_spaces" in out.metadata
