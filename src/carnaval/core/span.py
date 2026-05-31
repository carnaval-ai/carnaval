# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Span type: a detected fragment in text.

A Span represents a sensitive entity located in the source text.
Used across all pipeline stages: produced by S3 (detect), consumed by S4 (resolve)
and S5 (mask).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Span:
    """A detected fragment (sensitive entity span).

    Attributes:
        start: Start offset in the source text (inclusive).
        end: End offset in the source text (exclusive).
        entity_type: Entity type (PERSON, EMAIL, ORG_SINGLETON, ...).
        text: Original captured text content.
        score: Confidence score in [0.0, 1.0].
        recognizer: Name of the producing recognizer (for debugging and arbitration).
        metadata: Free-form key/value metadata (language, pattern_name, ...).
    """

    start: int
    end: int
    entity_type: str
    text: str
    score: float = 1.0
    recognizer: str = ""
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start negatif : {self.start}")
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) <= start ({self.start})")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score hors [0,1] : {self.score}")
        if not self.entity_type:
            raise ValueError("entity_type vide")

    @property
    def length(self) -> int:
        """Length of the span in characters."""
        return self.end - self.start

    def overlaps(self, other: Span) -> bool:
        """Return True if the two spans share at least one character."""
        return not (self.end <= other.start or other.end <= self.start)

    def contains(self, other: Span) -> bool:
        """Return True if self strictly contains or equals other."""
        return self.start <= other.start and self.end >= other.end

    def shift(self, delta: int) -> Span:
        """Return a copy of the span shifted by delta characters."""
        return Span(
            start=self.start + delta,
            end=self.end + delta,
            entity_type=self.entity_type,
            text=self.text,
            score=self.score,
            recognizer=self.recognizer,
            metadata=dict(self.metadata),
        )

    def trim_whitespace(self) -> Span | None:
        """Return a copy of the span with leading/trailing whitespace removed (or None if empty).

        A PII span must never start or end with a whitespace character.
        When a recognizer captures the trailing separator space, the placeholder
        sticks to the next token during masking (e.g. "[ADDR]Tel."). Trimming
        boundary whitespace tightens the span to its actual content without loss:
        the whitespace stays in clear text outside the mask, and round-trip
        remains exact.

        Returns:
            - `self` if no boundary whitespace (avoids unnecessary copy),
            - a new trimmed Span otherwise,
            - None if the span contains only whitespace.
        """
        left = len(self.text) - len(self.text.lstrip())
        right = len(self.text) - len(self.text.rstrip())
        if left == 0 and right == 0:
            return self
        if left + right >= len(self.text):
            return None
        return Span(
            start=self.start + left,
            end=self.end - right,
            entity_type=self.entity_type,
            text=self.text[left : len(self.text) - right],
            score=self.score,
            recognizer=self.recognizer,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON/audit (note: contains the original text)."""
        return {
            "start": self.start,
            "end": self.end,
            "entity_type": self.entity_type,
            "text": self.text,
            "score": self.score,
            "recognizer": self.recognizer,
            "metadata": dict(self.metadata),
        }

    def to_dict_safe(self) -> dict[str, Any]:
        """Serialize without the original value (for non-sensitive logs/audit)."""
        return {
            "start": self.start,
            "end": self.end,
            "entity_type": self.entity_type,
            "length": self.length,
            "score": self.score,
            "recognizer": self.recognizer,
        }
