# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Etape post-detect : extension d'un nom d'entreprise sur sa ligne.

Regle metier (decision Patrice) :

    "Si un nom d'entreprise composé est identifié quelque part dans
    le document, il ne doit jamais apparaitre en clair ailleurs.
    Si un nom est trouvé près d'un acronyme identifié comme nom
    d'entreprise, il faut masquer les noms qui suivent sur la ligne."

Cas typique :

    | M.E.D - MATERIEL ELECTRIQUE DISTRIBUTION (BAS RHIN) |
            ^^^^^^                                                        l
            span ORG detecte (CompanyHeaderRegex)              extension a masquer
                                                                    sur la meme ligne

Cette etape examine chaque ligne contenant un span ORG / ORG_SINGLETON
deja detecte et masque les "groupes de mots commerciaux" adjacents
non encore couverts. Un groupe = >= 2 tokens en majuscules ou Title
case consecutifs (avec separateurs admis : espace, tiret, '&', 'et',
'de', 'la', etc.).

Mecanismes de protection contre les faux positifs :

    - filtre noise-words (memes mots metier que le filtre GLiNER) :
      "TOTAL HT", "NET A PAYER", "CONDITIONS DE LIVRAISON", etc.
      ne deviennent pas des ORG ;
    - exigence d'au moins 2 mots dans le groupe (un mot seul comme
      "BANQUE" reste tolere comme libelle) ;
    - seuls les groupes ADJACENTS au span ORG existant (meme ligne)
      sont consideres, pas tout le document.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Types de spans servant d'ancre pour l'extension. Une org confirmee
# attire les noms adjacents ; une PERSON ou un LOCATION non.
_ORG_LIKE_TYPES = frozenset({"ORGANIZATION", "ORG", "ORG_SINGLETON"})

# Mots qui ne forment JAMAIS un nom commercial, meme groupes : labels
# tabulaires, libelles juridiques, mentions standards. La verification
# est faite sur la version normalisee (lower + ascii deaccent).
_NON_COMPANY_NOISE: frozenset[str] = frozenset({
    # Labels de section / tableau (FR)
    "total", "totaux", "somme", "sous-total", "net", "ht", "ttc", "tva",
    "facturation", "livraison", "commande", "client", "fournisseur",
    "designation", "reference", "quantite", "remise", "montant",
    "conditions", "regement", "reglement", "echeance", "modalites",
    "informations", "legales", "mentions", "protection", "donnees",
    "personnelles", "service", "responsable", "delegue", "interlocuteur",
    "acheteur", "vendeur", "destinataire", "expediteur", "transporteur",
    "interne", "externe", "principal", "central", "general", "speciale",
    "tarification", "contractuelle", "forfait", "visite", "technicien",
    "represente", "gerant", "president", "presidente",
    "siret", "siren", "ape", "naf", "rcs", "kbis", "capital",
    "social", "actions", "simplifiee", "anonyme", "responsabilite",
    "limitee", "individuelle", "auto", "entrepreneur",
    "bordereau", "facture", "regle", "regles", "art", "article",
    "page", "pages", "ligne", "lignes", "alinea",
    "engagement", "engagements", "reciproques", "objet", "champ",
    "encours", "autorise", "compte",
    # Labels EN
    "subject", "recipient", "sender", "issuer", "shipped", "shipping",
    "billed", "billing", "issued", "delivered", "payment", "amount",
    "value", "total", "subtotal", "net", "gross", "invoice", "order",
    "customer", "supplier", "vendor", "buyer", "seller", "carrier",
    "office", "hours", "tracking", "incoterm", "reverse", "charge",
    "include", "discount", "annual", "monthly", "basic", "plan",
    "account", "manager", "direct", "ground", "express", "page",
    "long", "short", "mail", "gateway", "name", "title",
    # Labels DE
    "konto", "kunde", "lieferant", "rechnung", "bestellung", "betrag",
    "menge", "preis", "artikel", "gesamt", "summe",
    # Particules + connecteurs (ne demarrent pas un groupe)
    "de", "du", "des", "la", "le", "les", "el", "los", "las",
    "von", "van", "der", "den", "et", "and", "und", "or", "of",
})

# Particules autorisees a l'INTERIEUR d'un groupe (entre 2 mots).
_INTERNAL_PARTICLES: frozenset[str] = frozenset({
    "de", "du", "des", "la", "le", "les", "et", "and", "und",
    "&", "y", "of", "do", "da", "dos", "das",
})

# Mots-cles juridiques qui marquent le DEBUT de la zone "metadonnees"
# du fournisseur. L'extension s'arrete des qu'on rencontre l'un d'eux :
# le nom commercial est avant ; ce qui suit est le statut, le capital,
# l'adresse legale, etc.
_LEGAL_BOUNDARY_RE = re.compile(
    r"(?i)\b(?:S\.?A\.?R\.?L\.?|S\.?A\.?S\.?(?:U)?|S\.?A\.?|SNC|SARL|SAS|EURL|EIRL"
    r"|GmbH|AG|Ltd|LLC|Inc|Corp|SpA|Srl|BV|NV|Lda|Lda\.?"
    r"|au\s+capital|capital(?:\s+social)?|SIREN|SIRET|RCS"
    r"|incoterm|TVA|VAT|N°)\b"
)

# Translation accent -> ASCII pour la comparaison aux mots noise.
_DEACCENT = str.maketrans(
    "àâäáãåèéêëìíîïòóôöõùúûüýÿçñ"
    "ąćęłńóśźż"
    "şğı"                                   # turc minuscules
    "ěščřžťďňů"                             # tcheque/slovaque minuscules
    "ÀÂÄÁÃÅÈÉÊËÌÍÎÏÒÓÔÖÕÙÚÛÜÝŸÇÑ"
    "ĄĆĘŁŃÓŚŹŻ"
    "ŞĞİ"                                   # turc majuscules
    "ĚŠČŘŽŤĎŇŮ",                            # tcheque/slovaque majuscules
    "aaaaaaeeeeiiiiooooouuuuyycn"
    "acelnoszz"
    "sgi"
    "escrztdnu"
    "AAAAAAEEEEIIIIOOOOOUUUUYYCN"
    "ACELNOSZZ"
    "SGI"
    "ESCRZTDNU",
)


def _norm(value: str) -> str:
    return value.lower().translate(_DEACCENT)


def _line_span(text: str, pos: int) -> tuple[int, int]:
    """Retourne (start, end) de la ligne contenant la position `pos`."""
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return start, end


# Token "commercial" : un mot d'au moins 3 caracteres debutant par une
# lettre majuscule ou un acronyme (lettres + chiffres mais commence par
# majuscule). Tirets internes acceptes. Pas d'apostrophe en debut.
_COMMERCIAL_TOKEN = re.compile(
    r"\b(?:[A-Z][A-Za-zÀ-ÿ0-9\-’']{2,}|[A-Z]{2,}[0-9]{1,4}|[A-Z](?:\.[A-Z]){1,5}\.?)\b"
)


def _scan_company_groups(line_text: str) -> list[tuple[int, int]]:
    """Repere les plages d'un meme groupe de mots commerciaux dans la ligne.

    Un groupe = >= 2 tokens commerciaux consecutifs separes par
    espaces / tirets / particules internes (de, et, &, ...). Un mot du
    bruit (TOTAL, HT, FACTURATION, ...) ou un libelle juridique borne
    le groupe.
    """
    tokens: list[tuple[int, int, str]] = [
        (m.start(), m.end(), m.group(0))
        for m in _COMMERCIAL_TOKEN.finditer(line_text)
    ]
    if not tokens:
        return []
    groups: list[tuple[int, int]] = []
    i = 0
    n = len(tokens)
    while i < n:
        # Demarre un nouveau groupe en (i)
        tok_start, tok_end, tok_text = tokens[i]
        if _norm(tok_text) in _NON_COMPANY_NOISE:
            i += 1
            continue
        if _LEGAL_BOUNDARY_RE.match(tok_text):
            i += 1
            continue
        group_start = tok_start
        group_end = tok_end
        j = i
        while j + 1 < n:
            next_start, next_end, next_text = tokens[j + 1]
            # On verifie que les caracteres separateurs entre les tokens
            # sont uniquement des espaces, tirets, '&' ou particules
            # internes. Si on rencontre autre chose -> rupture.
            between = line_text[group_end:next_start]
            normbetw = between.strip()
            if normbetw and normbetw.lower() not in _INTERNAL_PARTICLES and normbetw not in {"-", "–", "&", ","}:
                break
            # Le token suivant ne doit etre ni du bruit ni un libelle.
            if _norm(next_text) in _NON_COMPANY_NOISE:
                break
            if _LEGAL_BOUNDARY_RE.match(next_text):
                break
            # On l'absorbe.
            group_end = next_end
            j += 1
        if j > i:
            # Groupe de >= 2 tokens confirme.
            groups.append((group_start, group_end))
        i = j + 1
    return groups


def _line_gaps(
    line_start: int,
    line_end: int,
    spans: list[Span],
) -> list[tuple[int, int]]:
    """Retourne les sous-intervalles de la ligne NON couverts par un span.

    Sans cela, le scan inclut le span source dans le groupe commercial
    et le rejette ensuite pour chevauchement - on perdrait l'extension.
    """
    covered = sorted(
        (max(s.start, line_start), min(s.end, line_end))
        for s in spans
        if not (s.end <= line_start or line_end <= s.start)
    )
    gaps: list[tuple[int, int]] = []
    cursor = line_start
    for cs, ce in covered:
        if cursor < cs:
            gaps.append((cursor, cs))
        cursor = max(cursor, ce)
    if cursor < line_end:
        gaps.append((cursor, line_end))
    return gaps


def expand_org_on_line(
    text: str, spans: list[Span]
) -> list[Span]:
    """Etend la portee de masquage : pour chaque ligne ayant un span ORG,
    on masque aussi les groupes de mots commerciaux adjacents non encore
    couverts.

    Implementation : pour chaque ligne portant un span ORG, on calcule
    les "trous" (portions non couvertes par un span existant), puis on
    scanne chaque trou independamment pour y reperer des groupes de
    mots commerciaux. Cette approche evite que le span source soit
    absorbe dans le groupe et que le groupe complet soit ensuite
    rejete pour chevauchement.
    """
    org_spans = [s for s in spans if s.entity_type in _ORG_LIKE_TYPES]
    if not org_spans:
        return spans
    new_spans: list[Span] = []
    seen_ranges: set[tuple[int, int]] = set()
    seen_org_lines: set[int] = set()
    for org in org_spans:
        line_start, line_end = _line_span(text, org.start)
        if line_start in seen_org_lines:
            continue
        seen_org_lines.add(line_start)
        for gap_start, gap_end in _line_gaps(line_start, line_end, spans):
            gap_text = text[gap_start:gap_end]
            for grp_rel_start, grp_rel_end in _scan_company_groups(gap_text):
                abs_start = gap_start + grp_rel_start
                abs_end = gap_start + grp_rel_end
                if (abs_start, abs_end) in seen_ranges:
                    continue
                seen_ranges.add((abs_start, abs_end))
                new_spans.append(
                    Span(
                        start=abs_start,
                        end=abs_end,
                        entity_type="ORGANIZATION",
                        text=text[abs_start:abs_end],
                        score=max(0.6, org.score * 0.85),
                        recognizer="OrgLineExpansion",
                        metadata={"expanded_from": org.recognizer},
                    )
                )
    return spans + new_spans
