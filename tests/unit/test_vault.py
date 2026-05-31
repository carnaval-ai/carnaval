"""Tests unitaires du vault AES-256-GCM."""

from __future__ import annotations

from pathlib import Path

import pytest

from carnaval.core.vault import Vault, VaultError


VALID_PWD = "test_password_long_enough_32_chars"


class TestVaultBasic:
    def test_store_and_get(self):
        v = Vault(password=VALID_PWD)
        v.store("[PERSON_1]", "Alice")
        assert v.get_original("[PERSON_1]") == "Alice"
        assert v.get_placeholder("Alice") == "[PERSON_1]"

    def test_get_unknown(self):
        v = Vault(password=VALID_PWD)
        assert v.get_original("[UNKNOWN]") is None
        assert v.get_placeholder("Inconnu") is None

    def test_len(self):
        v = Vault(password=VALID_PWD)
        assert len(v) == 0
        v.store("[X_1]", "x")
        v.store("[X_2]", "y")
        assert len(v) == 2


class TestVaultPasswordValidation:
    def test_empty_password(self):
        with pytest.raises(VaultError, match="trop court"):
            Vault(password="")

    def test_short_password(self):
        with pytest.raises(VaultError, match="trop court"):
            Vault(password="short")


class TestVaultPersistence:
    def test_save_and_reload(self, tmp_path: Path):
        path = tmp_path / "vault.enc"
        v1 = Vault(password=VALID_PWD, path=path)
        v1.store("[PERSON_1]", "Alice")
        v1.store("[ORG_1]", "Acme Corp")
        v1.save()

        assert path.exists()
        assert path.stat().st_size > 0

        v2 = Vault(password=VALID_PWD, path=path)
        v2.load()
        assert v2.get_original("[PERSON_1]") == "Alice"
        assert v2.get_original("[ORG_1]") == "Acme Corp"
        assert len(v2) == 2

    def test_wrong_password_raises(self, tmp_path: Path):
        path = tmp_path / "vault.enc"
        v1 = Vault(password=VALID_PWD, path=path)
        v1.store("[X]", "secret")
        v1.save()

        v2 = Vault(password="another_password_long_enough", path=path)
        with pytest.raises(VaultError, match="Mauvais password"):
            v2.load()

    def test_corrupted_file_raises(self, tmp_path: Path):
        path = tmp_path / "vault.enc"
        path.write_bytes(b"too_short")
        v = Vault(password=VALID_PWD, path=path)
        with pytest.raises(VaultError, match="corrompu"):
            v.load()

    def test_load_missing_file_noop(self, tmp_path: Path):
        path = tmp_path / "absent.enc"
        v = Vault(password=VALID_PWD, path=path)
        v.load()
        assert len(v) == 0

    def test_save_without_path_raises(self):
        v = Vault(password=VALID_PWD)
        v.store("[X]", "x")
        with pytest.raises(VaultError, match="Aucun chemin"):
            v.save()

    def test_unicode_values(self, tmp_path: Path):
        path = tmp_path / "vault.enc"
        v1 = Vault(password=VALID_PWD, path=path)
        v1.store("[PERSON_1]", "Stephanie")
        v1.store("[ADDR_1]", "126 rue de la Liberte")
        v1.save()

        v2 = Vault(password=VALID_PWD, path=path)
        v2.load()
        assert v2.get_original("[PERSON_1]") == "Stephanie"
        assert v2.get_original("[ADDR_1]") == "126 rue de la Liberte"


class TestVaultMappingExport:
    def test_export_mapping(self):
        v = Vault(password=VALID_PWD)
        v.store("[X_1]", "alpha")
        v.store("[X_2]", "beta")
        export = v.export_mapping()
        assert export["forward"]["alpha"] == "[X_1]"
        assert export["backward"]["[X_2]"] == "beta"
