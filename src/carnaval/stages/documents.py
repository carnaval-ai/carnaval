# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Intermediate documents exchanged between pipeline stages.

All documents are immutable (frozen dataclass). Each stage produces
a new document derived from the input document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from carnaval.core.span import Span


@dataclass(frozen=True)
class RawDocument:
    """Raw document as read from disk (S1 output)."""

    source_path: Path
    text: str
    encoding: str = "utf-8"
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def length(self) -> int:
        """Length of the document text in characters."""
        return len(self.text)


@dataclass(frozen=True)
class NormalizedDocument:
    """Document after preprocessing (S2 output).

    The text may have been normalized (optional whitespace and noise removed).
    The detected language is attached.
    """

    source_path: Path
    text: str
    language: str  # 'fr', 'en', 'de', 'ja', 'unknown'
    encoding: str = "utf-8"
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class DetectedDocument:
    """Document with raw Spans (S3 output)."""

    source_path: Path
    text: str
    language: str
    spans: tuple[Span, ...]  # tuple for immutability
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class ResolvedDocument:
    """Document after deduplication and conflict resolution (S4 output)."""

    source_path: Path
    text: str
    language: str
    spans: tuple[Span, ...]  # ordered, non-overlapping spans
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class MaskedDocument:
    """Document after masking (S5 output).

    Contains the anonymized text and the Spans enriched with the assigned placeholder.
    """

    source_path: Path
    original_text: str  # input text
    anonymized_text: str  # text with placeholders
    language: str
    spans: tuple[Span, ...]  # with metadata["placeholder"] populated
    by_category: dict[str, int] = field(default_factory=dict, compare=False, hash=False)
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class WrittenOutput:
    """Inventory of written output files (S6 output)."""

    txt_path: Path
    json_path: Path
    jsonl_path: Path
    xml_path: Path
    conll_path: Path
    html_path: Path
    vault_path: Path
    meta_path: Path
