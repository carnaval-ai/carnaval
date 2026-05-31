# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Common contract and helpers for recognizers.

A recognizer is a function that takes a text and returns a list of Spans.
No classes, no inheritance, no framework.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, Protocol

from carnaval.core.span import Span


class Recognizer(Protocol):
    """Functional contract for a recognizer."""

    def __call__(self, text: str) -> list[Span]: ...


# ----------------------------------------------------------------------
# Helpers regex -> Span
# ----------------------------------------------------------------------


def regex_to_spans(
    pattern: re.Pattern[str],
    text: str,
    *,
    entity_type: str,
    recognizer: str,
    score: float = 1.0,
    validator: Callable[[str], bool] | None = None,
    metadata: dict | None = None,
) -> list[Span]:
    """Iterate over the matches of a compiled pattern and produce Spans.

    Args:
        pattern: Compiled regex.
        text: Source text.
        entity_type: Entity type to assign to the Span.
        recognizer: Name of the producing recognizer (debug, arbitration).
        score: Score [0,1] applied to each produced Span.
        validator: Optional callable `(text) -> bool` that filters matches
            (useful for checksums: IBAN mod 97, Luhn, ...).
        metadata: Optional dict added to the Spans.

    Returns:
        List of Spans (potentially empty).
    """
    spans: list[Span] = []
    for m in pattern.finditer(text):
        captured = m.group(0)
        if validator is not None and not validator(captured):
            continue
        spans.append(
            Span(
                start=m.start(),
                end=m.end(),
                entity_type=entity_type,
                text=captured,
                score=score,
                recognizer=recognizer,
                metadata=dict(metadata) if metadata else {},
            )
        )
    return spans


# ----------------------------------------------------------------------
# Helpers for tolerant deny lists
# ----------------------------------------------------------------------


# French vowels with their accented variants.
# When `tolerant_accents=True`, each vowel of an item becomes a character
# class that also matches its accented forms.
_ACCENT_CLASSES = {
    "a": "[aàáâäãåAÀÁÂÄÃÅ]",
    "e": "[eéèêëEÉÈÊË]",
    "i": "[iíìîïIÍÌÎÏ]",
    "o": "[oóòôöõOÓÒÔÖÕ]",
    "u": "[uúùûüUÚÙÛÜ]",
    "c": "[cçCÇ]",
    "n": "[nñNÑ]",
    "y": "[yýÿYÝŸ]",
}

# Equivalent character classes for separators and apostrophes.
# The `*` (zero or more) also accepts joined texts like "SampleCounty"
# or "GLOBEXINDUSTRIESSAS". Combined with the external word_boundary, the risk
# of false positives remains very low: we only match at the beginning/end of a word.
#
# IMPORTANT: we do NOT include `\n` in the class. A line break in
# a document is a strong delimiter. Matching "ST BARTHELEMY" through
# "ST\nBARTHELEMY" created multi-line spans that were then dropped by the
# S4 resolver, leaving the orphan occurrence `BARTHELEMY` exposed
# (case Dopag.pdf). If a variant must specifically cross a
# line break, declare two explicit entries in the YAML.
_FLEX_SPACE_CLASS = r"[ \t\-_]*"  # space, tab, hyphen, underscore (NOT \n)
_FLEX_QUOTE_CLASS = r"['‘’]"  # straight + curly apostrophes


_REGEX_SPECIAL_CHARS = set(r"\.^$*+?()[]{}|")
_SEPARATORS = (" ", "\t", "-", "_")

# Word characters for word boundaries of the combined pattern:
# ASCII + Latin-1 accented letters (À-ÿ). Without the accented range,
# a dictionary entry would match adjacent to an accented letter -- "Vue" (town)
# was detected in the middle of "prévue".
_WORD_CHARS = r"A-Za-z0-9_À-ÿ"
_APOSTROPHES = ("'", "‘", "’")


def _flexibilize_item(item: str, *, tolerant_accents: bool = False) -> str:
    """Transform a string into a regex tolerant of common variations:

    - Multiple spaces / tabs / hyphens / underscores: equivalent
    - Straight (`'`) and curly (`U+2018`, `U+2019`) apostrophes: equivalent
    - (optional) Accented vowels: character classes

    Example: "Sample County" produces a pattern that matches:
        - Sample County
        - SAMPLE COUNTY
        - Sample-County
        - Sample_County
        - Sample  County
        - Sample county (case mix, via IGNORECASE downstream)

    Implementation: character-by-character scan (no re.escape) to avoid
    the pitfall where re.escape() escapes spaces in recent Python and
    subsequently breaks substitutions.
    """
    result: list[str] = []
    i = 0
    n = len(item)
    while i < n:
        ch = item[i]

        # Sequence of separators (spaces, tabs, hyphens, underscores) -> 1 class
        if ch in _SEPARATORS:
            j = i
            while j < n and item[j] in _SEPARATORS:
                j += 1
            result.append(_FLEX_SPACE_CLASS)
            i = j
            continue

        # Apostrophe
        if ch in _APOSTROPHES:
            result.append(_FLEX_QUOTE_CLASS)
            i += 1
            continue

        # Accented vowel (optional)
        if tolerant_accents and ch.lower() in _ACCENT_CLASSES:
            result.append(_ACCENT_CLASSES[ch.lower()])
            i += 1
            continue

        # Normal character: escape if it is a special regex character
        if ch in _REGEX_SPECIAL_CHARS:
            result.append("\\" + ch)
        else:
            result.append(ch)
        i += 1

    return "".join(result)


def build_alternation_pattern(
    items: Iterable[str],
    *,
    case_sensitive: bool = False,
    word_boundary: bool = True,
    flexible_separators: bool = True,
    tolerant_accents: bool = False,
) -> re.Pattern[str]:
    """Build an alternation regex from a list of items.

    The produced pattern is TOLERANT by default to common variations:
    case (IGNORECASE), separators (space/hyphen/underscore equivalent),
    straight and curly apostrophes.

    Sorted by descending length so that the longest version matches
    first (regex alternation is not "longest match" by default).

    Args:
        items: List of strings to include.
        case_sensitive: True to require exact case (default False).
        word_boundary: True to require word boundaries (default True).
        flexible_separators: True (default) to treat spaces, hyphens, and
            underscores as equivalent. Allows "Sample County" to also
            match "Sample-County", "Sample_County", etc.
        tolerant_accents: True to treat accented vowels as equivalent
            to their simple form (default False because it makes the pattern
            significantly heavier and can generate false positives).

    Returns:
        Compiled pattern.
    """
    items_sorted = sorted({i for i in items if i}, key=len, reverse=True)
    if not items_sorted:
        return re.compile(r"(?!x)x")

    if flexible_separators or tolerant_accents:
        parts = [
            _flexibilize_item(i, tolerant_accents=tolerant_accents)
            for i in items_sorted
        ]
    else:
        parts = [re.escape(i) for i in items_sorted]

    body = "|".join(parts)
    if word_boundary:
        body = rf"(?:{body})"
        body = rf"(?<![{_WORD_CHARS}]){body}(?![{_WORD_CHARS}])"
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(body, flags)
