"""Tests des recognizers a base de deny lists."""

from __future__ import annotations

import pytest

from carnaval.recognizers.denylist.organizations import (
    recognize_organizations,
    recognize_organizations_loose,
)
from carnaval.recognizers.denylist.people import recognize_people
from carnaval.recognizers.denylist.singleton import recognize_singleton


# ============================================================================
# Singleton (ex : entreprise mere unique a anonymiser)
# ============================================================================


class TestSingleton:
    VARIANTS = [
        "ACME CORP",
        "Acme Corporation",
        "Acme Corp.",
        "ACMECORP",
        "Acme",
    ]

    @pytest.mark.parametrize("text,expected", [
        ("ACME CORP a passe commande", True),
        ("Bonjour Acme Corporation", True),
        ("Texte sans acme dedans...", True),  # le mot 'acme' minuscule matche (case-insensitive)
        ("Quantite 1200", False),
        ("Reference produit XYZ", False),
        ("ACMECORP sans espaces", True),
    ])
    def test_match(self, text, expected):
        spans = recognize_singleton(text, self.VARIANTS)
        assert (len(spans) > 0) == expected

    def test_entity_type_default(self):
        spans = recognize_singleton("ACME CORP", self.VARIANTS)
        assert spans[0].entity_type == "ORG_SINGLETON"

    def test_entity_type_override(self):
        spans = recognize_singleton(
            "ACME CORP", self.VARIANTS, entity_type="ENTREPRISE_INTERNE"
        )
        assert spans[0].entity_type == "ENTREPRISE_INTERNE"

    def test_empty_variants(self):
        assert recognize_singleton("ACME CORP", []) == []

    def test_longest_match_first(self):
        # "Acme Corporation" doit etre matche entier, pas "Acme" en premier
        spans = recognize_singleton("Bonjour Acme Corporation aujourd'hui", self.VARIANTS)
        assert len(spans) == 1
        assert spans[0].text == "Acme Corporation"


# ============================================================================
# Organizations (multiples, indexees plus tard)
# ============================================================================


class TestOrganizations:
    ORGS = ["Globex Inc.", "Initech", "Soylent Corp", "Vandelay Industries"]

    def test_multiple(self):
        text = "Facture Globex Inc., devis Initech, contrat Soylent Corp"
        spans = recognize_organizations(text, self.ORGS)
        assert len(spans) == 3
        for s in spans:
            assert s.entity_type == "ORGANIZATION"

    def test_no_match(self):
        assert recognize_organizations("Pas d'organisation", self.ORGS) == []

    def test_case_insensitive(self):
        assert len(recognize_organizations("initech", self.ORGS)) == 1


# ============================================================================
# Organizations loose (textes parasites)
# ============================================================================


class TestOrganizationsLoose:
    ORGS = ["acme", "globex", "initech"]

    def test_match_glued(self):
        # Texte colle ("venteacmedisponible") - le strict raterait
        text = "venteacmedisponible chez nous"
        spans = recognize_organizations_loose(text, self.ORGS)
        assert len(spans) >= 1

    def test_filter_short(self):
        # Variantes trop courtes filtrees
        orgs = ["xy", "ab", "Initech"]
        spans = recognize_organizations_loose("xy ab Initech", orgs, min_len=4)
        assert len(spans) == 1
        assert spans[0].text == "Initech"


# ============================================================================
# People
# ============================================================================


class TestPeople:
    PEOPLE = ["John Doe", "Jane Smith", "Alice Wonder"]

    def test_match(self):
        spans = recognize_people("Bonjour John Doe et Jane Smith", self.PEOPLE)
        assert len(spans) == 2

    def test_entity_type(self):
        spans = recognize_people("John Doe", self.PEOPLE)
        assert spans[0].entity_type == "PERSON"

    def test_no_partial(self):
        # "John" seul ne doit pas matcher si le deny est "John Doe"
        spans = recognize_people("John est ici", self.PEOPLE)
        assert len(spans) == 0
