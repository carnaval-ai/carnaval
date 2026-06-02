# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Test Template / Boilerplate for carnaval.

This file provides a starting point for developers who want to write:
1. Unit tests for custom recognizers.
2. Unit tests for custom pipeline stages.
3. Integration tests for custom anonymization profiles.

Copy this template into a new test file under `tests/unit/` or `tests/integration/`
and adapt it to your needs.
"""

from __future__ import annotations

from pathlib import Path
import pytest

# 1. Imports from the core library
from carnaval.core.span import Span
from carnaval.core.vault import Vault
from carnaval.stages.documents import RawDocument, NormalizedDocument, ResolvedDocument, MaskedDocument
from carnaval.pipeline import run_anonymization

# Default strong password for testing vaults
TEST_PASSWORD = "test_password_must_be_at_least_16_chars_long"


# ======================================================================
# UNIT TEST TEMPLATE: Custom Recognizer
# ======================================================================

class TestCustomRecognizerTemplate:
    """Test class for verifying custom entity detection logic."""

    def test_custom_regex_recognition(self):
        """Verify that a custom pattern (e.g. specialized product codes) is detected."""
        # 1. Arrange: setup text input and target patterns
        text = "Order confirmation for item PRD-9982-A."
        
        # 2. Act: invoke your recognition logic (e.g. regex pattern match)
        # Here we mock the behavior by directly instantiating a list of Span objects.
        spans = []
        if "PRD-" in text:
            spans.append(
                Span(start=27, end=37, entity_type="PRODUCT_REF", text="PRD-9982-A", score=1.0)
            )
            
        # 3. Assert: verify detected spans match expectations
        assert len(spans) == 1
        assert spans[0].entity_type == "PRODUCT_REF"
        assert spans[0].text == "PRD-9982-A"
        assert spans[0].score == 1.0


# ======================================================================
# UNIT TEST TEMPLATE: Custom Pipeline Stage
# ======================================================================

class TestCustomStageTemplate:
    """Test class for verifying custom preprocess or postprocess pipeline stages."""

    def test_custom_stage_modifies_document(self):
        """Verify that the stage processes document metadata or content correctly."""
        # 1. Arrange
        raw_doc = RawDocument(
            text="Clean this text.",
            source_path=Path("mock.txt"),
            encoding="utf-8",
            metadata={"original_encoding": "utf-8"}
        )
        
        # 2. Act: apply your custom preprocessing step
        # E.g., we add custom metadata keys
        processed_metadata = dict(raw_doc.metadata)
        processed_metadata["preprocessed"] = True
        
        prep_doc = NormalizedDocument(
            text=raw_doc.text,
            source_path=raw_doc.source_path,
            language="en",
            metadata=processed_metadata
        )
        
        # 3. Assert
        assert prep_doc.language == "en"
        assert prep_doc.metadata.get("preprocessed") is True


# ======================================================================
# INTEGRATION TEST TEMPLATE: End-to-End Pipeline / Profile
# ======================================================================

@pytest.fixture
def mock_outbox_dir(tmp_path: Path) -> Path:
    """Fixture creating output folders in a sandbox directory for testing."""
    box = tmp_path / "outbox"
    # Create all target output subdirectories
    for sub in ("txt", "json", "jsonl", "xml", "conll", "html", "vault", "meta"):
        (box / sub).mkdir(parents=True)
    return box


class TestIntegrationProfileTemplate:
    """End-to-end integration test structure for custom business profiles."""

    def test_anonymize_roundtrip(self, mock_outbox_dir: Path, tmp_path: Path):
        """Test a full run: load document, mask, check file outputs, and verify vault reinjection."""
        # 1. Arrange: Write a mock text file to test
        input_file = tmp_path / "sample_document.txt"
        input_file.write_text("Invoice from Acme Corp to customer Carol Carter.", encoding="utf-8")

        # 2. Act: Run the anonymization pipeline using a specific profile
        # Note: Set use_gliner=False in unit/local tests to prevent model downloads
        masked, vault, outbox = run_anonymization(
            input_path=input_file,
            outbox_dir=mock_outbox_dir,
            vault_password=TEST_PASSWORD,
            profile="acknowledge",  # Replace with your custom profile folder name
            use_gliner=False
        )

        # 3. Assert: Verify the anonymized text contains placeholders
        assert "[CLIENT_NAME]" in masked.anonymized_text  # Acme Corp is standard singleton
        assert "Acme Corp" not in masked.anonymized_text
        assert "Carol Carter" not in masked.anonymized_text

        # 4. Verify output files are written to the outbox directory
        output_txt_file = mock_outbox_dir / "txt" / "sample_document_anonymise.txt"
        assert output_txt_file.exists()
        assert "[CLIENT_NAME]" in output_txt_file.read_text(encoding="utf-8")
