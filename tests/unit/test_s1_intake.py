"""Tests etage 1 : Intake."""

from __future__ import annotations

from pathlib import Path

import pytest

from carnaval.stages.s1_intake import IntakeError, intake


class TestIntake:
    def test_reads_utf8(self, tmp_path: Path):
        f = tmp_path / "doc.txt"
        f.write_text("Hello carnaval", encoding="utf-8")
        doc = intake(f)
        assert doc.text == "Hello carnaval"
        assert doc.encoding == "utf-8"
        assert doc.source_path == f

    def test_fallback_latin1(self, tmp_path: Path):
        f = tmp_path / "latin.txt"
        f.write_bytes("caractères latin-1".encode("latin-1"))
        doc = intake(f)
        assert "caract" in doc.text
        assert doc.encoding == "latin-1"

    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(IntakeError, match="File not found"):
            intake(tmp_path / "absent.txt")

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        with pytest.raises(IntakeError, match="Empty file"):
            intake(f)

    def test_too_large(self, tmp_path: Path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 200)
        with pytest.raises(IntakeError, match="too large"):
            intake(f, max_size_bytes=100)

    def test_not_a_file(self, tmp_path: Path):
        with pytest.raises(IntakeError, match="Not a file"):
            intake(tmp_path)

    def test_metadata(self, tmp_path: Path):
        f = tmp_path / "doc.txt"
        f.write_text("hello", encoding="utf-8")
        doc = intake(f)
        assert doc.metadata["filename"] == "doc.txt"
        assert doc.metadata["size_bytes"] == 5
