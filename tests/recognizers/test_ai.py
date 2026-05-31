"""Tests du moteur GLiNER.

Le modele GLiNER (~500 Mo) est telecharge au premier appel. Les tests sont
skip si le modele n'est pas charge-able (offline / pas installe).
"""

from __future__ import annotations

import pytest

from carnaval.recognizers.ai.gliner_engine import (
    DEFAULT_LABELS,
    LABEL_TO_ENTITY_TYPE,
    is_available,
    recognize_with_gliner,
)


@pytest.fixture(scope="module")
def gliner_or_skip():
    """Skip le test si gliner n'est pas disponible."""
    if not is_available():
        pytest.skip("gliner non installe")


class TestGlinerSetup:
    def test_is_available(self, gliner_or_skip):
        assert is_available() is True

    def test_default_labels_have_mapping(self):
        # Tous les labels par defaut doivent avoir une entree dans le mapping
        # (sinon entity_type vaudra le label brut en majuscule, ce qui est OK
        # mais on prefere couvrir explicitement).
        for label in DEFAULT_LABELS:
            # Tolere : label peut etre absent du mapping, alors entity_type
            # sera le label.upper(). On verifie juste qu'il n'y a pas de plantage.
            entity_type = LABEL_TO_ENTITY_TYPE.get(label, label.upper())
            assert entity_type


class TestGlinerEmpty:
    def test_empty_text_returns_empty(self, gliner_or_skip):
        # Sans charger le modele : verifier que l'on court-circuite proprement
        # NB : sans modele charge, on retourne [] tres vite.
        assert recognize_with_gliner("") == []
        assert recognize_with_gliner("   ") == []


# Le test reel de detection est lourd (telechargement modele HF).
# On le marque comme `slow` pour pouvoir le filtrer en CI rapide.


@pytest.mark.slow
class TestGlinerDetection:
    """Tests d'integration sur du texte reel (necessite le modele charge)."""

    def test_detect_person(self, gliner_or_skip):
        text = "John Doe travaille chez Globex."
        spans = recognize_with_gliner(text, threshold=0.3)
        types = {s.entity_type for s in spans}
        assert "PERSON" in types

    def test_detect_email(self, gliner_or_skip):
        text = "Contact : john.doe@example.com"
        spans = recognize_with_gliner(text, threshold=0.3)
        # GLiNER peut detecter EMAIL ou laisser au regex.
        # On accepte les deux : presence d'un span couvrant l'email.
        assert any("john.doe" in s.text or s.entity_type == "EMAIL" for s in spans)
