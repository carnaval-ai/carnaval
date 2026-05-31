# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Layered configuration loading.

Merge strategy:
    1. base    → config/pipeline.yaml + files under config/*/*.yaml
    2. profile → profiles/<type>/profile.yaml + sub-files
    3. private → profiles_private/<custom>/profile.yaml + sub-files (optional)

Lists are CONCATENATED (deny_lists, allow_lists), dicts are deeply MERGED.
Scalar values from upper layers override lower layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    """Application configuration resolved through layered merging."""

    raw: dict[str, Any] = field(default_factory=dict)
    layers: list[str] = field(default_factory=list)  # names of merged layers

    # Typical fast accessors
    @property
    def pipeline(self) -> dict[str, Any]:
        return self.raw.get("pipeline", {})

    @property
    def patterns(self) -> dict[str, Any]:
        return self.raw.get("patterns", {})

    @property
    def deny_lists(self) -> dict[str, Any]:
        return self.raw.get("deny_lists", {})

    @property
    def allow_lists(self) -> dict[str, Any]:
        return self.raw.get("allow_lists", {})

    @property
    def policies(self) -> dict[str, Any]:
        return self.raw.get("policies", {})

    @property
    def ai_models(self) -> dict[str, Any]:
        return self.raw.get("ai_models", {})

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Dotted-path access: cfg.get('policies.priority_rules.DenylistRecognizer')."""
        parts = dotted_key.split(".")
        node: Any = self.raw
        for p in parts:
            if not isinstance(node, dict) or p not in node:
                return default
            node = node[p]
        return node


# ----------------------------------------------------------------------
# Merge utilities
# ----------------------------------------------------------------------


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge of two dictionaries.

    Rules:
    - dict + dict   → recursive key-by-key merge
    - list + list   → concatenation (no deduplication — caller's responsibility)
    - scalar + scalar → overlay wins
    - mixed types   → overlay wins (implicit warning)
    """
    result = dict(base)
    for key, val in overlay.items():
        if key in result:
            existing = result[key]
            if isinstance(existing, dict) and isinstance(val, dict):
                result[key] = _deep_merge(existing, val)
            elif isinstance(existing, list) and isinstance(val, list):
                result[key] = existing + val
            else:
                result[key] = val
        else:
            result[key] = val
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file. Returns {} if the file is empty or does not exist."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_directory_layer(dir_path: Path) -> dict[str, Any]:
    """Load all YAML files from a directory into a structured dict by subfolder.

    For a layout like:
        layer/
            pipeline.yaml
            patterns/
                fiscal_fr.yaml      → patterns.fiscal_fr.*
            deny_lists/
                organizations.yaml  → deny_lists.organizations.*

    File content replaces the corresponding sub-namespace.
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return {}

    out: dict[str, Any] = {}

    # 1. .yaml files directly at the layer root (e.g. pipeline.yaml, ai_models.yaml)
    for yml in sorted(dir_path.glob("*.yaml")):
        key = yml.stem
        data = _load_yaml(yml)
        # If the YAML contains a root key with the same name, merge it
        # Otherwise store the content under the key.
        if key in data and isinstance(data[key], dict):
            out[key] = _deep_merge(out.get(key, {}), data[key])
        else:
            out[key] = (
                _deep_merge(out.get(key, {}), data) if isinstance(data, dict) else data
            )

    # 2. subdirectories: patterns/, deny_lists/, allow_lists/, policies/
    #    + limited recursion for places/{fr,de,...}.yaml
    for sub in sorted(p for p in dir_path.iterdir() if p.is_dir()):
        sub_content: dict[str, Any] = {}
        # 2a. direct .yaml files (e.g. deny_lists/organizations.yaml)
        for yml in sorted(sub.glob("*.yaml")):
            sub_content[yml.stem] = _load_yaml(yml)
        # 2b. sub-subdirectories (e.g. deny_lists/places/fr.yaml)
        #     -> deny_lists.places = {fr: [...], de: [...], ...}
        for subsub in sorted(p for p in sub.iterdir() if p.is_dir()):
            lang_dict: dict[str, Any] = {}
            for yml in sorted(subsub.glob("*.yaml")):
                lang_dict[yml.stem] = _load_yaml(yml)
            if lang_dict:
                sub_content[subsub.name] = _deep_merge(
                    sub_content.get(subsub.name, {}), lang_dict
                )
        if sub_content:
            out[sub.name] = _deep_merge(out.get(sub.name, {}), sub_content)

    return out


# ----------------------------------------------------------------------
# API publique
# ----------------------------------------------------------------------

# Donnees livrees avec le paquet : src/carnaval/data/
_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_config(
    base_dir: Path | str | None = None,
    profile: str | None = None,
    private_profile: str | None = None,
    profiles_dir: Path | str | None = None,
    private_dir: Path | str | None = None,
    repo_root: Path | str | None = None,
) -> Config:
    """Load configuration in cascade: base → profile → private_profile.

    Args:
        base_dir: Path to the `config/` directory (default: config shipped with the package).
        profile: Name of the public profile to apply (e.g. 'acknowledge').
        private_profile: Name of the private profile (under profiles_private/).
        profiles_dir: Directory containing public profiles (default: profiles shipped
            with the package).
        private_dir: Directory containing private profiles (default: ./profiles_private
            in the current working directory).
        repo_root: Path to the repository root directory (optional).

    Returns:
        Resolved Config object.
    """
    if repo_root:
        repo_path = Path(repo_root)
        if not base_dir:
            base_dir = repo_path / "config"
        if not profiles_dir:
            profiles_dir = repo_path / "profiles"
        if not private_dir:
            private_dir = repo_path / "profiles_private"

    base_path = Path(base_dir) if base_dir else _DATA_DIR / "config"

    layers_loaded: list[str] = []
    merged: dict[str, Any] = {}

    # Layer 1: base
    base_layer = _load_directory_layer(base_path)
    if base_layer:
        merged = _deep_merge(merged, base_layer)
        layers_loaded.append(f"base:{base_path}")

    # Layer 2: public profile
    if profile:
        prof_base = Path(profiles_dir) if profiles_dir else _DATA_DIR / "profiles"
        prof_path = prof_base / profile
        prof_layer = _load_directory_layer(prof_path)
        if not prof_layer:
            raise FileNotFoundError(f"Profil introuvable : {prof_path}")
        merged = _deep_merge(merged, prof_layer)
        layers_loaded.append(f"profile:{profile}")

    # Layer 3: private profile (optional)
    if private_profile:
        priv_base = Path(private_dir) if private_dir else Path.cwd() / "profiles_private"
        priv_path = priv_base / private_profile
        priv_layer = _load_directory_layer(priv_path)
        if not priv_layer:
            raise FileNotFoundError(f"Profil prive introuvable : {priv_path}")
        merged = _deep_merge(merged, priv_layer)
        layers_loaded.append(f"private:{private_profile}")

    return Config(raw=merged, layers=layers_loaded)
