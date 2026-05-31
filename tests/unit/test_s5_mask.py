"""Tests etage 5 : Mask."""

from __future__ import annotations

from pathlib import Path

from carnaval.core.span import Span
from carnaval.core.vault import Vault
from carnaval.stages.documents import ResolvedDocument
from carnaval.stages.s5_mask import mask


VALID_PWD = "test_password_long_enough_chars"


def _resolved(text: str, spans: list[Span]) -> ResolvedDocument:
    return ResolvedDocument(
        source_path=Path("d.txt"),
        text=text,
        language="fr",
        spans=tuple(sorted(spans, key=lambda s: s.start)),
    )


class TestMaskBasic:
    def test_single_person(self):
        text = "Hello Alice."
        spans = [Span(start=6, end=11, entity_type="PERSON", text="Alice")]
        vault = Vault(password=VALID_PWD)
        out = mask(_resolved(text, spans), vault)
        assert out.anonymized_text == "Hello [CONTACT_1]."
        assert out.original_text == text
        assert vault.get_original("[CONTACT_1]") == "Alice"

    def test_multiple_types(self):
        text = "Alice chez Globex."
        spans = [
            Span(start=0, end=5, entity_type="PERSON", text="Alice"),
            Span(start=11, end=17, entity_type="ORGANIZATION", text="Globex"),
        ]
        vault = Vault(password=VALID_PWD)
        out = mask(_resolved(text, spans), vault)
        assert "[CONTACT_1]" in out.anonymized_text
        assert "[FOURNISSEUR_1]" in out.anonymized_text
        assert "Alice" not in out.anonymized_text
        assert "Globex" not in out.anonymized_text

    def test_same_value_same_placeholder(self):
        text = "Alice et Alice et Alice"
        spans = [
            Span(start=0, end=5, entity_type="PERSON", text="Alice"),
            Span(start=9, end=14, entity_type="PERSON", text="Alice"),
            Span(start=18, end=23, entity_type="PERSON", text="Alice"),
        ]
        vault = Vault(password=VALID_PWD)
        out = mask(_resolved(text, spans), vault)
        # Toutes les occurrences doivent partager le meme placeholder
        assert out.anonymized_text.count("[CONTACT_1]") == 3
        assert len(vault) == 1

    def test_singleton_no_index(self):
        text = "Acme Corp ici. Acme Corp la."
        spans = [
            Span(start=0, end=9, entity_type="ORG_SINGLETON", text="Acme Corp"),
            Span(start=15, end=24, entity_type="ORG_SINGLETON", text="Acme Corp"),
        ]
        vault = Vault(password=VALID_PWD)
        out = mask(_resolved(text, spans), vault)
        assert "[CLIENT_NAME]" in out.anonymized_text
        assert "[CLIENT_NAME_1]" not in out.anonymized_text  # pas d'index pour singleton
        assert out.anonymized_text.count("[CLIENT_NAME]") == 2

    def test_by_category_counted(self):
        text = "Alice ecrit a Bob qui repond a alice@a.com"
        spans = [
            Span(start=0, end=5, entity_type="PERSON", text="Alice"),
            Span(start=14, end=17, entity_type="PERSON", text="Bob"),
            Span(start=31, end=42, entity_type="EMAIL", text="alice@a.com"),
        ]
        vault = Vault(password=VALID_PWD)
        out = mask(_resolved(text, spans), vault)
        assert out.by_category["PERSON"] == 2
        assert out.by_category["EMAIL"] == 1

    def test_substitution_right_to_left_preserves_offsets(self):
        text = "AB CD EF GH IJ"
        spans = [
            Span(start=0, end=2, entity_type="X", text="AB"),
            Span(start=3, end=5, entity_type="X", text="CD"),
            Span(start=6, end=8, entity_type="X", text="EF"),
        ]
        vault = Vault(password=VALID_PWD)
        out = mask(_resolved(text, spans), vault)
        # Les remplacements doivent etre coherents (offsets corrects)
        assert out.anonymized_text == "[X_1] [X_2] [X_3] GH IJ"
