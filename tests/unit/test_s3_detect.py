"""Tests etage 3 : Detect."""

from __future__ import annotations

from pathlib import Path

from carnaval.core.config_loader import Config
from carnaval.stages.documents import NormalizedDocument
from carnaval.stages.s3_detect import _extract_denylist, detect


def _norm(text: str, language: str = "fr") -> NormalizedDocument:
    return NormalizedDocument(
        source_path=Path("dummy.txt"), text=text, language=language,
    )


class TestExtractDenylist:
    def test_direct_list(self):
        cfg = Config(raw={"deny_lists": {"organizations": ["Acme", "Globex"]}})
        assert _extract_denylist(cfg, "organizations") == ["Acme", "Globex"]

    def test_nested_same_key(self):
        cfg = Config(raw={
            "deny_lists": {
                "organizations": {"organizations": ["Acme", "Globex"]}
            }
        })
        assert _extract_denylist(cfg, "organizations") == ["Acme", "Globex"]

    def test_first_list_in_dict(self):
        cfg = Config(raw={
            "deny_lists": {
                "organizations": {"items": ["Acme"], "version": 1}
            }
        })
        assert _extract_denylist(cfg, "organizations") == ["Acme"]

    def test_missing(self):
        cfg = Config(raw={})
        assert _extract_denylist(cfg, "anything") == []


class TestDetect:
    def test_email_only(self):
        cfg = Config()
        doc = _norm("Contact : alice@example.com")
        out = detect(doc, cfg, use_gliner=False)
        types = {s.entity_type for s in out.spans}
        assert "EMAIL" in types

    def test_phone_fr(self):
        cfg = Config()
        doc = _norm("Tel : 02.41.34.85.15")
        out = detect(doc, cfg, use_gliner=False)
        types = {s.entity_type for s in out.spans}
        assert "PHONE" in types

    def test_organization_from_config(self):
        cfg = Config(raw={"deny_lists": {"organizations": ["Globex Inc."]}})
        doc = _norm("Facture Globex Inc.")
        out = detect(doc, cfg, use_gliner=False)
        types = {s.entity_type for s in out.spans}
        assert "ORGANIZATION" in types

    def test_singleton_from_config(self):
        cfg = Config(raw={
            "deny_lists": {"organization_singleton": ["Acme Corp"]}
        })
        doc = _norm("Acme Corp signe.")
        out = detect(doc, cfg, use_gliner=False)
        types = {s.entity_type for s in out.spans}
        assert "ORG_SINGLETON" in types

    def test_fr_only_recognizers_skipped_for_en(self):
        cfg = Config()
        doc = _norm("Phone 02.41.34.85.15", language="en")
        out = detect(doc, cfg, use_gliner=False)
        # Le phone FR ne doit pas etre detecte pour une langue != fr
        types = {s.entity_type for s in out.spans}
        # Cette assertion peut etre nuancee : si on accepte les regex FR
        # pour toutes les langues, c'est conscient. Ici on a desactive pour 'en'.
        assert "PHONE" not in types
