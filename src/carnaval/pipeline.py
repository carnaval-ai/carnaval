# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Carnaval pipeline orchestrator.

Composes stages S1 -> S6 into a single call. Contains NO business logic,
only the wiring.

Three public entry points, from highest to lowest level:

    run_anonymization_from_pdf(pdf_path, ...)
        PDF -> layout-aware extraction -> text -> pipeline
    run_anonymization(input_path, ...)
        .txt file on disk -> pipeline
    run_anonymization_from_text(text, ...)
        text already in memory (e.g. pre-extracted by Eureka) -> pipeline

All three converge on `_run_pipeline_from_raw`, which executes S2 -> S6.
"""

from __future__ import annotations

import time
from pathlib import Path

from carnaval.core.config_loader import Config, load_config
from carnaval.core.logger import get_logger
from carnaval.core.pdf import extract_text_from_pdf
from carnaval.core.vault import Vault
from carnaval.stages.documents import MaskedDocument, RawDocument, WrittenOutput
from carnaval.stages.s1_intake import intake
from carnaval.stages.s2_preprocess import preprocess
from carnaval.stages.s3_detect import detect
from carnaval.stages.s4_resolve import resolve
from carnaval.stages.s5_mask import mask
from carnaval.stages.s6_output import output


# Default source shown in logs and the `source_path` of RawDocument
# when feeding the pipeline from memory (no file on disk).
# The name is also used as filename stem for S6 artifacts,
# so it must be valid on Windows / Linux / macOS (no angle brackets,
# slashes, or reserved characters).
_DEFAULT_MEMORY_SOURCE = "in-memory"


def _run_pipeline_from_raw(
    raw_doc: RawDocument,
    outbox_dir: Path | str,
    vault_password: str,
    *,
    profile: str | None = None,
    private_profile: str | None = None,
    use_gliner: bool = True,
    gliner_threshold: float = 0.4,
    cleanup_pipes: bool = False,
    language: str | None = None,
    repo_root: Path | str | None = None,
) -> tuple[MaskedDocument, WrittenOutput, Config]:
    """Execute stages S2 -> S6 from an already-built RawDocument.

    This internal function is the single convergence point for the three
    public entry points: it materializes the chain
    preprocess -> detect -> resolve -> mask -> output. A single source
    of truth simplifies pipeline evolution (new profile or detection param
    changed in exactly one place).
    """
    log = get_logger()
    t0 = time.time()

    config = load_config(profile=profile, private_profile=private_profile, repo_root=repo_root)
    log.info("config_loaded", layers=config.layers)

    log.info("s1_intake_done", size_bytes=raw_doc.length)

    norm_doc = preprocess(raw_doc, language=language, cleanup_pipes=cleanup_pipes)
    log.info("s2_preprocess_done", language=norm_doc.language)

    det_doc = detect(
        norm_doc,
        config,
        use_gliner=use_gliner,
        gliner_threshold=gliner_threshold,
    )
    log.info("s3_detect_done", raw_spans=len(det_doc.spans))

    res_doc = resolve(det_doc)
    log.info(
        "s4_resolve_done",
        resolved_spans=len(res_doc.spans),
        dropped=len(det_doc.spans) - len(res_doc.spans),
    )

    vault = Vault(password=vault_password)
    masked_doc = mask(res_doc, vault)
    log.info(
        "s5_mask_done",
        anonymized_chars=len(masked_doc.anonymized_text),
        by_category=masked_doc.by_category,
    )

    duration = time.time() - t0
    written = output(masked_doc, vault, outbox_dir, duration_seconds=duration)
    log.info(
        "s6_output_done",
        duration_seconds=round(duration, 2),
        outbox=str(outbox_dir),
    )

    return masked_doc, written, config


def run_anonymization(
    input_path: Path | str,
    outbox_dir: Path | str,
    vault_password: str,
    *,
    profile: str | None = None,
    private_profile: str | None = None,
    use_gliner: bool = True,
    gliner_threshold: float = 0.4,
    cleanup_pipes: bool = False,
    language: str | None = None,
    repo_root: Path | str | None = None,
) -> tuple[MaskedDocument, WrittenOutput, Config]:
    """Full S1 -> S6 pipeline from a .txt file on disk.

    Args:
        input_path: path to the .txt file to anonymize. Text is consumed
            line by line; it MUST follow the layout contract documented in
            `carnaval.core.pdf` (one visual block per line, `[PAGE n]`
            markers between pages) so that layout-aware protections
            (table_body, cross-page propagation) work correctly.
        outbox_dir: output directory (subdirs txt/json/... will be created).
        vault_password: password for the encrypted vault (min 16 chars).
        profile: business profile name (e.g. 'acknowledge').
        private_profile: private profile name (under profiles_private/).
        use_gliner: True to enable AI detection (slow on first call).
        gliner_threshold: GLiNER confidence threshold.
        cleanup_pipes: True to remove stray `|` between words.
        language: force language ('fr', 'en', 'de', 'ja'). Auto if None.
        repo_root: repository root directory.

    Returns:
        (MaskedDocument, WrittenOutput, Config)
    """
    raw_doc = intake(input_path)
    return _run_pipeline_from_raw(
        raw_doc,
        outbox_dir=outbox_dir,
        vault_password=vault_password,
        profile=profile,
        private_profile=private_profile,
        use_gliner=use_gliner,
        gliner_threshold=gliner_threshold,
        cleanup_pipes=cleanup_pipes,
        language=language,
        repo_root=repo_root,
    )


def run_anonymization_from_text(
    text: str,
    outbox_dir: Path | str,
    vault_password: str,
    *,
    profile: str | None = None,
    private_profile: str | None = None,
    use_gliner: bool = True,
    gliner_threshold: float = 0.4,
    cleanup_pipes: bool = False,
    language: str | None = None,
    source_name: str = _DEFAULT_MEMORY_SOURCE,
    repo_root: Path | str | None = None,
) -> tuple[MaskedDocument, WrittenOutput, Config]:
    """Full pipeline from text already in memory.

    Nominal path when an upstream extractor (typically Eureka, which
    filters CGV pages and applies its own `max_pages` logic) wants to
    delegate only the anonymization phase to Carnaval. No intermediate
    file is written to disk.

    **Expected layout contract**: the provided `text` must follow the
    layout-aware convention described in `carnaval.core.pdf`:

    - visual blocks separated by `\n` (one block = one paragraph or
      table cell);
    - top->bottom / left->right order (PyMuPDF blocks-sorted);
    - `[PAGE n]` markers between pages (1-based), separated by a blank line.

    Text that does not follow this contract (linear / "flat" extraction)
    will still work — regex recognizers will match — but will lose
    layout-aware protections: `core.table_body` will no longer distinguish
    line items, and article references may be mistaken for phones.

    Args:
        text: text already extracted, compliant with the contract above.
        outbox_dir: output directory.
        vault_password: vault password (min 16 chars).
        profile: business profile (e.g. 'acknowledge').
        private_profile: private profile (under profiles_private/).
        use_gliner: True to enable AI detection.
        gliner_threshold: GLiNER confidence threshold.
        cleanup_pipes: True to remove stray `|` characters.
        language: force language ('fr', 'en', ...). Auto if None.
        source_name: logical source identifier, copied into the
            `source_path` of RawDocument and useful for logs / traceability
            (e.g. original PDF name from Eureka side).
        repo_root: repository root directory.

    Returns:
        (MaskedDocument, WrittenOutput, Config) — identical to the other entry points.

    Raises:
        ValueError: if `text` is empty.
    """
    if not text or not text.strip():
        raise ValueError("text est vide : rien a anonymiser")
    raw_doc = RawDocument(
        source_path=Path(source_name),
        text=text,
        encoding="utf-8",
        metadata={
            "size_bytes": len(text.encode("utf-8")),
            "filename": source_name,
            "source": "in_memory",
        },
    )
    return _run_pipeline_from_raw(
        raw_doc,
        outbox_dir=outbox_dir,
        vault_password=vault_password,
        profile=profile,
        private_profile=private_profile,
        use_gliner=use_gliner,
        gliner_threshold=gliner_threshold,
        cleanup_pipes=cleanup_pipes,
        language=language,
        repo_root=repo_root,
    )


def run_anonymization_from_pdf(
    pdf_path: Path | str,
    outbox_dir: Path | str,
    vault_password: str,
    *,
    profile: str | None = None,
    private_profile: str | None = None,
    use_gliner: bool = True,
    gliner_threshold: float = 0.4,
    cleanup_pipes: bool = False,
    language: str | None = None,
    repo_root: Path | str | None = None,
) -> tuple[MaskedDocument, WrittenOutput, Config]:
    """Full pipeline: PDF -> spatially structured text -> anonymized.

    Convenient to plug Carnaval directly onto a PDF without going through
    an intermediate .txt file. Extraction uses PyMuPDF in `blocks` mode
    sorted by visual position: top->bottom / left->right order is preserved,
    avoiding the interleaving of footers and multi-page tables produced by
    1D extractions. See `carnaval.core.pdf` for contract details.

    Note: this entry point extracts the ENTIRE PDF (all pages). If you
    want to exclude terms & conditions pages or bound the page count,
    perform your own upstream extraction (e.g. via
    `eureka.core.pdf_extractor.extract_text_from_pdf`) and pass the
    resulting text to `run_anonymization_from_text`.

    Args:
        pdf_path: path to the PDF to anonymize.
        outbox_dir: output directory (subdirs txt/json/... will be created).
        vault_password: encrypted vault password (min 16 chars).
        profile: business profile name (e.g. 'acknowledge').
        private_profile: private profile name (under profiles_private/).
        use_gliner: True to enable AI detection (slow on first call).
        gliner_threshold: GLiNER confidence threshold.
        cleanup_pipes: True to remove stray `|` between words.
        language: force language ('fr', 'en', 'de', 'ja'). Auto if None.
        repo_root: repository root directory.

    Returns:
        (MaskedDocument, WrittenOutput, Config) — identical to run_anonymization.

    Raises:
        FileNotFoundError: if the PDF does not exist.
    """
    pdf = Path(pdf_path)
    text = extract_text_from_pdf(pdf)
    return run_anonymization_from_text(
        text,
        outbox_dir=outbox_dir,
        vault_password=vault_password,
        profile=profile,
        private_profile=private_profile,
        use_gliner=use_gliner,
        gliner_threshold=gliner_threshold,
        cleanup_pipes=cleanup_pipes,
        language=language,
        source_name=pdf.name,
        repo_root=repo_root,
    )
