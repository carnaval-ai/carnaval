"""Tests etage 7 : Reinject (JSON + XML)."""

from __future__ import annotations

import json
from xml.etree import ElementTree as ET

import pytest

from carnaval.core.vault import Vault
from carnaval.stages.s7_reinject import (
    reinject_json_data,
    reinject_json_string,
    reinject_string,
    reinject_xml_string,
)


VALID_PWD = "test_password_long_enough_chars"


@pytest.fixture
def vault_filled() -> Vault:
    v = Vault(password=VALID_PWD)
    v.store("[PERSON_1]", "Alice")
    v.store("[ORG]", "Acme Corp")
    v.store("[ORG_1]", "Globex Inc.")
    v.store("[EMAIL_1]", "alice@example.com")
    v.store("[VAT_1]", "FR99123456789")
    return v


# ============================================================================
# JSON
# ============================================================================


class TestReinjectJsonData:
    def test_string(self, vault_filled):
        assert reinject_json_data("Contact [PERSON_1]", vault_filled) == "Contact Alice"

    def test_dict(self, vault_filled):
        out = reinject_json_data({"contact": "[PERSON_1]"}, vault_filled)
        assert out == {"contact": "Alice"}

    def test_nested(self, vault_filled):
        data = {
            "header": {"company": "[ORG]", "vat": "[VAT_1]"},
            "lines": [
                {"supplier": "[ORG_1]"},
                {"contact": "[PERSON_1] via [EMAIL_1]"},
            ],
        }
        out = reinject_json_data(data, vault_filled)
        assert out["header"]["company"] == "Acme Corp"
        assert out["header"]["vat"] == "FR99123456789"
        assert out["lines"][0]["supplier"] == "Globex Inc."
        assert out["lines"][1]["contact"] == "Alice via alice@example.com"

    def test_unknown_placeholder_preserved(self, vault_filled):
        assert reinject_json_data("[UNKNOWN_99]", vault_filled) == "[UNKNOWN_99]"

    def test_scalars_passthrough(self, vault_filled):
        assert reinject_json_data(42, vault_filled) == 42
        assert reinject_json_data(None, vault_filled) is None
        assert reinject_json_data(True, vault_filled) is True


class TestReinjectJsonString:
    def test_full_roundtrip(self, vault_filled):
        json_input = '{"contact": "[PERSON_1]", "amount": 1200}'
        out = reinject_json_string(json_input, vault_filled)
        parsed = json.loads(out)
        assert parsed["contact"] == "Alice"
        assert parsed["amount"] == 1200


# ============================================================================
# XML
# ============================================================================


class TestReinjectXml:
    def test_text_in_element(self, vault_filled):
        xml = "<root><contact>[PERSON_1]</contact></root>"
        out = reinject_xml_string(xml, vault_filled)
        root = ET.fromstring(out)
        assert root.find("contact").text == "Alice"

    def test_attribute(self, vault_filled):
        xml = '<root supplier="[ORG_1]"/>'
        out = reinject_xml_string(xml, vault_filled)
        root = ET.fromstring(out)
        assert root.attrib["supplier"] == "Globex Inc."

    def test_nested(self, vault_filled):
        xml = (
            '<order vat="[VAT_1]">'
            '<contact>[PERSON_1]</contact>'
            '<supplier>[ORG_1]</supplier>'
            '<amount currency="EUR">1200</amount>'
            '</order>'
        )
        out = reinject_xml_string(xml, vault_filled)
        root = ET.fromstring(out)
        assert root.attrib["vat"] == "FR99123456789"
        assert root.find("contact").text == "Alice"
        assert root.find("supplier").text == "Globex Inc."
        assert root.find("amount").text == "1200"

    def test_unknown_placeholder_preserved(self, vault_filled):
        xml = "<root>[UNKNOWN_42]</root>"
        out = reinject_xml_string(xml, vault_filled)
        root = ET.fromstring(out)
        assert root.text == "[UNKNOWN_42]"


# ============================================================================
# Auto-detect
# ============================================================================


class TestAutoDetect:
    def test_json_detection(self, vault_filled):
        out = reinject_string('{"x": "[PERSON_1]"}', vault_filled)
        # Doit avoir parse/serialise JSON
        parsed = json.loads(out)
        assert parsed["x"] == "Alice"

    def test_xml_detection(self, vault_filled):
        out = reinject_string('<root>[PERSON_1]</root>', vault_filled)
        root = ET.fromstring(out)
        assert root.text == "Alice"

    def test_plain_text_fallback(self, vault_filled):
        out = reinject_string("Bonjour [PERSON_1]", vault_filled)
        assert out == "Bonjour Alice"
