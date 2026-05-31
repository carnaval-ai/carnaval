"""Tests etage 6 : Output (multi-format)."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from carnaval.core.serializers import (
    to_conll,
    to_html,
    to_json,
    to_jsonl,
    to_txt,
    to_xml,
)
from carnaval.core.span import Span
from carnaval.core.vault import Vault
from carnaval.stages.documents import MaskedDocument
from carnaval.stages.s6_output import output


VALID_PWD = "test_password_long_enough_chars"


def _masked(stem: str = "doc") -> MaskedDocument:
    spans = (
        Span(start=0, end=5, entity_type="PERSON", text="Alice",
             score=0.95, recognizer="GLiNER",
             metadata={"placeholder": "[PERSON_1]"}),
        Span(start=14, end=20, entity_type="ORGANIZATION", text="Globex",
             score=1.0, recognizer="OrganizationsDenyList",
             metadata={"placeholder": "[ORG_1]"}),
    )
    return MaskedDocument(
        source_path=Path(f"{stem}.txt"),
        original_text="Alice chez le Globex demain",
        anonymized_text="[PERSON_1] chez le [ORG_1] demain",
        language="fr",
        spans=spans,
        by_category={"PERSON": 1, "ORGANIZATION": 1},
    )


class TestSerializers:
    def test_txt(self):
        out = to_txt(_masked())
        assert "[PERSON_1]" in out
        assert "Alice" not in out

    def test_json(self):
        out = to_json(_masked())
        parsed = json.loads(out)
        assert parsed["language"] == "fr"
        assert len(parsed["entities"]) == 2
        assert parsed["entities"][0]["placeholder"] == "[PERSON_1]"

    def test_jsonl(self):
        out = to_jsonl(_masked())
        lines = [l for l in out.split("\n") if l]
        assert len(lines) == 2
        for line in lines:
            entity = json.loads(line)
            assert "placeholder" in entity

    def test_xml(self):
        out = to_xml(_masked())
        root = ET.fromstring(out)
        assert root.tag == "carnavalResult"
        entities = root.find("entities")
        assert len(entities) == 2

    def test_conll(self):
        out = to_conll(_masked())
        # Verifie qu'il y a au moins une ligne avec B- ou I-
        assert "B-PERSON" in out or "I-PERSON" in out
        assert "B-ORGANIZATION" in out or "I-ORGANIZATION" in out

    def test_html(self):
        out = to_html(_masked())
        assert "<html" in out
        assert "PERSON" in out
        # le texte original doit apparaitre (visualisation)
        assert "Alice" in out


class TestOutputWriteAll:
    def test_writes_all_formats(self, tmp_path: Path):
        doc = _masked()
        vault = Vault(password=VALID_PWD)
        vault.store("[PERSON_1]", "Alice")
        vault.store("[ORG_1]", "Globex")
        paths = output(doc, vault, tmp_path)

        # Tous les fichiers doivent exister
        assert paths.txt_path.exists()
        assert paths.json_path.exists()
        assert paths.jsonl_path.exists()
        assert paths.xml_path.exists()
        assert paths.conll_path.exists()
        assert paths.html_path.exists()
        assert paths.vault_path.exists()
        assert paths.meta_path.exists()

    def test_meta_no_sensitive_data(self, tmp_path: Path):
        doc = _masked()
        vault = Vault(password=VALID_PWD)
        vault.store("[PERSON_1]", "Alice")
        paths = output(doc, vault, tmp_path)

        meta_content = paths.meta_path.read_text(encoding="utf-8")
        # La valeur originale ne doit JAMAIS apparaitre dans la metadata
        assert "Alice" not in meta_content
        assert "Globex" not in meta_content

    def test_vault_reloadable(self, tmp_path: Path):
        doc = _masked()
        v1 = Vault(password=VALID_PWD)
        v1.store("[PERSON_1]", "Alice")
        v1.store("[ORG_1]", "Globex")
        paths = output(doc, v1, tmp_path)

        # Recharger le vault depuis le fichier
        v2 = Vault(password=VALID_PWD, path=paths.vault_path)
        v2.load()
        assert v2.get_original("[PERSON_1]") == "Alice"
        assert v2.get_original("[ORG_1]") == "Globex"
