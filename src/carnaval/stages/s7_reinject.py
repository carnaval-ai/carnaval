# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Stage 7 - Reinject: restoring original values in JSON/XML.

INVERSE stage of the pipeline. The cloud LLM returns a structure (JSON or XML)
containing placeholders `[TYPE_n]` or `[TYPE]`. This step recursively walks
the structure and restores real values from the Vault.

Supported inputs:
    - dict / list / str (Python objects already parsed)
    - JSON str (auto-detect if starts with '{' or '[')
    - XML str  (auto-detect if starts with '<')
    - Path to a .json or .xml file
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from carnaval.core.vault import Vault

# Pattern that matches any placeholder produced by S5:
#   [PERSON_1], [EMAIL_42], [ORG], [VAT_3], etc.
# H3 v7: also accepts alphanumeric suffixes (opaque hashes
# `_89d6`, `_703a`) and compound prefixes (REF_COMMANDE_CLIENT,
# CLIENT_NAME, FOURNISSEUR). Major v7 bug fixed: without this update,
# NO opaque placeholder was reinjected by the vault
# - the final business JSON contained [REF_COMMANDE_CLIENT_89d6]
# instead of the PO reinjected from the encrypted vault.
PLACEHOLDER_PATTERN = re.compile(r"\[([A-Z][A-Z_]*(?:_[A-Za-z0-9]+)?)\]")


# List of placeholder prefixes that we accept to match bare.
_BARE_PLACEHOLDER_TYPES = (
    r"ORG|"
    r"SUPPLIER_\d+|PERSON_\d+|EMAIL_\d+|PHONE_\d+|ADDR_\d+|LOCATION_\d+|"
    r"SIREN_\d+|SIRET_\d+|VAT_\d+|IBAN_\d+|BIC_\d+|URL_\d+|ORG_\d+|NRP_\d+"
)

# Pattern: placeholder without brackets, but ALONE in the string (anchors).
PLACEHOLDER_PATTERN_BARE = re.compile(rf"^({_BARE_PLACEHOLDER_TYPES})$")

# Pattern: placeholder without brackets, INLINE (in the middle of a sentence).
# Some LLMs drop brackets even when the placeholder is included
# in a sentence ("Delivered to ADDR_2", "2-ADDR_4 communication interface").
# Strict word boundaries to avoid matching substrings.
PLACEHOLDER_PATTERN_BARE_INLINE = re.compile(rf"\b({_BARE_PLACEHOLDER_TYPES})\b")


def _restore_in_string(text: str, vault: Vault) -> str:
    """Replace all placeholders in a string with their original value.

    Handles three formats:
    - Standard `[TYPE_n]`
    - `TYPE_n` bare-only (string = single placeholder)
    - `... TYPE_n ...` bare-inline (placeholder inside a sentence)
    """

    def repl_standard(match: re.Match) -> str:
        ph = match.group(0)
        original = vault.get_original(ph)
        return original if original is not None else ph

    out = PLACEHOLDER_PATTERN.sub(repl_standard, text)

    # Fallback 1: the COMPLETE value is a bare placeholder ("ORG_1")
    if out and PLACEHOLDER_PATTERN_BARE.match(out):
        wrapped = f"[{out}]"
        original = vault.get_original(wrapped)
        if original is not None:
            return original

    # Fallback 2: bare placeholder in the middle of a sentence
    # ("Delivered to ADDR_2", "2-ADDR_4 communication...")
    def repl_bare_inline(match: re.Match) -> str:
        ph_bare = match.group(0)
        wrapped = f"[{ph_bare}]"
        original = vault.get_original(wrapped)
        return original if original is not None else ph_bare

    out = PLACEHOLDER_PATTERN_BARE_INLINE.sub(repl_bare_inline, out)

    return out


# ----------------------------------------------------------------------
# JSON
# ----------------------------------------------------------------------


def reinject_json_data(data: Any, vault: Vault) -> Any:
    """Recursive traversal of a JSON-like structure and restoration.

    Args:
        data: dict, list, str, or scalar.
        vault: Loaded Vault.

    Returns:
        Structure of the same shape, with placeholders replaced.
    """
    if isinstance(data, str):
        return _restore_in_string(data, vault)
    if isinstance(data, dict):
        return {k: reinject_json_data(v, vault) for k, v in data.items()}
    if isinstance(data, list):
        return [reinject_json_data(item, vault) for item in data]
    if isinstance(data, tuple):
        return tuple(reinject_json_data(item, vault) for item in data)
    return data


def reinject_json_string(json_str: str, vault: Vault) -> str:
    """Parse a JSON, restore, re-serialize. Preserves indentation of 2."""
    parsed = json.loads(json_str)
    restored = reinject_json_data(parsed, vault)
    return json.dumps(restored, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------
# XML
# ----------------------------------------------------------------------


def _restore_in_element(elem: ET.Element, vault: Vault) -> None:
    """Recursive restoration of an XML node (mutates the tree)."""
    if elem.text:
        elem.text = _restore_in_string(elem.text, vault)
    if elem.tail:
        elem.tail = _restore_in_string(elem.tail, vault)
    # Attributes
    for attr_key, attr_val in list(elem.attrib.items()):
        elem.attrib[attr_key] = _restore_in_string(attr_val, vault)
    # Children
    for child in elem:
        _restore_in_element(child, vault)


def reinject_xml_string(xml_str: str, vault: Vault) -> str:
    """Parse an XML, restore, re-serialize."""
    root = ET.fromstring(xml_str)
    _restore_in_element(root, vault)
    return ET.tostring(root, encoding="unicode")


# ----------------------------------------------------------------------
# Auto-detection + entry point
# ----------------------------------------------------------------------


def reinject_file(input_path: Path | str, vault: Vault) -> str:
    """Auto-detect JSON vs XML based on extension OR content.

    Args:
        input_path: .json or .xml file.
        vault: Loaded Vault.

    Returns:
        Restored content as a string.
    """
    p = Path(input_path)
    content = p.read_text(encoding="utf-8")
    return reinject_string(content, vault)


def reinject_string(content: str, vault: Vault) -> str:
    """Restore in a string by auto-detecting JSON vs XML."""
    stripped = content.lstrip()
    if not stripped:
        return content
    first = stripped[0]
    if first in ("{", "["):
        return reinject_json_string(content, vault)
    if first == "<":
        return reinject_xml_string(content, vault)
    # Fallback: treat as raw text
    return _restore_in_string(content, vault)
