# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers de noms de personnes par pattern.

Complement de GLiNER pour les formats courants :
- "NOM, Prenom"        (BERTAUX, Francoise)
- "M. NOM Prenom"      (M. DOE Jane)
- "MR NOM Prenom"      (MR OGER DAVID - civilites sans point)
- "Prenom NOM"         (Norbert GUERIN - prenom suivi de nom en majuscules)
"""

from __future__ import annotations

import re

from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans

# NOM en majuscules + virgule + Prenom. Pas de \b initial : les textes
# parasites collent parfois le NOM au mot precedent.
NAME_COMMA_PATTERN = re.compile(r"[A-Z]{3,20},\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b")

# Civilites (avec OU sans point). Accepte "M.", "M ", "Mme", "MME", "MR",
# "Monsieur", "Madame", "Mlle", "Mademoiselle", "Mr ", "Mrs ".
# Apres la civilite : 2 a 4 mots dont au moins une majuscule.
CIVILITE_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:M\.|Mme\.?|Mlle\.?|MR\.?|MME\.?|MLLE\.?|Mr\.?|Mrs\.?|Ms\.?|"
    r"Monsieur|Madame|Mademoiselle)[ \t]+"
    r"[A-Z][A-Za-z\-']+(?:[ \t]+[A-Z][A-Za-z\-']+){1,3}\b"
)

# Prenom capitalize (1ere majuscule, puis minuscules) + NOM en majuscules.
# Couvre "Norbert GUERIN", "Jane DOE", "Marie DUPONT".
# On exige le prenom au moins 3 lettres et le nom au moins 3 lettres en
# majuscules pour limiter les faux positifs avec des sigles techniques.
# R1/R3 v7 : separateur `[ \t]+` (PAS `\s` qui inclut `\n`). Bug observe
# KEYENCE : "A.S.\nPar" matche comme Prenom+Nom alors que c'est "S.A.S."
# (forme juridique) suivi de "Parc Activite" sur la ligne suivante.
PRENOM_NOM_PATTERN = re.compile(
    r"\b[A-Z][a-zéèêëàâäîïôöùûüç]{2,15}[ \t]+[A-Z]{3,20}\b"
)

# Cas particulier : texte parasite ou Prenom+Nom sont colles ("StephanieCurabet")
# OU les deux sont juste capitalize ("Kelly Dupuis", "Norbert Guerin").
# Format : Capitalized + (espace optionnel) + Capitalized
# Risque : matche aussi "Code Article", "Mode Expedition" -> score modere
# pour eviter de tuer les vrais champs metier.
# R1/R3 v7 : separateur `[ \t\-]*` (PAS `[\s\-]` qui inclut `\n`).
PRENOM_NOM_GLUED_PATTERN = re.compile(
    r"\b[A-Z][a-zéèêëàâäîïôöùûüç]{2,15}"
    r"[ \t\-]*"  # 0 ou plus separateurs, hors saut de ligne
    r"[A-Z][a-zéèêëàâäîïôöùûüç]{2,15}\b"
)


def recognize_name_comma(text: str, score: float = 0.8) -> list[Span]:
    return regex_to_spans(
        NAME_COMMA_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="NameCommaRegex",
        score=score,
    )


def recognize_civilite(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        CIVILITE_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="CiviliteRegex",
        score=score,
    )


def recognize_prenom_nom(text: str, score: float = 0.75) -> list[Span]:
    """Detecte 'Prenom NOM' (prenom capitalize suivi de nom en majuscules).

    Score modere car risque de faux positifs (ex: 'Bonjour MONSIEUR',
    'Notes COMMANDE'). Le filtrage final via priority_rules + score_threshold
    limite ces faux positifs.
    """
    return regex_to_spans(
        PRENOM_NOM_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="PrenomNomRegex",
        score=score,
    )


def recognize_prenom_nom_glued(text: str, score: float = 0.55) -> list[Span]:
    """Variante tolerante : 'Prenom Nom' colles ou les deux capitalize.

    NB : pattern PUR (sans contexte). Risque eleve de faux positifs sur les
    bigrammes capitalize courants ('Mode Expedition', 'Code Article').
    Pour eviter ces faux positifs, on utilise plutot
    `recognize_contextual_person` (avec mot-cle proche) en production.
    Garde comme fallback optionnel.
    """
    return regex_to_spans(
        PRENOM_NOM_GLUED_PATTERN,
        text,
        entity_type="PERSON",
        recognizer="PrenomNomGluedRegex",
        score=score,
    )


# Mots-cles qui precedent typiquement un nom de personne dans un AR
# (correspondant fournisseur, demandeur interne, contact, etc.).
PERSON_CONTEXT_KEYWORDS = (
    "correspondant",
    "contact",
    "suivi par",
    "affaire suivie",
    "demandeur",
    "acheteur",
    "vendeur",
    "rep:",
    "rep ",
    "a l'attention",
    "attention de",
    "responsable",
)

# Pattern Prenom + Nom CAPITALIZE (ex: 'Stephanie Curabet', 'Kelly Dupuis').
# Utilise UNIQUEMENT en post-context (apres un mot-cle PERSON_CONTEXT_KEYWORDS).
_PERSON_CAPITALIZE_BIGRAM = re.compile(
    r"\b[A-Z][a-zéèêëàâäîïôöùûüç]{2,15}\s+" r"[A-Z][a-zéèêëàâäîïôöùûüç]{2,15}\b"
)


def recognize_contextual_person(text: str, score: float = 0.75) -> list[Span]:
    """Detecte 'Prenom Nom' (capitalize/capitalize) APRES un mot-cle de contexte.

    Couvre 'Votre correspondant Stephanie Curabet', 'Affaire suivie par Marie
    Dupont', 'Contact Pierre Martin' etc. Evite les faux positifs sur les
    bigrammes capitalize metier ('Date de livraison', 'Mode Expedition') qui
    ne sont jamais precedes de ces mots-cles.

    Fenetre de contexte : 40 chars avant le bigramme.
    """
    spans: list[Span] = []
    window = 40
    for m in _PERSON_CAPITALIZE_BIGRAM.finditer(text):
        start = m.start()
        before = text[max(0, start - window) : start].lower()
        if any(kw in before for kw in PERSON_CONTEXT_KEYWORDS):
            spans.append(
                Span(
                    start=start,
                    end=m.end(),
                    entity_type="PERSON",
                    text=m.group(0),
                    score=score,
                    recognizer="ContextualPersonRegex",
                )
            )
    return spans


def recognize_name_patterns(text: str) -> list[Span]:
    """Aggregateur."""
    return (
        recognize_name_comma(text)
        + recognize_civilite(text)
        + recognize_prenom_nom(text)
        + recognize_contextual_person(text)
        # NB : recognize_prenom_nom_glued n'est PAS appele ici (trop de faux
        # positifs). Si besoin, l'appeler explicitement avec un score bas et
        # un score_threshold suffisamment haut.
    )
