# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Stage 2 - Preprocess: language detection + light normalization.

Responsibilities:
- Detect the language
- Minimal normalization (BOM, non-standard whitespace, multiple spaces)
- (Optional, disabled by default) removal of vertical bar noise
  that appears in some PDF extractors

Input: RawDocument
Output: NormalizedDocument
"""

from __future__ import annotations

import re

from carnaval.core.language_detector import detect_language
from carnaval.stages.documents import NormalizedDocument, RawDocument

_BOM_PATTERN = re.compile(r"^﻿")
_MULTI_SPACES_PATTERN = re.compile(r"[ \t]{2,}")
# Non-standard whitespace (non-breaking U+00A0, narrow no-break U+202F, etc.),
# excluding newlines and tabs. PDF extraction injects them heavily; we map
# them to ASCII space so that character-by-character recognizers (IBAN, RIB)
# do not break on the injected chars and miss entities.
_NONSTD_SPACE_PATTERN = re.compile(r"[^\S\n\r\t\f\v]")
# Vertical bar noise in the middle of words ("Chi | mieBERTAUX")
# We turn "X | Y" -> "XY" or "X Y" -> "XY" depending on context. Conservative:
# only remove "alpha | alpha" when glued to letters.
_PIPE_NOISE_PATTERN = re.compile(r"([A-Za-z]) \| ([A-Za-z])")


def preprocess(
    doc: RawDocument,
    *,
    language: str | None = None,
    normalize_spaces: bool = True,
    cleanup_pipes: bool = False,
) -> NormalizedDocument:
    """Prepare text for detection.

    Args:
        doc: Input RawDocument.
        language: force a language ('fr', 'en', 'de', 'ja'). Auto-detect if None.
        normalize_spaces: True -> collapse multiple spaces.
        cleanup_pipes: True -> remove `|` noise like "Chi | mie".
            DEFAULT: False, because it risks touching business content.

    Returns:
        NormalizedDocument.
    """
    text = doc.text

    # 1. BOM
    text = _BOM_PATTERN.sub("", text)

    # 2. Non-standard spaces -> ASCII space. Without this, a recognizer that
    #    collects character-by-character (IBAN, RIB) stops on the non-breaking
    #    space injected by PDF extraction and misses the entity.
    text = _NONSTD_SPACE_PATTERN.sub(" ", text)

    # 3. Pipe noise (optional) - Markdown-aware (audit v8):
    # does NOT touch lines starting with "|" because those are
    # Markdown table lines (injected by Eureka via pdfplumber).
    # Otherwise the "X | Y" -> "XY" pattern would destroy column
    # separators in headers ("Affaire | Poste | Qte" -> "AffairePosteQte").
    if cleanup_pipes:
        out_lines: list[str] = []
        for line in text.split("\n"):
            if line.lstrip().startswith("|"):
                # Markdown table line: structural pipes, left intact.
                out_lines.append(line)
                continue
            # Repeat: "Chi | mie | BERTAUX" -> "ChimieBERTAUX"
            prev = None
            cleaned = line
            while prev != cleaned:
                prev = cleaned
                cleaned = _PIPE_NOISE_PATTERN.sub(r"\1\2", cleaned)
            out_lines.append(cleaned)
        text = "\n".join(out_lines)

    # 4. Multiple spaces
    if normalize_spaces:
        text = _MULTI_SPACES_PATTERN.sub(" ", text)

    # 5. Language detection
    lang = language or detect_language(text)

    return NormalizedDocument(
        source_path=doc.source_path,
        text=text,
        language=lang,
        encoding=doc.encoding,
        metadata={
            **doc.metadata,
            "normalize_spaces": normalize_spaces,
            "cleanup_pipes": cleanup_pipes,
        },
    )
