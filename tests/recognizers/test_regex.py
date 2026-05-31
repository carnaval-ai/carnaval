"""Tests des recognizers regex."""

from __future__ import annotations

import pytest

from carnaval.recognizers.regex.address_fr import (
    recognize_address_fr,
    recognize_postal_city_fr,
    recognize_zone_fr,
)
from carnaval.recognizers.regex.email import recognize_email
from carnaval.recognizers.regex.fiscal_fr import (
    recognize_all_fiscal_fr,
    recognize_siren,
    recognize_siret,
    recognize_vat_fr,
)
from carnaval.recognizers.regex.header_source import recognize_header_source
from carnaval.recognizers.regex.iban_bic import (
    recognize_bic,
    recognize_iban,
    validate_iban_checksum,
)
from carnaval.recognizers.regex.name_patterns import (
    recognize_civilite,
    recognize_name_comma,
)
from carnaval.recognizers.regex.phone_fr import recognize_phone_fr
from carnaval.recognizers.regex.url import recognize_url


# ============================================================================
# Email
# ============================================================================


class TestEmail:
    @pytest.mark.parametrize("text,expected_count", [
        ("Contact alice@example.com merci", 1),
        ("Plusieurs : a@b.fr, c@d.com, e@f.org", 3),
        ("Pas d'email ici", 0),
        ("Avec sous-domaine : user@mail.acme.co.uk", 1),
        ("Format complexe : a.b+tag-1@x.y.z.fr", 1),
    ])
    def test_count(self, text, expected_count):
        spans = recognize_email(text)
        assert len(spans) == expected_count
        for s in spans:
            assert s.entity_type == "EMAIL"
            assert "@" in s.text


# ============================================================================
# Telephone FR
# ============================================================================


class TestPhoneFr:
    @pytest.mark.parametrize("text,expected", [
        ("Tel : 02.41.34.85.15", True),
        ("Contact +33 2 41 33 75 75", True),
        ("Mobile 06.08.60.12.23", True),
        ("Fax 04.50.25.35.45", True),
        ("Tel 0241414242", True),
        ("Astreinte 09.70.15.30.01", True),
        ("Reference 12345", False),
        ("Article 84123100", False),
        ("Code postal 49124", False),
        # Ne doit pas matcher au milieu d'une ref produit
        ("Reference produit 0810822010647", False),
    ])
    def test_match(self, text, expected):
        spans = recognize_phone_fr(text)
        assert (len(spans) > 0) == expected


# ============================================================================
# Fiscal FR (SIRET, SIREN, VAT)
# ============================================================================


class TestFiscalFr:
    def test_siret(self):
        assert len(recognize_siret("SIRET 380.590.489.00015")) == 1
        assert len(recognize_siret("30895021100026 SIRET")) == 1
        assert len(recognize_siret("Numero court 12345")) == 0

    def test_siren(self):
        assert len(recognize_siren("SIREN 440 236 453")) == 1
        assert len(recognize_siren("RCS 308950211")) == 1
        # Ne doit pas couper un nombre plus long
        assert len(recognize_siren("4700004226")) == 0

    def test_vat_fr(self):
        assert len(recognize_vat_fr("TVA FR99123456789")) == 1
        assert len(recognize_vat_fr("FR 28 308 950 211")) == 1
        assert len(recognize_vat_fr("DE 123456789")) == 0
        # Case-sensitive : "fr66..." minuscule ne doit pas matcher
        assert len(recognize_vat_fr("fr99123456789")) == 0

    def test_aggregator(self):
        text = "SIRET 380.590.489.00015 - SIREN 440 236 453 - TVA FR99123456789"
        spans = recognize_all_fiscal_fr(text)
        types = sorted({s.entity_type for s in spans})
        assert "SIRET" in types
        assert "SIREN" in types
        assert "VAT" in types


# ============================================================================
# IBAN / BIC
# ============================================================================


class TestIbanBic:
    def test_iban_checksum_valid(self):
        assert validate_iban_checksum("FR763000600001234567890141")
        assert validate_iban_checksum("DE89370400440532013000")
        assert validate_iban_checksum("FR76 1762 9000 0100 1136 9280 060")

    def test_iban_checksum_invalid(self):
        assert not validate_iban_checksum("FR0000000000000000000000000")
        assert not validate_iban_checksum("XYZ_not_an_iban")
        assert not validate_iban_checksum("FR12")

    def test_iban_match(self):
        spans = recognize_iban("IBAN FR763000600001234567890141 BIC COBA")
        assert len(spans) == 1
        assert spans[0].entity_type == "IBAN"

    def test_iban_glued(self):
        # IBAN colle au mot precedent
        spans = recognize_iban("IBANFR763000600001234567890141 BIC")
        assert len(spans) == 1

    def test_iban_invalid_filtered(self):
        # Le pattern peut matcher mais le checksum doit filtrer
        spans = recognize_iban("XX1234567890123456 something")
        assert len(spans) == 0

    def test_bic_requires_context(self):
        # Avec contexte : doit matcher
        assert len(recognize_bic("BIC AAAAFR2XXXX")) == 1
        assert len(recognize_bic("SWIFT AAAAFR2XXXX")) == 1
        # Sans contexte BIC/SWIFT : pas de match
        assert len(recognize_bic("Le mot STALINGRAD est une ville")) == 0
        assert len(recognize_bic("PARC ACTIVITES ANGERS")) == 0


# ============================================================================
# URL
# ============================================================================


class TestUrl:
    @pytest.mark.parametrize("text,expected", [
        ("Site web www.acme.com", True),
        ("https://example.org/page", True),
        ("Voir globex.io pour catalog", True),
        ("Quantite 1200 unites", False),
        ("Reference KHZ-DA-032", False),
    ])
    def test_match(self, text, expected):
        assert (len(recognize_url(text)) > 0) == expected


# ============================================================================
# Adresses FR
# ============================================================================


class TestAddressFr:
    def test_postal_city(self):
        spans = recognize_postal_city_fr("Livraison 49124 ST BARTHELEMY D'ANJOU")
        assert len(spans) == 1
        assert "BARTHELEMY" in spans[0].text

    def test_postal_city_glued(self):
        # Texte parasite colle
        spans = recognize_postal_city_fr("49124STBARTHELEMYDANJOU")
        assert len(spans) >= 1

    def test_zone(self):
        spans = recognize_zone_fr("Adresse PARC ACTIVITE ANGERS/ST BARTHELEMY")
        assert len(spans) == 1

    def test_zone_no_match(self):
        # ZONE seul sans mots-cle ne doit pas matcher
        assert len(recognize_zone_fr("Le PARC est ferme")) == 0

    def test_aggregator(self):
        text = "PARC ACTIVITE LYON 69001 LYON"
        spans = recognize_address_fr(text)
        assert len(spans) >= 1


# ============================================================================
# Name patterns
# ============================================================================


class TestNamePatterns:
    def test_name_comma(self):
        spans = recognize_name_comma("Contact : BERTAUX, Francoise au telephone")
        assert len(spans) == 1
        assert spans[0].entity_type == "PERSON"

    def test_name_comma_glued(self):
        # Format colle parasite
        spans = recognize_name_comma("ygieneBERTAUX, Francoise tel")
        assert len(spans) == 1

    def test_civilite(self):
        spans = recognize_civilite("Bonjour M. AUBERT Patrice")
        assert len(spans) == 1

    def test_civilite_mme(self):
        spans = recognize_civilite("Mme DUPONT Marie nous contacte")
        assert len(spans) == 1


# ============================================================================
# Header source
# ============================================================================


class TestHeaderSource:
    def test_match(self):
        text = "# Fichier source: Acme_ack_2024.pdf\nContenu apres."
        spans = recognize_header_source(text)
        assert len(spans) == 1
        assert "Acme_ack_2024.pdf" in spans[0].text

    def test_no_match_without_header(self):
        assert len(recognize_header_source("Pas de header ici.")) == 0
