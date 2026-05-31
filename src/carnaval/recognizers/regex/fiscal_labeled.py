# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer d'identifiants fiscaux ancres sur leur libelle.

GLiNER ne detecte pas de facon fiable les numeros fiscaux hors de ses
langues d'entrainement : le NIP polonais, par exemple, passe au travers.
Or, dans un accuse de reception, un identifiant fiscal est toujours
precede d'un libelle explicite (NIP, VAT number, NIF, 纳税人识别号...).

Ce recognizer s'ancre sur ces libelles - standards publics, communs a
tous les pays - puis capture la valeur qui suit. L'ancrage sur le libelle
evite de masquer un nombre quelconque : seule une valeur annoncee comme
fiscale est retenue, et elle doit contenir au moins un chiffre.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelles fiscaux rencontres en tete d'un identifiant, toutes langues
# confondues. Les variantes longues ("VAT number") precedent les courtes
# ("VAT") dans l'alternance pour etre consommees en priorite.
_FISCAL_LABELS = (
    # TVA intracommunautaire / VAT
    r"Num[ée]ro\s+de\s+TVA",
    r"N[°o]\s*(?:de\s+)?TVA(?:\s*intra\w*\.?)?",
    r"VAT\s+(?:registration\s+)?(?:number|no\.?|reg\.?)",
    r"VAT",
    r"USt[-\s]?IdNr\.?",
    r"Partita\s+IVA",
    r"P\.?\s?IVA",
    # Numero EORI - operateur economique (douane UE)
    r"EORI",
    # Identifiants fiscaux nationaux
    r"NIP",                            # Pologne
    r"N\.?I\.?F\.?",                   # Espagne / Portugal
    r"C\.?I\.?F\.?",                   # Espagne
    r"N[úu]mero\s+de\s+contribuinte",  # Portugal
    r"Codice\s+fiscale",               # Italie
    r"Steuernummer",                   # Allemagne
    r"Vergi\s+kimlik\s+numaras[ıi]",   # Turquie
    r"Vergi\s+(?:numaras[ıi]|no\.?)",  # Turquie
    r"VKN",                            # Turquie (abrege)
    r"Tax\s+(?:identification\s+)?(?:number|id\.?)",
    r"纳税人识别号",                     # Chine
    r"统一社会信用代码",                  # Chine (code credit social unifie)
    r"税号",                            # Chine (abrege)
    # Bulgarie : ДДС № (TVA bulgare). La valeur sera "BG" + 9 ou 10
    # chiffres - couverte par le pattern _VALUE generique.
    r"ДДС\s*(?:№|номер|No\.?|N\.?)?",
)

# Separateurs admis entre le libelle et la valeur, sur la meme ligne :
# deux-points ASCII ou pleine largeur, diese, espaces, tabulations.
_SEP = r"[ \t:#：]*"

# Valeur fiscale : prefixe pays optionnel (GB, FR...), au moins un chiffre,
# puis chiffres et lettres. Un separateur interne (espace, tiret, point,
# slash) doit etre suivi d'un chiffre : la valeur ne peut donc pas deborder
# sur un mot voisin (dans "DE213 402 337 BW Bank", " BW Bank" n'est pas
# avale). Sensible a la casse ; pas de saut de ligne admis.
#
# Le quantificateur {7,22} impose une longueur minimale realiste : tout
# identifiant fiscal connu fait au moins 8 caracteres. Sans ce plancher,
# le libelle "VAT" (en-tete de colonne courant dans un tableau d'AR)
# capturait des fragments de montants : "VAT-20 20" pris pour un numero.
_VALUE = r"([A-Z]{0,3}[- ]?\d(?:[\dA-Z]|[ .\-/]\d){7,22})"

# Le libelle est insensible a la casse (groupe scope (?i:...)) ; la valeur
# reste sensible a la casse.
_FISCAL_PATTERN = re.compile(
    r"(?i:" + "|".join(_FISCAL_LABELS) + r")" + _SEP + _VALUE
)


def recognize_fiscal_labeled(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les identifiants fiscaux annonces par un libelle explicite.

    Args:
        text: texte source.
        score: confiance attribuee aux spans produits.

    Returns:
        Liste de Span de type VAT (eventuellement vide).
    """
    spans: list[Span] = []
    for m in _FISCAL_PATTERN.finditer(text):
        spans.append(
            Span(
                start=m.start(1),
                end=m.end(1),
                entity_type="VAT",
                text=m.group(1),
                score=score,
                recognizer="FiscalLabeledRegex",
            )
        )
    return spans
