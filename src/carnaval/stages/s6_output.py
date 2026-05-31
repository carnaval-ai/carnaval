# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Stage 6 - Output: writing results to disk in multiple formats.

Responsibilities:
- Write the anonymized text (.txt)
- Write the business JSON (entities + meta)
- Write the JSONL (entity streaming)
- Write the XML
- Write the CoNLL (for NER training)
- Write the HTML (visualization)
- Write the encrypted vault
- Write the meta.json (audit)

Input: MaskedDocument + Vault + output directory
Output: WrittenOutput (paths of written files)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from carnaval.core.serializers import (
    to_conll,
    to_html,
    to_json,
    to_jsonl,
    to_txt,
    to_xml,
)
from carnaval.core.vault import Vault
from carnaval.stages.documents import MaskedDocument, WrittenOutput


def _safe_write(path: Path, content: str | bytes) -> None:
    """Writes ensuring the parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def output(
    doc: MaskedDocument,
    vault: Vault,
    outbox_dir: Path | str,
    *,
    duration_seconds: float | None = None,
) -> WrittenOutput:
    """Writes all output formats in parallel.

    Layout produced:
        outbox/
            txt/<stem>_anonymise.txt
            json/<stem>_anonymise.json
            jsonl/<stem>_entities.jsonl
            xml/<stem>_anonymise.xml
            conll/<stem>_anonymise.conll
            html/<stem>_anonymise.html
            vault/<stem>_vault.enc
            meta/<stem>_meta.json
    """
    outbox = Path(outbox_dir)
    stem = doc.source_path.stem

    paths = WrittenOutput(
        txt_path=outbox / "txt" / f"{stem}_anonymise.txt",
        json_path=outbox / "json" / f"{stem}_anonymise.json",
        jsonl_path=outbox / "jsonl" / f"{stem}_entities.jsonl",
        xml_path=outbox / "xml" / f"{stem}_anonymise.xml",
        conll_path=outbox / "conll" / f"{stem}_anonymise.conll",
        html_path=outbox / "html" / f"{stem}_anonymise.html",
        vault_path=outbox / "vault" / f"{stem}_vault.enc",
        meta_path=outbox / "meta" / f"{stem}_meta.json",
    )

    # Write output formats
    _safe_write(paths.txt_path, to_txt(doc))
    _safe_write(paths.json_path, to_json(doc))
    _safe_write(paths.jsonl_path, to_jsonl(doc))
    _safe_write(paths.xml_path, to_xml(doc))
    _safe_write(paths.conll_path, to_conll(doc))
    _safe_write(paths.html_path, to_html(doc))

    # Encrypted vault
    paths.vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault.path = paths.vault_path
    vault.save()

    # Metadata (audit) - no sensitive data
    meta = {
        "source": str(doc.source_path),
        "language": doc.language,
        "num_spans": len(doc.spans),
        "by_category": doc.by_category,
        "outputs": {
            "txt": str(paths.txt_path),
            "json": str(paths.json_path),
            "jsonl": str(paths.jsonl_path),
            "xml": str(paths.xml_path),
            "conll": str(paths.conll_path),
            "html": str(paths.html_path),
            "vault": str(paths.vault_path),
        },
        "timestamp": time.time(),
        "duration_seconds": duration_seconds,
    }
    _safe_write(paths.meta_path, json.dumps(meta, ensure_ascii=False, indent=2))

    return paths
