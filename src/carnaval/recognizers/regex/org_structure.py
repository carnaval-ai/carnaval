# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Mentions structurelles d'organisation : services, departements, agences.

Vecteur d'attaque red-team V12 (faiblesse "Comptabilite Fournisseurs"
+ "Plant" + service centralise) : ces libelles sont la signature
d'une structure de grand industriel et participent au faisceau
d'identification du destinataire. Combines au plant code, ils
confirment le profil.

Strategie : masquer les libelles d'unite organisationnelle quand ils
sont en position d'EN-TETE (debut de ligne ou apres ":") - pas dans
le corps de phrase ou ils sont du vocabulaire metier normal.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span


# Mentions de services / departements / unites organisationnelles.
# Mode multiligne : matche en debut de ligne uniquement (^), pour
# eviter de masquer dans un texte legal ("la comptabilite est..."
# devient "[SERVICE_n] est...").
_ORG_STRUCTURE_PATTERN = re.compile(
    r"(?im)^\s*"
    r"(?P<value>"
    # FR : Service / Departement / Direction / Comptabilite F + variantes
    r"Comptabilit[ée]\s+[Ff]ournisseurs?"
    r"|Comptabilit[ée]\s+(?:clients|generale|analytique)"
    r"|Service\s+(?:comptabilit[ée]|client|achats|qualit[ée]|production|logistique|approvisionnement)"
    r"|D[ée]partement\s+(?:Achats|Ventes|Production|Qualit[ée]|Logistique|RH)"
    r"|Direction\s+(?:Achats|Industrielle|Financi[èe]re|Technique|Generale)"
    # EN
    r"|Accounts?\s+Payable"
    r"|Purchasing\s+Department"
    r"|Quality\s+(?:department|control|assurance)"
    # DE
    r"|Kreditorenbuchhaltung"
    r"|Eink(?:auf|aufsabteilung)"
    # ES
    r"|Contabilidad\s+(?:proveedores|clientes)"
    r"|Departamento\s+(?:compras|ventas|calidad)"
    r"|Cuentas\s+a\s+pagar"
    # IT
    r"|Contabilit[àa]\s+fornitori"
    r"|Ufficio\s+(?:acquisti|qualit[àa])"
    r"|Reparto\s+acquisti"
    r")\b"  # bord de mot apres (pas obligatoirement fin de ligne)
)


def recognize_org_structure(text: str, score: float = 0.78) -> list[Span]:
    """Detecte les libelles d'unite organisationnelle en debut de ligne.

    Audit P3 V12 : ces libelles ne sont pas des PII en eux-memes mais
    participent au faisceau d'identification d'un grand industriel
    (signature d'une structure org centralisee).

    Args:
        text: texte source.
        score: confiance (faible : couche optionnelle).

    Returns:
        Liste de Span de type ORG_STRUCTURE.
    """
    spans: list[Span] = []
    for m in _ORG_STRUCTURE_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="ORG_STRUCTURE",
                text=m.group("value"),
                score=score,
                recognizer="OrgStructureRegex",
            )
        )
    return spans
