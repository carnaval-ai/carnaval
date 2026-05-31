# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Stage 1 - Intake: read the source file.

Responsibilities:
- Check file existence
- Read content as UTF-8 (fallback to latin-1 on failure)
- Capture metadata: size, encoding, mtime
- Reject empty or too large files (configurable)

Input: Path
Output: RawDocument
"""

from __future__ import annotations

from pathlib import Path

from carnaval.stages.documents import RawDocument


class IntakeError(Exception):
    """Input error (file not found, unreadable, too large, ...)."""


def intake(
    path: Path | str,
    max_size_bytes: int = 50 * 1024 * 1024,  # 50 MB
) -> RawDocument:
    """Read a .txt file into a RawDocument.

    Args:
        path: path to the file.
        max_size_bytes: maximum accepted size.

    Returns:
        Populated RawDocument.

    Raises:
        IntakeError: if the file is missing, empty, too large or unreadable.
    """
    p = Path(path)
    if not p.exists():
        raise IntakeError(f"File not found: {p}")
    if not p.is_file():
        raise IntakeError(f"Not a file: {p}")

    size = p.stat().st_size
    if size == 0:
        raise IntakeError(f"Empty file: {p}")
    if size > max_size_bytes:
        raise IntakeError(f"File too large: {size} bytes > {max_size_bytes}")

    # Read with encoding fallback
    encoding_used = "utf-8"
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        encoding_used = "latin-1"
        text = p.read_text(encoding="latin-1")

    return RawDocument(
        source_path=p,
        text=text,
        encoding=encoding_used,
        metadata={
            "size_bytes": size,
            "mtime": p.stat().st_mtime,
            "filename": p.name,
        },
    )
