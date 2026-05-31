"""Tests d'integration : pipeline complet S1 -> S6 -> S7."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from carnaval.core.vault import Vault
from carnaval.pipeline import run_anonymization
from carnaval.stages.s7_reinject import reinject_string


VALID_PWD = "test_password_long_enough_chars"


SAMPLE_TEXT = """# Fichier source: Globex_ack_2024.pdf
Bonjour Alice Doe,
Votre commande chez Globex Inc. a ete prise en compte.
Contact : alice.doe@globex.example
Tel : 02.41.34.85.15
TVA FR99123456789
IBAN FR763000600001234567890141 BIC AAAAFR2XXXX
Reference produit : KHZ-DA-032-0050-M (a conserver)
Montant : 1200.50 EUR
"""


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Cree un mini repo avec config + profile pour tester."""
    config = tmp_path / "config"
    config.mkdir()
    (config / "pipeline.yaml").write_text("language: fr\n", encoding="utf-8")
    (config / "deny_lists").mkdir()
    (config / "deny_lists" / "organizations.yaml").write_text(
        "organizations:\n  - Globex Inc.\n", encoding="utf-8"
    )

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    sample = inbox / "ack_sample.txt"
    sample.write_text(SAMPLE_TEXT, encoding="utf-8")

    outbox = tmp_path / "outbox"
    outbox.mkdir()
    for sub in ("txt", "json", "jsonl", "xml", "conll", "html", "vault", "meta"):
        (outbox / sub).mkdir()

    return tmp_path


class TestPipelineEndToEnd:
    def test_runs_without_gliner(self, fake_repo: Path):
        sample = fake_repo / "inbox" / "ack_sample.txt"
        masked, written, cfg = run_anonymization(
            input_path=sample,
            outbox_dir=fake_repo / "outbox",
            vault_password=VALID_PWD,
            use_gliner=False,
            repo_root=fake_repo,
        )
        assert masked.language == "fr"
        assert len(masked.spans) > 0
        # Les entites critiques doivent etre masquees
        assert "alice.doe@globex.example" not in masked.anonymized_text
        assert "02.41.34.85.15" not in masked.anonymized_text
        assert "FR99123456789" not in masked.anonymized_text
        assert "FR763000600001234567890141" not in masked.anonymized_text
        # Le champ metier reste preserve
        assert "KHZ-DA-032-0050-M" in masked.anonymized_text
        assert "1200" in masked.anonymized_text or "EUR" in masked.anonymized_text

    def test_all_outputs_produced(self, fake_repo: Path):
        sample = fake_repo / "inbox" / "ack_sample.txt"
        _, written, _ = run_anonymization(
            input_path=sample,
            outbox_dir=fake_repo / "outbox",
            vault_password=VALID_PWD,
            use_gliner=False,
            repo_root=fake_repo,
        )
        for path in (written.txt_path, written.json_path, written.jsonl_path,
                     written.xml_path, written.conll_path, written.html_path,
                     written.vault_path, written.meta_path):
            assert path.exists(), f"Manquant : {path}"
            assert path.stat().st_size > 0

    def test_organization_from_config_masked(self, fake_repo: Path):
        sample = fake_repo / "inbox" / "ack_sample.txt"
        masked, _, _ = run_anonymization(
            input_path=sample,
            outbox_dir=fake_repo / "outbox",
            vault_password=VALID_PWD,
            use_gliner=False,
            repo_root=fake_repo,
        )
        # Globex Inc. (deny list) doit etre masque
        assert "Globex Inc." not in masked.anonymized_text

    def test_roundtrip_via_reinjection(self, fake_repo: Path):
        sample = fake_repo / "inbox" / "ack_sample.txt"
        masked, written, _ = run_anonymization(
            input_path=sample,
            outbox_dir=fake_repo / "outbox",
            vault_password=VALID_PWD,
            use_gliner=False,
            repo_root=fake_repo,
        )

        # Charger le JSON produit et le passer dans reinject
        json_content = written.json_path.read_text(encoding="utf-8")
        json_obj = json.loads(json_content)
        anonymized_text = json_obj["anonymized_text"]

        # Recharger le vault et restituer le texte
        vault = Vault(password=VALID_PWD, path=written.vault_path)
        vault.load()
        restored = reinject_string(anonymized_text, vault)

        # Les valeurs originales doivent etre revenues
        assert "alice.doe@globex.example" in restored
        assert "02.41.34.85.15" in restored
        assert "FR99123456789" in restored
        assert "Globex Inc." in restored

    def test_meta_no_sensitive_leak(self, fake_repo: Path):
        sample = fake_repo / "inbox" / "ack_sample.txt"
        _, written, _ = run_anonymization(
            input_path=sample,
            outbox_dir=fake_repo / "outbox",
            vault_password=VALID_PWD,
            use_gliner=False,
            repo_root=fake_repo,
        )
        meta = written.meta_path.read_text(encoding="utf-8")
        # Aucune valeur sensible ne doit apparaitre dans le meta
        assert "alice.doe" not in meta
        assert "Globex Inc." not in meta
        assert "FR99123456789" not in meta
