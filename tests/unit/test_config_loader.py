"""Tests unitaires du chargeur de configuration en couches."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from carnaval.core.config_loader import Config, _deep_merge, load_config


# ============================================================================
# Tests du merge profond
# ============================================================================


class TestDeepMerge:
    def test_dict_merge(self):
        a = {"x": 1, "y": 2}
        b = {"y": 20, "z": 30}
        assert _deep_merge(a, b) == {"x": 1, "y": 20, "z": 30}

    def test_nested_dict_merge(self):
        a = {"top": {"x": 1, "y": 2}}
        b = {"top": {"y": 20, "z": 30}}
        assert _deep_merge(a, b) == {"top": {"x": 1, "y": 20, "z": 30}}

    def test_list_concatenation(self):
        a = {"items": [1, 2, 3]}
        b = {"items": [4, 5]}
        assert _deep_merge(a, b) == {"items": [1, 2, 3, 4, 5]}

    def test_scalar_overwrite(self):
        a = {"x": 1}
        b = {"x": 99}
        assert _deep_merge(a, b) == {"x": 99}

    def test_mixed_types_overlay_wins(self):
        a = {"x": [1, 2]}
        b = {"x": "scalar"}
        assert _deep_merge(a, b) == {"x": "scalar"}

    def test_base_unchanged(self):
        a = {"x": [1, 2]}
        b = {"x": [3]}
        result = _deep_merge(a, b)
        assert a == {"x": [1, 2]}
        assert result == {"x": [1, 2, 3]}


# ============================================================================
# Tests de chargement par couches
# ============================================================================


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Cree une mini-arborescence repo avec config/ et profiles/ pour tests."""
    # config/ base
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pipeline.yaml").write_text(yaml.safe_dump({
        "language": "fr",
        "threshold": 0.4,
    }), encoding="utf-8")

    (tmp_path / "config" / "deny_lists").mkdir()
    (tmp_path / "config" / "deny_lists" / "organizations.yaml").write_text(
        yaml.safe_dump({"organizations": ["Acme", "Globex"]}), encoding="utf-8"
    )

    # profiles/acknowledge
    prof = tmp_path / "profiles" / "acknowledge"
    prof.mkdir(parents=True)
    (prof / "profile.yaml").write_text(yaml.safe_dump({"name": "acknowledge"}), encoding="utf-8")
    (prof / "deny_lists").mkdir()
    (prof / "deny_lists" / "organizations.yaml").write_text(
        yaml.safe_dump({"organizations": ["Initech"]}), encoding="utf-8"
    )

    # profiles_private/custom
    priv = tmp_path / "profiles_private" / "custom"
    priv.mkdir(parents=True)
    (priv / "deny_lists").mkdir()
    (priv / "deny_lists" / "organizations.yaml").write_text(
        yaml.safe_dump({"organizations": ["SecretCo"]}), encoding="utf-8"
    )

    return tmp_path


class TestLoadConfigLayers:
    def test_base_only(self, fake_repo: Path):
        cfg = load_config(repo_root=fake_repo)
        assert cfg.raw["pipeline"]["language"] == "fr"
        assert cfg.deny_lists["organizations"]["organizations"] == ["Acme", "Globex"]
        assert cfg.layers == [f"base:{fake_repo / 'config'}"]

    def test_with_profile(self, fake_repo: Path):
        cfg = load_config(repo_root=fake_repo, profile="acknowledge")
        # Les listes doivent etre concatenees
        orgs = cfg.deny_lists["organizations"]["organizations"]
        assert orgs == ["Acme", "Globex", "Initech"]
        assert "profile:acknowledge" in cfg.layers

    def test_with_private_profile(self, fake_repo: Path):
        cfg = load_config(
            repo_root=fake_repo,
            profile="acknowledge",
            private_profile="custom",
        )
        orgs = cfg.deny_lists["organizations"]["organizations"]
        assert orgs == ["Acme", "Globex", "Initech", "SecretCo"]
        assert "private:custom" in cfg.layers

    def test_missing_profile_raises(self, fake_repo: Path):
        with pytest.raises(FileNotFoundError):
            load_config(repo_root=fake_repo, profile="nonexistent")

    def test_missing_private_profile_raises(self, fake_repo: Path):
        with pytest.raises(FileNotFoundError):
            load_config(
                repo_root=fake_repo, profile="acknowledge", private_profile="nope"
            )

    def test_get_dotted_path(self, fake_repo: Path):
        cfg = load_config(repo_root=fake_repo)
        assert cfg.get("pipeline.language") == "fr"
        assert cfg.get("pipeline.threshold") == 0.4
        assert cfg.get("does.not.exist") is None
        assert cfg.get("does.not.exist", default="fallback") == "fallback"


class TestConfigAccessors:
    def test_empty_config(self):
        cfg = Config()
        assert cfg.pipeline == {}
        assert cfg.deny_lists == {}
        assert cfg.patterns == {}
        assert cfg.allow_lists == {}
        assert cfg.policies == {}
        assert cfg.ai_models == {}

    def test_raw_access(self):
        cfg = Config(raw={"custom": {"key": "value"}})
        assert cfg.get("custom.key") == "value"
