# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Etape post-detect : extension d'un nom de personne sur sa ligne.

Symetrique a `org_line_expansion.py` mais pour les PERSON.

Regle metier :

    "Si un nom de personne est identifie sur une ligne, les tokens
    capitalises ADJACENTS sur la meme ligne (avant ou apres) qui
    ressemblent a un prenom ou un nom de famille doivent etre
    masques egalement."

Cas typiques observes en production :

    ORIGINAL  : "Carine Piron"             ANONYM : "Carine [PERSON_4]"
    ORIGINAL  : "Madame DERENTINGER Melanie"   ANONYM : "[PERSON_1] Melanie"
    ORIGINAL  : "MANGEONJEAN CAMILLE"     ANONYM : "MANGEONJEAN [PERSON_2]"

Cause racine : GLiNER multilingue capture parfois un seul des deux
tokens du nom complet (prenom OU nom), laissant l'autre en clair.

Cette etape examine chaque ligne contenant un span PERSON et etend
le masquage aux 1-2 tokens capitalises IMMEDIATEMENT adjacents.

Protections contre les faux positifs :

    - filtre noise-words : "Telephone", "Email", "Fax", "Page",
      "Bonjour", etc. ne deviennent pas des PERSON ;
    - les libelles fiscaux/juridiques (SIREN, TVA, RCS) coupent
      l'extension ;
    - seuls les tokens IMMEDIATEMENT adjacents (separes par 1-3
      blancs) sont consideres : pas de saut a travers plusieurs
      mots intermediaires.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Type ancrage pour l'extension.
_PERSON_TYPES = frozenset({"PERSON"})

# Mots qui ne sont jamais un prenom / nom propre, meme capitalises.
# Comparaison sur version normalisee (lower + deaccent).
_NON_PERSON_NOISE: frozenset[str] = frozenset({
    # FR - libelles tabulaires / civilites / formules
    "monsieur", "madame", "mademoiselle", "mr", "mme", "mlle",
    "monsieur,", "madame,",
    "telephone", "tel", "fax", "email", "mail", "adresse", "ville",
    "code", "postal", "pays", "rue", "avenue", "boulevard", "place",
    "page", "pages", "ligne", "lignes", "section", "colonne",
    "reference", "numero", "date", "heure", "jour", "mois", "annee",
    "tarif", "prix", "quantite", "remise", "montant", "valeur",
    "total", "totaux", "somme", "sous-total", "net", "ht", "ttc", "tva",
    # Mentions legales / metadata - ne sont pas des noms propres
    "identification", "identifiant", "ident", "ident.", "n",
    "intracom", "intracommunautaire", "intracommunautaires",
    "tva", "vat", "siret", "siren", "rcs", "rib", "iban", "bic", "ape",
    "capital", "social", "actions", "naf",
    "fr", "de", "en", "es", "it", "pt", "uk", "be", "nl",  # codes pays
    "designation", "description", "article", "articles", "lot",
    "facturation", "livraison", "commande", "client", "fournisseur",
    "qte", "quantite", "unite", "delai", "delais",
    "service", "responsable", "delegue", "interlocuteur", "contact",
    "acheteur", "vendeur", "destinataire", "expediteur", "transporteur",
    "siret", "siren", "ape", "naf", "rcs", "kbis", "capital", "social",
    "actions", "simplifiee", "anonyme", "responsabilite", "limitee",
    "individuelle", "auto", "entrepreneur", "gerant", "president",
    "presidente", "directeur", "directrice",
    "votre", "notre", "vos", "nos", "ce", "cette", "ces", "le", "la",
    "les", "un", "une", "des", "de", "du",
    "bonjour", "bonsoir", "cordialement", "sincerement", "salutations",
    "veuillez", "merci", "remerciements",
    "conditions", "generales", "particulieres", "garantie", "vente",
    "ventes", "achat", "achats", "paiement", "reglement", "echeance",
    "validite", "incoterm", "incoterms", "consignation", "reservation",
    "compte", "comptable", "comptabilite",
    # EN
    "telephone", "phone", "fax", "email", "address", "city", "country",
    "page", "pages", "line", "section", "column",
    "reference", "number", "date", "time", "day", "month", "year",
    "price", "quantity", "discount", "amount", "value", "total", "net",
    "subtotal", "gross", "vat", "tax",
    "description", "item", "items", "article", "articles",
    "billing", "shipping", "delivery", "order", "customer", "supplier",
    "vendor", "buyer", "seller", "carrier", "subject", "recipient",
    "sender", "issuer", "shipped", "billed", "issued", "delivered",
    "payment", "due", "amount", "invoice", "shipment",
    "contact", "responsible", "manager", "buyer", "delivery",
    "purchase", "sales", "office", "department", "warehouse",
    # DE
    "telefon", "telefax", "anschrift", "stadt", "land",
    "konto", "kunde", "lieferant", "rechnung", "bestellung", "betrag",
    "menge", "preis", "artikel", "gesamt", "summe",
    "datum", "stand", "kennzeichen", "nummer",
    "geschaeftsfuehrer", "geschaftsfuhrer", "vorsitzender", "vorstand",
    "aufsichtsrats", "aufsichtsrat", "sitz", "gesellschaft",
    # Mots metier specifiques tableau AR
    "mode", "type", "categorie", "statut", "etat", "base",
    "documents", "document", "informations", "remarques", "notes",
    "from", "to", "via", "by", "on", "in", "at",
    "particularites", "particulieres",
    "delivery", "address", "billing",
    "qty", "unit", "uom", "pcs", "pc", "ea", "kg", "lb",
    # Mots de connexion / particules ne demarrant pas un nom
    "et", "and", "und", "or", "ou",
    # FR specific noise
    "nonobstant", "mode", "qte", "ref", "tel", "tél",
    "représentant", "representant", "assistant", "assistante",
    "commercial", "commerciale", "responsable", "comptable",
    "comptabilite", "comptabilité",
    "telephone", "téléphone", "fax", "mail", "email",
    "documents", "particulieres", "particulières",
    "spring", "automation",
})

# Pattern d'un token de type "nom propre" :
#   - commence par majuscule (Latin etendu OU CJK CN/JP : non vise ici)
#   - au moins 2 caracteres au total
#   - peut etre tout-en-majuscules (nom de famille frequent en CAPS)
#   - tolere apostrophes / tirets internes (Saint-Pierre, O'Brien)
_NAME_TOKEN = re.compile(
    r"\b(?:[A-ZÀ-Ý][A-Za-zÀ-ÿ\-'’]{1,30}|[A-ZÀ-Ý]{2,30})\b"
)

# Libelles fiscaux / juridiques qui coupent l'extension.
_LEGAL_BOUNDARY_RE = re.compile(
    r"(?i)\b(?:S\.?A\.?R\.?L\.?|S\.?A\.?S\.?(?:U)?|S\.?A\.?|SNC|SARL|SAS|EURL"
    r"|EIRL|GmbH|AG|Ltd|LLC|Inc|Corp|SpA|Srl|BV|NV|Lda"
    r"|au\s+capital|capital(?:\s+social)?|SIREN|SIRET|RCS"
    r"|incoterm|TVA|VAT|N°)\b"
)

# Translation accent -> ASCII pour la normalisation (meme table que
# org_line_expansion pour coherence).
_DEACCENT = str.maketrans(
    "àâäáãåèéêëìíîïòóôöõùúûüýÿçñ"
    "ąćęłńóśźż"
    "şğı"
    "ěščřžťďňů"
    "ÀÂÄÁÃÅÈÉÊËÌÍÎÏÒÓÔÖÕÙÚÛÜÝŸÇÑ"
    "ĄĆĘŁŃÓŚŹŻ"
    "ŞĞİ"
    "ĚŠČŘŽŤĎŇŮ",
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


def _is_name_like(token: str) -> bool:
    """True si le token a la forme d'un prenom / nom de famille
    et n'est pas dans la liste de bruit."""
    if not _NAME_TOKEN.fullmatch(token):
        return False
    if _norm(token) in _NON_PERSON_NOISE:
        return False
    if _LEGAL_BOUNDARY_RE.fullmatch(token):
        return False
    return True


def _extend_left(text: str, span_start: int, line_start: int) -> int:
    """Etend vers la gauche : remonte jusqu'a 2 tokens name-like consecutifs.

    Retourne la nouvelle position de debut.
    """
    new_start = span_start
    cursor = span_start
    extended = 0
    while extended < 2:
        # Recule sur les blancs immediatement a gauche.
        left = cursor - 1
        while left >= line_start and text[left] in " \t":
            left -= 1
        if left < line_start:
            break
        # Token candidat : trouve sa borne gauche.
        token_end = left + 1
        token_start = token_end
        while (
            token_start > line_start
            and (text[token_start - 1].isalpha()
                 or text[token_start - 1] in "-'’")
        ):
            token_start -= 1
        token = text[token_start:token_end]
        if not _is_name_like(token):
            break
        new_start = token_start
        cursor = token_start
        extended += 1
    return new_start


def _extend_right(text: str, span_end: int, line_end: int) -> int:
    """Etend vers la droite : avance jusqu'a 2 tokens name-like consecutifs.

    Retourne la nouvelle position de fin.
    """
    new_end = span_end
    cursor = span_end
    extended = 0
    while extended < 2:
        right = cursor
        while right < line_end and text[right] in " \t":
            right += 1
        if right >= line_end:
            break
        token_start = right
        token_end = token_start
        while (
            token_end < line_end
            and (text[token_end].isalpha()
                 or text[token_end] in "-'’")
        ):
            token_end += 1
        if token_end == token_start:
            break
        token = text[token_start:token_end]
        if not _is_name_like(token):
            break
        new_end = token_end
        cursor = token_end
        extended += 1
    return new_end


def expand_person_on_line(text: str, spans: list[Span]) -> list[Span]:
    """Etend la portee de masquage d'un span PERSON aux 1-2 tokens
    name-like immediatement adjacents sur la meme ligne.

    Args:
        text: texte source.
        spans: spans deja detectes (PERSON inclus).

    Returns:
        Nouvelle liste de spans avec un span PERSON etendu pour chaque
        cas detecte. Les spans originaux sont preserves ; les extensions
        sont AJOUTEES (et seront mergees / deduplicees par S4 resolve).
    """
    # Pre-traitement : un span PERSON ne traverse normalement pas un
    # saut de ligne (un nom de personne tient sur une ligne). Quand
    # GLiNER produit un span cross-line, c'est presque toujours une
    # fusion erronee ("Surname\nIntervention", "FirstName\nORG"). On
    # tronque ces spans a la fin de leur premiere ligne pour eviter
    # qu'ils englobent du contenu non-PII (parfois meme a client name
    # de la ligne suivante, ce qui creerait une fuite).
    out_spans: list[Span] = []
    for s in spans:
        if s.entity_type in _PERSON_TYPES:
            line_start, line_end = _line_span(text, s.start)
            if s.end > line_end:
                truncated_text = text[s.start:line_end].rstrip()
                truncated_end = s.start + len(truncated_text)
                if truncated_end > s.start:
                    out_spans.append(
                        Span(
                            start=s.start,
                            end=truncated_end,
                            entity_type=s.entity_type,
                            text=text[s.start:truncated_end],
                            score=s.score,
                            recognizer=s.recognizer,
                            metadata=s.metadata,
                        )
                    )
                # Si le span ne contient rien d'utile sur sa 1re ligne,
                # on le drop simplement.
                continue
        out_spans.append(s)

    person_spans = [s for s in out_spans if s.entity_type in _PERSON_TYPES]
    if not person_spans:
        return out_spans
    new_spans: list[Span] = []
    seen_ranges: set[tuple[int, int]] = set()
    for p in person_spans:
        line_start, line_end = _line_span(text, p.start)
        ext_start = _extend_left(text, p.start, line_start)
        ext_end = _extend_right(text, p.end, line_end)
        if ext_start != p.start or ext_end != p.end:
            if (ext_start, ext_end) not in seen_ranges:
                seen_ranges.add((ext_start, ext_end))
                new_spans.append(
                    Span(
                        start=ext_start,
                        end=ext_end,
                        entity_type="PERSON",
                        text=text[ext_start:ext_end],
                        score=max(0.6, p.score * 0.9),
                        recognizer="PersonLineExpansion",
                        metadata={"expanded_from": p.recognizer},
                    )
                )

        # Extension cross-line specifique aux signatures de lettre :
        # "Jean Luc\nKLEE", "Patrice\nAUBERT" - le nom de famille (souvent
        # en CAPS) est positionne sur sa propre ligne, seul. On regarde
        # la ligne IMMEDIATEMENT SUIVANTE : si elle contient UN SEUL
        # token name-like (>= 2 chars), on l'absorbe. Restrictif pour
        # eviter d'aspirer un en-tete de section ou une reference.
        adjacent = _try_extend_next_line(text, ext_end, line_end)
        if adjacent is not None:
            adj_start, adj_end = adjacent
            full_start = ext_start
            full_end = adj_end
            if (full_start, full_end) not in seen_ranges:
                seen_ranges.add((full_start, full_end))
                new_spans.append(
                    Span(
                        start=full_start, end=full_end,
                        entity_type="PERSON",
                        text=text[full_start:full_end],
                        score=max(0.55, p.score * 0.85),
                        recognizer="PersonLineExpansion",
                        metadata={
                            "expanded_from": p.recognizer,
                            "cross_line": True,
                        },
                    )
                )
    return out_spans + new_spans


def _try_extend_next_line(
    text: str, current_end: int, current_line_end: int
) -> tuple[int, int] | None:
    """Cherche un token name-like SEUL sur la ligne immediatement suivante.

    Pattern signature de lettre : prenom (ligne N) + nom (ligne N+1, seul).
    Retourne (start, end) du token absorbe, ou None si la ligne suivante
    contient autre chose qu'un unique nom de famille candidat.

    Conditions strictes (anti faux positifs) :
        - la ligne suivante existe ;
        - elle contient EXACTEMENT un token alphabetique de >= 2 chars ;
        - ce token est name-like (passe les filtres _is_name_like) ;
        - la ligne ne contient pas d'autres caracteres significatifs
          (pas de chiffres, pas de ponctuation autre que blancs).
    """
    n = len(text)
    if current_line_end >= n or text[current_line_end] != "\n":
        return None
    next_start = current_line_end + 1
    next_end = text.find("\n", next_start)
    if next_end == -1:
        next_end = n
    line_content = text[next_start:next_end].strip()
    if not line_content:
        return None
    # Un seul token autorise : pas d'espace interne sauf trim externe.
    if " " in line_content or "\t" in line_content:
        return None
    # Token doit etre purement alphabetique (lettres + tirets/apostrophes
    # internes), pas de chiffres ni ponctuation.
    if not all(c.isalpha() or c in "-'’" for c in line_content):
        return None
    if len(line_content) < 2:
        return None
    if not _is_name_like(line_content):
        return None
    # Trouver les bornes precises du token dans le texte original.
    tok_start = next_start
    while tok_start < next_end and text[tok_start] in " \t":
        tok_start += 1
    tok_end = tok_start + len(line_content)
    return (tok_start, tok_end)
