# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de codes de site / usine / plant.

Detecte les designations narratives d'implantation industrielle qui
identifient le destinataire :

    "PLANT ANGP - AngP - fr"       <- plant code interne client
    "PLANT [ville] - AngP - FR"
    "Usine de Saint-Etienne"
    "Site de Drancy"
    "Etablissement de Lyon"
    "Werk Stuttgart"               <- DE
    "Plant Toyota City"            <- EN/JP
    "Stabilimento di Torino"       <- IT
    "Planta de Valladolid"         <- ES

Vecteur d'attaque red-team : un code "PLANT ANGP-FR" ou "Usine de
Saint-Barthelemy" identifie geographiquement le destinataire sans
besoin de regex d'adresse classique.

Strategie : capture par libelle ancre (PLANT/USINE/SITE/WERK...) suivi
d'un nom propre (code ou ville). Le span englobe libelle + nom pour que
le masquage soit complet.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelles de site / usine / etablissement, multilingues.
_PLANT_LABEL = (
    r"(?:"
    # FR
    r"Usine|Site|[ÉE]tablissement|Atelier|D[ée]p[ôo]t|Centre\s+(?:de\s+)?production"
    r"|Plate(?:-?\s*)?forme\s+(?:logistique|industrielle)"
    # EN / international
    r"|Plant|Factory|Manufacturing\s+(?:facility|site|plant)"
    r"|Production\s+(?:site|facility|plant)"
    # DE
    r"|Werk|Werkstandort|Standort|Fertigungsstätte|Fertigungsstaette"
    # ES
    r"|Planta|Fábrica|Fabrica|Centro\s+(?:de\s+)?producción|Centro\s+(?:de\s+)?produccion"
    # IT
    r"|Stabilimento|Fabbrica|Impianto"
    # PT
    r"|F[áa]brica|Unidade\s+(?:de\s+)?produ[çc][ãa]o"
    # PL
    r"|Zak[łl]ad(?:\s+produkcyjny)?|Fabryka"
    # CZ
    r"|Z[áa]vod|Tov[áa]rna"
    # TR
    r"|Fabrika|Tesis|[ÜU]retim\s+tesisi"
    r")"
)

# Designation du site : 1 a 5 segments commencant par majuscule OU code
# alphanumerique. Couvre uniformement :
#   - codes internes "ANGP-FR", "AngP-fr", "ANGP_FR/EU"
#   - noms de ville Unicode "Saint-Etienne", "Stuttgart-Untertürkheim"
#   - composes avec espace "Toyota City"
# Un seul alternant pour eviter le piege de l'ordre dans (A|B) ou A
# matche partiellement et empeche B de matcher plus long.
_PLANT_NAME = (
    r"[A-ZÀ-Ý][A-Za-zÀ-ÿ0-9'’]{1,30}"
    # Separateurs entre segments : espace, tab, tiret, slash, underscore
    # MAIS PAS `\n` (sinon le pattern absorbe la ligne suivante :
    # "PLANT ANGP-FR\n126 RUE DE STALINGRAD" matche jusqu'a "126 RUE",
    # laissant "DE STALINGRAD" orphelin et la rue partiellement masquee).
    r"(?:[ \t\-/_][A-Za-zÀ-ÿ0-9'’]{1,30}){0,4}"
)

# Liaison optionnelle entre libelle et nom : "de", "of", "von", "di",
# "do", etc. + ponctuation possible.
# IMPORTANT : on N'AUTORISE PAS `\n` dans la liaison (sinon le pattern
# enchaine "Site\nRemarques" et capture du texte de la ligne suivante,
# bug audit v5-bis). Utilise [ \t] au lieu de \s.
_PLANT_LINK = r"(?:[ \t]+(?:de[ \t]+|of[ \t]+|du[ \t]+|d['’]|von[ \t]+|di[ \t]+|do[ \t]+|en[ \t]+|in[ \t]+|à[ \t]+|w[ \t]+))?[ \t:\-]*"

# Case-insensitive UNIQUEMENT sur le libelle (PLANT/Plant/plant) et la
# liaison (de/of/...). Le NOM PROPRE doit commencer par une vraie
# majuscule pour eviter de matcher "Atelier de soudure" (mot commun).
# Le `(?i:...)` est un groupe scoped IGNORECASE.
_PLANT_PATTERN = re.compile(
    rf"(?<![A-Za-zÀ-ÿ])(?i:{_PLANT_LABEL}{_PLANT_LINK}){_PLANT_NAME}"
)


# Liaisons (de/du/of/von/...) tolerees apres le libelle. Ce sont des
# mots-outils valides ("Usine de X", "Werk von X") ; on les SAUTE pour
# trouver le vrai nom propre.
_PLANT_LINKERS = frozenset({
    "de", "du", "des", "le", "la", "les", "of", "the", "a", "an",
    "von", "der", "die", "das", "den", "vom",
    "di", "del", "della", "delle", "degli", "dei",
    "do", "da", "dos", "das",
    "en", "in", "à", "au", "aux", "w",
})

# Mots qui ne forment JAMAIS un nom propre de site (libelles techniques).
# Verifies SUR LE NOM PROPRE (post-liaison) - pas sur la liaison.
_NON_PLANT_NOISE = frozenset({
    "production", "manufacturing", "facility", "facilities",
    "list", "type", "code", "number", "date", "name", "title",
    "address", "contact", "phone", "email", "fax",
    "client", "fournisseur", "supplier", "customer",
    "destinataire", "expediteur", "recipient", "sender",
    "and", "or", "et", "section", "page",
})


def recognize_plant_code(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les designations de site/usine/plant + le nom qui suit.

    Le span couvre TOUT le bloc "PLANT XXX" pour que le masquage final
    soit propre - sinon "PLANT [SITE_n]" continue de signaler qu'il y
    a une usine, alors que le but est de neutraliser le marqueur.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Spans de type LOCATION.
    """
    spans: list[Span] = []
    for m in _PLANT_PATTERN.finditer(text):
        # Filtre noise : on extrait le vrai nom propre EN SAUTANT les
        # liaisons (de/of/von/...) et on verifie qu'il n'est pas un
        # libelle technique. "Usine de production" -> nom = "production"
        # = noise -> rejete. "Usine de Saint-Etienne" -> nom =
        # "Saint-Etienne" -> OK.
        tokens = m.group(0).split()
        # Skip le libelle (1er token) et toutes les liaisons consecutives.
        i = 1
        while i < len(tokens):
            tok_norm = tokens[i].lower().strip(".,:-/'’")
            if tok_norm in _PLANT_LINKERS:
                i += 1
                continue
            break
        if i >= len(tokens):
            # Seulement libelle + liaisons, pas de nom propre -> rejet.
            continue
        proper_name = tokens[i].lower().strip(".,:-/'’")
        if proper_name in _NON_PLANT_NOISE:
            continue
        spans.append(
            Span(
                start=m.start(), end=m.end(),
                entity_type="LOCATION",
                text=m.group(0),
                score=score,
                recognizer="PlantCodeRegex",
            )
        )
    return spans
