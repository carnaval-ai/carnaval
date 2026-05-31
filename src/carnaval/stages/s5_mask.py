# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Stage 5 - Mask: applying placeholders + feeding the vault.

Responsibilities:
- Assign a placeholder to each Span
- Guarantee consistency: same original value -> same placeholder
- Singleton types (`ORG_SINGLETON`) -> placeholder without index
- Other types -> indexed placeholder `[TYPE_n]`
- Build the anonymized text (substitution from-end-to-start to avoid
  breaking offsets)

Input: ResolvedDocument + Vault
Output: MaskedDocument
"""

from __future__ import annotations

import re
from dataclasses import replace as dc_replace
from typing import Any

from carnaval.core.span import Span
from carnaval.core.vault import Vault
from carnaval.stages.documents import MaskedDocument, ResolvedDocument


# Post-tokenization normalization (audit v2 VN8 + audit v3 R4).
#
# Pattern A: A tokenized token followed by a single UPPERCASE LETTER
# preceding a punctuation mark - this is typically a residual fragment
# of a proper name adjacent to the token ("(A2569 - Renault G)" tokenized
# as "(A2569 - [ORG_1] G)" - we remove the `G`).
_POST_TOKEN_TRAILING_LETTER = re.compile(
    r"(\[[A-Z_]+(?:_\d+)?\])\s+([A-Z])(?=[\s,;:\)\]\.])"
)

# Pattern B (audit v3 R4): A token directly adjacent to a single letter in CAPS
# that precedes a space/punctuation. Observed examples:
#   "[ORG_1]L au capital"  -> orphan of SARL (the SAR was tokenized)
#   "[ORG_1]S au"          -> orphan of SAS / SA
# The orphan letter is generally from a corporate name whose legal suffix
# was split into multiple spans. We remove the letter when it is single,
# in CAPS, and adjacent to the token.
_POST_TOKEN_ADJACENT_LETTER = re.compile(
    r"(\[[A-Z_]+(?:_\d+)?\])([A-Z])(?=\s|$|[^A-Za-z])"
)


def _normalize_post_tokens(text: str) -> str:
    """Post-tokenization cleanup.

    1. Remove orphan letters in CAPS that FOLLOW a token and
       precede punctuation (case `[ORG_1] G,`).
    2. Remove orphan letters in CAPS that are ADJACENT to a
       token and precede a space (case `[ORG_1]L au capital`, remainder of SARL).
    """
    text = _POST_TOKEN_TRAILING_LETTER.sub(r"\1", text)
    text = _POST_TOKEN_ADJACENT_LETTER.sub(r"\1", text)
    return text

# Types pour lesquels on emet un placeholder sans index (singleton).
DEFAULT_SINGLETON_TYPES = frozenset({"ORG_SINGLETON"})


# Mapping entity_type -> prefix used in the placeholder.
# The suffix `_n` is added for non-singleton types.
# Audit v7 phase 2: SEMANTIC placeholders to guide the downstream extraction AI.
# Explicit distinction between client (deploying customer singleton) vs
# supplier, contacts (people), addresses, refs, codes, etc.
# User recommendation (Patrice) post-audit v6.
DEFAULT_PLACEHOLDER_PREFIX = {
    # Companies: distinction between client (the recipient company of
    # the AR) vs supplier (the sender).
    "ORG_SINGLETON": "CLIENT_NAME",       # singleton = the deploying customer
    "ORGANIZATION": "FOURNISSEUR",        # other ORGs = suppliers
    # People: contacts (sales reps, buyers, signees...)
    "PERSON": "CONTACT",
    # Addresses
    "LOCATION": "ADRESSE",
    "ADDRESS": "ADRESSE",
    # Coordinates (technical identifiers, kept distinct for downstream AI clarity)
    "EMAIL": "EMAIL",
    "PHONE": "PHONE",
    "URL": "URL",
    # Fiscal / legal identifiers (kept distinct because they are useful
    # for the downstream extraction AI)
    "SIRET": "SIRET",
    "SIREN": "SIREN",
    "VAT": "VAT",
    "APE_CODE": "APE",
    "CAPITAL": "CAPITAL",
    "RIB": "RIB",
    "IBAN": "IBAN",
    "BIC": "BIC",
    "NATIONAL_ID": "NATID",
    "DATE_OF_BIRTH": "DOB",
    "NRP": "NRP",
    # Commercial references client-side
    "ORDER_REF": "REF_COMMANDE_CLIENT",
    "CLIENT_CODE": "CODE_CLIENT",
    "AFFAIR_NUMBER": "REF_AFFAIRE_CLIENT",
    # Internal / technical references
    "INTERNAL_REF": "REF",
    "TRACKING": "TRACKING",
    "ORG_STRUCTURE": "SERVICE",
    "COMMENT": "COMMENT",
    "DATE": "DATE",
}


class PlaceholderAllocator:
    """Distribue les placeholders en garantissant la coherence via Vault."""

    def __init__(
        self,
        vault: Vault,
        prefix_map: dict[str, str] | None = None,
        singleton_types: frozenset[str] | None = None,
        opaque_suffix: bool = False,
    ):
        """
        Args:
            opaque_suffix: If True, the sequential numerical index
                (_1, _2, _3) is replaced by a short opaque hash
                derived from the original value (_a8f7, _b3c2). Prevents
                a downstream LLM from "guessing" by order correlation that
                ([ADRESSE_1], [ADRESSE_2]) are (billing_address,
                shipping_address) based on their canonical position in an AR.
                Default: False (retro compatibility).
        """
        self._vault = vault
        self._prefix_map = prefix_map or DEFAULT_PLACEHOLDER_PREFIX
        self._singletons = singleton_types or DEFAULT_SINGLETON_TYPES
        self._counters: dict[str, int] = {}
        self._opaque_suffix = opaque_suffix

    def allocate(self, entity_type: str, original: str) -> str:
        """Return the placeholder for an original value.

        If the value is already in the vault, we return the existing placeholder
        (ensures consistency). Otherwise, we allocate a new one and record it.
        """
        existing = self._vault.get_placeholder(original)
        if existing:
            return existing

        prefix = self._prefix_map.get(entity_type, entity_type)
        if entity_type in self._singletons:
            placeholder = f"[{prefix}]"
        elif self._opaque_suffix:
            # Opaque hash derived from the original value. Stable (same
            # value -> same placeholder), but gives no clue
            # about the position in the document. The downstream LLM can
            # no longer correlate "_1" = "billing", "_2" = "delivery".
            import hashlib
            h = hashlib.sha256(original.encode("utf-8")).hexdigest()[:4]
            placeholder = f"[{prefix}_{h}]"
            # Unlikely but possible collision: if already taken, increase
            # hash length until uniqueness (max 8 chars).
            attempt = 4
            while self._vault.get_original(placeholder) and attempt < 8:
                attempt += 1
                h = hashlib.sha256(original.encode("utf-8")).hexdigest()[:attempt]
                placeholder = f"[{prefix}_{h}]"
        else:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            placeholder = f"[{prefix}_{self._counters[prefix]}]"

        self._vault.store(placeholder, original)
        return placeholder


def mask(
    doc: ResolvedDocument,
    vault: Vault,
    *,
    prefix_map: dict[str, str] | None = None,
    singleton_types: frozenset[str] | None = None,
    opaque_suffix: bool = False,
) -> MaskedDocument:
    """Apply placeholders to resolved text.

    Substitution strategy: we replace spans **from right to left**
    to avoid invalidating offsets of subsequent spans.

    Args:
        doc: ResolvedDocument (non-overlapping, sorted spans).
        vault: Vault to be populated.
        prefix_map: Override of entity_type -> prefix mapping.
        singleton_types: Override of the singleton types set.
        opaque_suffix: H3 (audit v7) - use an opaque hash instead of
            a sequential index. Prevents a downstream LLM from inferring the
            canonical position of entities in the document.

    Returns:
        MaskedDocument with anonymized text and spans enriched with placeholder.
    """
    allocator = PlaceholderAllocator(
        vault=vault,
        prefix_map=prefix_map,
        singleton_types=singleton_types,
        opaque_suffix=opaque_suffix,
    )

    # Build placeholder for each span (position order)
    enriched_spans: list[Span] = []
    for s in doc.spans:
        ph = allocator.allocate(s.entity_type, s.text)
        new_meta: dict[str, Any] = {**s.metadata, "placeholder": ph}
        enriched_spans.append(dc_replace(s, metadata=new_meta))

    # Substitution from right to left
    text = doc.text
    for s in sorted(enriched_spans, key=lambda x: x.start, reverse=True):
        ph = s.metadata["placeholder"]
        text = text[: s.start] + ph + text[s.end :]

    # Post-tokenization normalization (audit v2 VN8): clean up residual
    # orphan characters indicating a name was adjacent. Examples:
    #   "[ORG_1] G,"  ->  "[ORG_1],"  (the final `G` of "Renault G"
    #                                  signaling "Group")
    #   "[VAT_3][ORG]" ->  "[VAT_3] [ORG]"  (consolidation of adjacent
    #                                         tokens for readability)
    text = _normalize_post_tokens(text)

    by_category: dict[str, int] = {}
    for s in enriched_spans:
        by_category[s.entity_type] = by_category.get(s.entity_type, 0) + 1

    return MaskedDocument(
        source_path=doc.source_path,
        original_text=doc.text,
        anonymized_text=text,
        language=doc.language,
        spans=tuple(enriched_spans),
        by_category=by_category,
        metadata=doc.metadata,
    )
