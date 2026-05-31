# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Stage 3 - Detect: executes recognizers and collects Spans.

Responsibilities:
- Load active recognizers according to config
- Execute each recognizer on the text
- Collect Spans (no dedup - that's S4's role)

Input: NormalizedDocument + Config
Output: DetectedDocument
"""

from __future__ import annotations

import re
from typing import Callable

from carnaval.core.allow_list import apply_allow_list
from carnaval.core.config_loader import Config
from carnaval.core.propagation import propagate_entities
from carnaval.core.span import Span
from carnaval.core.table_body import drop_spans_in_table_body
from carnaval.recognizers.denylist.organizations import (
    recognize_organizations,
    recognize_organizations_loose,
)
from carnaval.recognizers.denylist.people import recognize_people
from carnaval.recognizers.denylist.places import recognize_places
from carnaval.recognizers.denylist.singleton import (
    recognize_singleton,
    recognize_singleton_loose,
)
from carnaval.recognizers.dictionary import (
    recognize_automotive_oem,
    recognize_cities,
    recognize_firstnames,
    recognize_initial_surname,
)
from carnaval.recognizers.regex.address import recognize_address
from carnaval.recognizers.regex.incoterm_location import (
    recognize_incoterm_location,
)
from carnaval.recognizers.regex.bank_by_context import recognize_bank_by_context
from carnaval.recognizers.regex.company_header import recognize_company_header
from carnaval.recognizers.regex.context_location import recognize_contextual_location
from carnaval.recognizers.regex.date_of_birth import recognize_date_of_birth
from carnaval.recognizers.regex.enumerated_names import recognize_enumerated_names
from carnaval.recognizers.regex.email import recognize_email
from carnaval.recognizers.regex.fiscal_fr import recognize_all_fiscal_fr
from carnaval.recognizers.regex.fiscal_labeled import recognize_fiscal_labeled
from carnaval.recognizers.regex.header_source import recognize_header_source
from carnaval.recognizers.regex.iban_bic import recognize_bic, recognize_iban
from carnaval.recognizers.regex.maiden_name import recognize_maiden_name
from carnaval.recognizers.regex.names import recognize_names
from carnaval.recognizers.regex.national_id import (
    recognize_bank_account_by_context,
    recognize_cn_hkid,
    recognize_cn_id,
    recognize_cn_passport,
    recognize_cn_uscc,
    recognize_cz_cssz,
    recognize_cz_dic,
    recognize_cz_ico,
    recognize_cz_op,
    recognize_cz_rodne_cislo,
    recognize_jp_driver_licence,
    recognize_jp_health_insurance,
    recognize_jp_hojin_bango,
    recognize_jp_mai_number,
    recognize_jp_passport,
    recognize_jp_touki_bangou,
    recognize_kr_business_registration,
    recognize_kr_rrn,
    recognize_es_ccc,
    recognize_es_cif,
    recognize_es_dni,
    recognize_es_nie,
    recognize_de_handelsregister,
    recognize_de_national_id,
    recognize_hmrc_ref,
    recognize_bg_egn,
    recognize_bg_eik,
    recognize_bg_health_insurance,
    recognize_bg_id_card,
    recognize_bg_lnch,
    recognize_it_codice_fiscale,
    recognize_it_codice_sdi,
    recognize_it_regulatory_number,
    recognize_it_tessera_sanitaria,
    recognize_national_id,
    recognize_pl_krs,
    recognize_pl_nip,
    recognize_pl_pesel,
    recognize_pl_regon,
    recognize_pt_cc,
    recognize_pt_nif,
    recognize_pt_niss,
    recognize_social_security_fr,
    recognize_tr_sgk,
    recognize_tr_sicil,
    recognize_tr_tckn,
    recognize_tr_vkn,
    recognize_uk_driving_licence,
    recognize_uk_national_insurance,
    recognize_uk_utr,
    recognize_urssaf,
)
from carnaval.recognizers.regex.address_fragment import recognize_address_fragment
from carnaval.recognizers.regex.affair_number import recognize_affair_number
from carnaval.recognizers.regex.client_code import recognize_client_code
from carnaval.recognizers.regex.commercial_cell import recognize_commercial_cell
from carnaval.recognizers.regex.compact_date import recognize_compact_date
from carnaval.recognizers.regex.internal_refs import recognize_internal_ref
from carnaval.recognizers.regex.legal_signals import (
    recognize_ape_code,
    recognize_capital,
    recognize_weee,
)
from carnaval.recognizers.regex.order_ref import recognize_order_ref_by_context
from carnaval.recognizers.regex.org_structure import recognize_org_structure
from carnaval.recognizers.regex.org_suffix import recognize_org_suffix
from carnaval.recognizers.regex.paren_content import recognize_paren_content
from carnaval.recognizers.regex.phone import (
    recognize_phone,
    recognize_phone_be,
    recognize_phone_anglo_international,
    recognize_phone_international,
)
from carnaval.recognizers.regex.plant_code import recognize_plant_code
from carnaval.recognizers.regex.postal_eu import recognize_postal_eu
from carnaval.recognizers.regex.table_columns import recognize_table_columns
from carnaval.recognizers.regex.tracking import recognize_tracking
from carnaval.recognizers.regex.rib_fr import (
    recognize_rib_fr,
    recognize_rib_fr_fields,
)
from carnaval.recognizers.regex.url import recognize_url
from carnaval.stages.documents import DetectedDocument, NormalizedDocument

# Recognizers regex universels (toutes langues)
_UNIVERSAL_REGEX_RECOGNIZERS: tuple[Callable[[str], list[Span]], ...] = (
    recognize_email,
    recognize_url,
    recognize_iban,
    recognize_bic,
    recognize_header_source,
    recognize_fiscal_labeled,
    recognize_rib_fr,
    recognize_rib_fr_fields,
    recognize_initial_surname,
    recognize_date_of_birth,
    recognize_national_id,
    recognize_social_security_fr,
    recognize_urssaf,
    recognize_uk_national_insurance,
    recognize_uk_driving_licence,
    recognize_uk_utr,
    recognize_hmrc_ref,
    recognize_es_dni,
    recognize_es_nie,
    recognize_es_cif,
    recognize_es_ccc,
    recognize_pt_nif,
    recognize_pt_cc,
    recognize_pt_niss,
    recognize_pl_nip,
    recognize_pl_regon,
    recognize_pl_krs,
    recognize_pl_pesel,
    recognize_de_handelsregister,
    recognize_de_national_id,
    recognize_tr_tckn,
    recognize_tr_vkn,
    recognize_tr_sgk,
    recognize_tr_sicil,
    recognize_cz_rodne_cislo,
    recognize_cz_ico,
    recognize_cz_dic,
    recognize_cz_op,
    recognize_cz_cssz,
    recognize_cn_id,
    recognize_cn_uscc,
    recognize_cn_hkid,
    recognize_cn_passport,
    recognize_bank_account_by_context,
    recognize_jp_mai_number,
    recognize_jp_hojin_bango,
    recognize_jp_driver_licence,
    recognize_jp_passport,
    recognize_jp_health_insurance,
    recognize_jp_touki_bangou,
    recognize_kr_business_registration,
    recognize_kr_rrn,
    recognize_it_codice_fiscale,
    recognize_it_codice_sdi,
    recognize_it_regulatory_number,
    recognize_it_tessera_sanitaria,
    recognize_bg_egn,
    recognize_bg_eik,
    recognize_bg_lnch,
    recognize_bg_id_card,
    recognize_bg_health_insurance,
    recognize_phone_be,
    recognize_phone_anglo_international,
    recognize_phone_international,
    recognize_maiden_name,
    recognize_bank_by_context,
    recognize_enumerated_names,
    recognize_company_header,
    # Anti-reidentification par recoupement (audit red-team P1) :
    # PO emise par client (V3), code plant (V2), tracking (V10),
    # constructeurs auto (V11).
    recognize_order_ref_by_context,
    recognize_plant_code,
    recognize_tracking,
    # Audit P2 : signaux legaux + references internes + adresses EU
    recognize_ape_code,
    recognize_capital,
    recognize_weee,
    recognize_internal_ref,
    recognize_postal_eu,
    # Audit P3 : structure organisationnelle
    recognize_org_structure,
    # Audit v2 P3 : VN2 / V11 / VN3 / VN5 / VN6
    recognize_commercial_cell,
    recognize_paren_content,
    recognize_client_code,
    # Directive Patrice (May 2026): dates are NOT to be masked - they
    # are vital for maintenance planning. The "acknowledge" profile
    # already declares them in `preserve: dates`. The compact_date recognizer is
    # therefore disabled for this use.
    # recognize_compact_date,
    recognize_address_fragment,
    # Audit v2 P3 : VN1 finition (tableau colonnaire)
    recognize_table_columns,
    # Audit v3 P4 : N° d'affaire / dossier client (directive Patrice)
    recognize_affair_number,
)
from carnaval.recognizers.post import expand_org_on_line, expand_person_on_line


# Proper-name types for which purely numeric text is necessarily
# a GLiNER error: a number is never a person, a place, or a company.
# PHONE / IBAN / etc. are numeric by nature and therefore excluded.
_NAME_ENTITY_TYPES = frozenset({"PERSON", "LOCATION", "ORGANIZATION"})
_NUMERIC_SPAN_PATTERN = re.compile(r"^\d[\d\s.,€%/-]*$")


def _drop_gliner_numeric_entities(spans: list[Span]) -> list[Span]:
    """Drops GLiNER proper-name spans whose text is purely numeric.

    GLiNER sometimes tags a number (amount, reference, code) as PERSON
    or LOCATION. Since a number is never a proper name, these are false
    positives: we remove them.
    """
    kept: list[Span] = []
    for s in spans:
        if s.entity_type in _NAME_ENTITY_TYPES and _NUMERIC_SPAN_PATTERN.match(
            s.text.strip()
        ):
            continue
        kept.append(s)
    return kept


# Principe R1 : un VAT doit AVOIR un prefixe pays OU un label fiscal
# explicite dans son contexte immediat. Sans ces gardes, GLiNER tague
# en VAT tout nombre 8-13 chiffres trouve a proximite de "TVA" en
# distance lointaine, ou meme sans (cas Code douanier 8 chiffres,
# Poids 5 chiffres, etc.).
_VAT_COUNTRY_PREFIX = re.compile(r"^\s*[A-Z]{2}[\s\d]")
_VAT_FISCAL_LABELS = re.compile(
    r"(?i)\b(?:TVA|VAT|UST\.?-?IdNr\.?|USt|BTW|IVA|MwSt|"
    r"Steuer-?Nr\.?|Steuernummer|Tax\s*ID|Identification\s+(?:fiscale|fiscal))\b"
)
# Distance maximale entre le label fiscal et la valeur VAT.
_VAT_LABEL_WINDOW = 40


def _drop_gliner_invalid_vat(spans: list[Span], text: str) -> list[Span]:
    """Drops GLiNER spans tagged VAT but WITHOUT explicit fiscal context.

    v7 IFM bug: GLiNER tags "85365019" (customs code) or "27,900"
    (weight) as VAT solely due to numeric format. Without country prefix
    [A-Z]{2} or nearby fiscal label, these are NOT VATs.

    Keep if:
      1. The span starts with 2 uppercase letters (ISO country prefix:
         FR, DE, ES, IT, GB, ...).
      2. OR an explicit fiscal label ("TVA", "VAT", "USt-IdNr", "BTW",
         "IVA", "MwSt", "Steuernummer", "Tax ID") is within
         `_VAT_LABEL_WINDOW` characters before the span.

    Otherwise: drop.
    """
    kept: list[Span] = []
    for s in spans:
        if s.entity_type != "VAT" or s.recognizer != "GLiNER":
            kept.append(s)
            continue
        if _VAT_COUNTRY_PREFIX.match(s.text):
            kept.append(s)
            continue
        ctx_start = max(0, s.start - _VAT_LABEL_WINDOW)
        ctx = text[ctx_start:s.start]
        if _VAT_FISCAL_LABELS.search(ctx):
            kept.append(s)
            continue
        # Silent drop (no logging to keep output clean on high-volume docs)
    return kept


# Delimiter characters to split a GLiNER span into meaningful tokens
# during the business_lexicon filter.
_SUBTOKEN_SEP = re.compile(r"[\s\-.,;:/()'’]+")
# Translation table to normalize accents -> ASCII (same rules as
# `core.allow_list._deaccent`), built once at import time.
_DEACCENT_TABLE = str.maketrans(
    "àâäáãåèéêëìíîïòóôöõùúûüýÿçñ"
    "ąćęłńóśźż"
    "şğı"                                   # turc minuscules
    "ěščřžťďňů",                            # tcheque/slovaque minuscules
    "aaaaaaeeeeiiiiooooouuuuyycn"
    "acelnoszz"
    "sgi"
    "escrztdnu",
)


def _norm_token(value: str) -> str:
    """Lowercase + deaccent for lexicon lookup comparison."""
    return value.lower().translate(_DEACCENT_TABLE)


# Noise vocabulary specific to the GLiNER filter. Common words
# (FR / EN / DE) that do NOT identify a person, place or organization,
# but which GLiNER regularly hallucinates as such at sentence start
# or in uppercase.
#
# This vocabulary is deliberately SEPARATE from `business_lexicon.yaml`:
#   - `business_lexicon` is used for allow_list (with overlap threshold) AND
#     table_body (header clusters). Adding "page", "long", "vers", "lot"
#     there could trigger false tabular zones on structured text.
#   - The GLiNER filter here works by strict 100% span coverage. A larger
#     list is harmless to other mechanisms.
#
# Stored normalized (lower + deaccent) for O(1) lookup without transformation.
# R3 v7: multilingual technical vocabulary - words that are NEVER a
# PERSON / ORG / LOCATION despite potential capitalization.
# Source: Eureka v7 audit on 5 PDFs (KEYENCE, IFM, BALLUFF, ...).
# Applied to ALL nominal recognizers (not just GLiNER).
_GLINER_NOISE_WORDS: frozenset[str] = frozenset(_norm_token(w) for w in {
    # === FR ===
    # Labels de document / mise en page
    "page", "pages", "ligne", "colonne", "section",
    # Unites / quantites
    "piece", "pieces", "pce", "pces", "pcs", "unite", "unites",
    "kg", "tonne", "metre", "litre", "carton", "lot",
    # Durees
    "jour", "jours", "mois", "annee", "annees", "semaine", "semaines",
    "heure", "heures", "minute", "seconde",
    # Mots metier FR ordinaires
    "regime", "aucune", "charge", "compte", "code", "vers",
    "banque", "social", "materiel", "virement", "viremement",
    "numero", "numéro", "reference", "référence", "designation", "désignation",
    "description", "quantite", "quantité", "remise", "montant", "total",
    "demandeur", "destinataire", "expediteur", "expéditeur",
    "transporteur", "signataire", "interlocuteur", "responsable",
    "conseillere", "conseillère", "conseiller",
    "vendeur", "acheteur", "fournisseur", "client", "service",
    "agence", "atelier", "site", "siege", "siège", "succursale",
    "filtre", "plaque", "verin", "vérin", "bride", "joint", "soufflet",
    "calibration", "vérification", "verification", "accreditation",
    "accréditation", "calibrage",
    "contact", "commercial", "commerciale", "logistique",
    "date", "echeance", "échéance", "livraison", "expedition", "expédition",
    "facture", "facturation", "commande",
    "rendu", "rendue", "destination", "lieu", "depart", "départ",
    "franco", "incoterm", "incoterms", "termes",
    # === EN ===
    "page", "long", "short", "mail", "gateway", "account", "plan",
    "basic", "annual", "monthly", "direct", "manager", "buyer",
    "seller", "vendor", "shipping", "loading", "unloading",
    "billing", "invoice", "payment", "delivery", "carrier",
    "ground", "express", "tracking", "incoterm", "reverse",
    "include", "amount", "total", "price", "quantity", "discount",
    "piece", "item", "unit", "qty", "each", "pack",
    "day", "days", "week", "weeks", "month", "months", "year", "years",
    "hour", "hours", "minute", "minutes",
    "purchase", "order", "reference", "description", "comment",
    "comments", "remarks", "destination", "location", "place",
    "company", "customer", "supplier", "contact", "person",
    "named", "warehouse", "destination",
    # === DE ===
    "konto", "kunde", "kunden", "lieferant", "rechnung", "bestellung",
    "betrag", "menge", "preis", "artikel", "stuck", "stück",
    "tag", "tage", "woche", "wochen", "monat", "monate", "jahr", "jahre",
    "ansprechpartner", "kontakt", "vertreter",
    "geliefert", "verzollt", "lieferung",
    # === ES ===
    "cliente", "proveedor", "factura", "pedido", "cantidad",
    "precio", "importe", "descuento", "iva",
    "dia", "días", "semana", "mes", "ano", "años",
    "pieza", "piezas", "unidad", "unidades", "destino", "lugar",
    "entrega", "facturacion", "facturación",
    # === IT ===
    "cliente", "fornitore", "fattura", "ordine", "quantità", "quantita",
    "prezzo", "importo", "sconto",
    "giorno", "giorni", "settimana", "mese", "anno", "anni",
    "pezzo", "pezzi", "unità", "unita", "consegna", "fatturazione",
    # === PT ===
    "cliente", "fornecedor", "fatura", "factura", "encomenda",
    "quantidade", "preço", "preco", "desconto",
    "dia", "dias", "semana", "mês", "mes", "ano", "anos",
    "peça", "peca", "unidade", "entrega",
    # === Polys courants ===
    "point", "time", "number", "name", "title",
    "value", "type", "class", "level", "model", "version",
    # === Formes juridiques / acronymes ambigus ===
    "sarl", "sas", "sasu", "snc", "scop", "scs", "selarl", "selas",
    "gmbh", "ag", "kg", "ohg", "sa", "spa", "srl", "bv", "nv", "ltd",
    "llc", "inc", "corp", "lda",
    # === Couleurs / dimensions / matieres ===
    "noir", "blanc", "rouge", "vert", "bleu", "gris", "jaune",
    "black", "white", "red", "green", "blue", "grey", "gray",
    "schwarz", "weiss", "rot", "grun", "blau", "grau",
    "negro", "blanco", "rojo", "verde", "azul", "gris", "amarillo",
})


def _drop_gliner_lexicon_entities(
    spans: list[Span], lex_simple: frozenset[str]
) -> list[Span]:
    """Excludes GLiNER proper-name spans that consist of ONLY one lexicon word.

    Common cases motivating this filter:

      - `Page`, `Long`, `gateway`, `mail` masked as `[ADDR]` or `[PERSON]`
      - `Filtre`, `Plaque`, `Bride`, `Verin` masked as `[ADDR]`
      - `Calibration`, `Verification`, `Accreditation`, `Hexagone`,
        `Atlantique` masked as `[PERSON]`
      - `Conseillere ADV`, `Account Manager`, `Regime TVA` masked as
        `[PERSON]` / `[ORG]`
      - `BANQUE`, `SOCIAL`, `MATERIEL` masked as `[ORG]` / `[BIC]`

    Rejection criterion: all significant tokens of the span (after
    splitting on whitespace/punctuation and lowercase+deaccent normalization)
    are present in the business_lexicon. If even ONE token is not in the
    lexicon (e.g. a genuine proper name), the span is kept.

    R3 (audit v7): the filter applies to ALL probabilistic nominal
    recognizers (PrenomNomRegex, PersonLineExpansion, EntityPropagation,
    GLiNER), not just GLiNER. Observed case KEYENCE: `Piece` (unit),
    `Days` (duration), `Demandeur` (label), `Désignation` (label) were
    tagged PERSON by PrenomNomRegex because they start with uppercase.

    CERTIFIED recognizers (explicit deny-lists, strict civilities):
    NOT subject to the filter - their match is ground truth.
    """
    if not lex_simple:
        return spans
    # R3: probabilistic recognizers to filter (as opposed to deny-
    # lists and certified patterns like Mr/Mme/Civility).
    _PROBABILISTIC_PERSON_RECOGNIZERS = {
        "GLiNER",
        "PrenomNomRegex",
        "PrenomNomGluedRegex",
        "PersonLineExpansion",
        "EntityPropagation",
        "ContextualPersonRegex",
        "InitialSurnameDict",
        "FirstnameDict_fr", "FirstnameDict_de", "FirstnameDict_en",
        "FirstnameDict_es", "FirstnameDict_it", "FirstnameDict_pt",
    }
    kept: list[Span] = []
    for s in spans:
        if (
            s.entity_type in _NAME_ENTITY_TYPES
            and s.recognizer in _PROBABILISTIC_PERSON_RECOGNIZERS
        ):
            tokens = [t for t in _SUBTOKEN_SEP.split(s.text.strip()) if t]
            if tokens and all(_norm_token(t) in lex_simple for t in tokens):
                # 100 % des tokens sont des mots du lexique metier : rejet.
                continue
        kept.append(s)
    return kept


# FR-specific regex recognizers (beyond the multilingual dispatchers):
# French tax (SIREN/SIRET/TVA FR), France-specific formats. Tax identifiers
# for other countries are covered by the universal `recognize_fiscal_labeled`
# recognizer (anchored on labels).
_FR_SPECIFIC_REGEX_RECOGNIZERS: tuple[Callable[[str], list[Span]], ...] = (
    recognize_all_fiscal_fr,
)


_SUPPORTED_LANGUAGES = frozenset({"fr", "en", "de", "es", "it", "pt", "nl", "bg"})

# Marqueurs linguistiques pour les documents hybrides.
# Deux niveaux :
#   STRONG = un seul hit suffit (mention non ambigue comme un nom de pays)
#   WEAK   = 2 hits distincts requis (suffixes orgs, mots commerciaux)
_LANGUAGE_MARKERS_STRONG: dict[str, tuple[str, ...]] = {
    "de": (
        r"\bDeutschland\b",
        r"\bÖsterreich\b",
        r"\bGeschäftsführer\b",
        r"\bSitz der Gesellschaft\b",
        r"\bRegistergericht\b",
        r"\bAufsichtsrat\w*\b",
    ),
    "en": (r"\bUnited Kingdom\b", r"\bUnited States\b"),
    "es": (r"\bEspaña\b",),
    "it": (r"\bItalia\b",),
    "pt": (r"\bPortugal\b", r"\bBrasil\b"),
    "fr": (r"\bFrance\b",),
    "bg": (
        r"\bБългария\b",
        r"\bРепублика\s+България\b",
        r"\bТърговски\s+регистър\b",
    ),
}

_LANGUAGE_MARKERS_WEAK: dict[str, tuple[str, ...]] = {
    "de": (
        r"\bGmbH\b",
        r"\bAG\b",
        r"\bKG\b",
        r"\bSE\b",
        r"\bVorstand\b",
        r"\bAmtsgericht\b",
        r"\bUST-IdNr\.\b",
        r"\bUSt-IdNr\.\b",
        r"\bSchweiz\b",
    ),
    "en": (
        r"\bLtd\.?\b",
        r"\bLLC\b",
        r"\bInc\.\b",
        r"\bCorp\.\b",
        r"\bPLC\b",
        r"\bSincerely\b",
        r"\bRegards\b",
    ),
    "es": (r"\bS\.A\.\b", r"\bSociedad Anonima\b", r"\bSL\b", r"\bAtentamente\b"),
    "it": (r"\bS\.r\.l\.\b", r"\bS\.p\.A\.\b", r"\bCordiali saluti\b"),
    "pt": (
        r"\bLda\.?\b",
        r"\bSociedade\b",
        r"\bAvenida\b",
        r"\bAv\.\s*\d",
        r"\bRua\b",
        r"\bCNPJ\b",
    ),
    "fr": (
        r"\bSARL\b",
        r"\bSAS\b",
        r"\bS\.A\.S\.\b",
        r"\bSASU\b",
        r"\bcordialement\b",
        r"\bSiège social\b",
    ),
    "bg": (
        # Formes juridiques bulgares : ООД/EOOD/АД/ЕАД/СД
        r"\bООД\b",
        r"\bЕООД\b",
        r"\bАД\b",
        r"\bЕАД\b",
        # Salutations / formules
        r"\bС\s+уважение\b",
        r"\bЗдравейте\b",
        # Termes commerciaux courants
        r"\bлв\.?\b",            # leva (devise)
        r"\bДДС\b",              # TVA
        r"\bфактура\b",
    ),
}

import re as _re

_STRONG_COMPILED: dict[str, list[_re.Pattern[str]]] = {
    lang: [_re.compile(p, _re.IGNORECASE) for p in patterns]
    for lang, patterns in _LANGUAGE_MARKERS_STRONG.items()
}
_WEAK_COMPILED: dict[str, list[_re.Pattern[str]]] = {
    lang: [_re.compile(p, _re.IGNORECASE) for p in patterns]
    for lang, patterns in _LANGUAGE_MARKERS_WEAK.items()
}


def _detect_languages_by_markers(text: str, weak_threshold: int = 2) -> set[str]:
    """Detecte les langues fortement presentes dans le texte par marqueurs.

    Une langue est activee si :
        - au moins un marqueur STRONG correspond (mention non ambigue), OU
        - au moins `weak_threshold` marqueurs WEAK distincts correspondent.
    """
    detected: set[str] = set()
    for lang in set(_LANGUAGE_MARKERS_STRONG) | set(_LANGUAGE_MARKERS_WEAK):
        strong_hit = any(p.search(text) for p in _STRONG_COMPILED.get(lang, []))
        if strong_hit:
            detected.add(lang)
            continue
        weak_hits = sum(1 for p in _WEAK_COMPILED.get(lang, []) if p.search(text))
        if weak_hits >= weak_threshold:
            detected.add(lang)
    return detected


def _extract_denylist(config: Config, name: str) -> list[str]:
    """Extrait une liste depuis config.deny_lists['<name>'].

    Conventions YAML supportees :
        deny_lists:
          organizations:
            organizations: [Acme, Globex]    # cle imbriquee
        ou bien :
        deny_lists:
          organizations: [Acme, Globex]       # liste directe
    """
    block = config.deny_lists.get(name, {})
    if isinstance(block, list):
        return list(block)
    if isinstance(block, dict):
        if name in block and isinstance(block[name], list):
            return list(block[name])
        for v in block.values():
            if isinstance(v, list):
                return list(v)
    return []


def _extract_denylist_multilang(
    config: Config,
    name: str,
    languages: set[str],
) -> list[str]:
    """Extrait une deny list multilingue.

    Layout YAML attendu :
        deny_lists/
          <name>/
            fr.yaml -> { <name>: [...] }
            de.yaml -> { <name>: [...] }
            ...

    Apres chargement :
        config.deny_lists[name] = {fr: {name: [...]}, de: {name: [...]}, ...}

    Args:
        config: Config charge.
        name: nom du bloc (ex: 'places').
        languages: ensemble des langues actives ({'fr'}, {'fr','de'}...).

    Returns:
        Liste concatenee de toutes les entrees pour les langues actives.
        Si le bloc est en ancien format (liste plate), fallback vers _extract_denylist.
    """
    block = config.deny_lists.get(name, {})

    # Compat ancien format : liste directe ou dict {name: [...]}
    if isinstance(block, list):
        return list(block)
    if not isinstance(block, dict):
        return []

    is_multilingual = any(k in _SUPPORTED_LANGUAGES for k in block.keys())
    if not is_multilingual:
        return _extract_denylist(config, name)

    result: list[str] = []
    for lang in languages:
        sub = block.get(lang, {})
        if not isinstance(sub, dict):
            continue
        # Cle imbriquee : sub = {name: [...]}
        if name in sub and isinstance(sub[name], list):
            result.extend(sub[name])
            continue
        # Fallback : prendre la premiere liste
        for v in sub.values():
            if isinstance(v, list):
                result.extend(v)
                break
    return result


def _resolve_active_languages(
    detected: str | None,
    primary: str | None,
    text: str = "",
) -> set[str]:
    """Calcule l'ensemble des langues actives.

    Combine plusieurs signaux :
        1. langue detectee par lingua (best-guess majoritaire)
        2. langue principale du pipeline (langue du client)
        3. marqueurs linguistiques forts dans le texte (GmbH -> de,
           SARL -> fr, Lda. -> pt...). Pour les documents hybrides.

    Fallback : {'fr'} si rien ne s'applique.
    """
    candidates: set[str] = set()
    for lang in (detected, primary):
        if lang and lang in _SUPPORTED_LANGUAGES:
            candidates.add(lang)
    if text:
        candidates |= _detect_languages_by_markers(text)
    return candidates or {"fr"}


def detect(
    doc: NormalizedDocument,
    config: Config,
    *,
    use_gliner: bool = True,
    gliner_threshold: float = 0.4,
    primary_language: str | None = None,
) -> DetectedDocument:
    """Lance tous les recognizers configures et collecte les Spans.

    Args:
        doc: document normalise.
        config: configuration carnaval (deny lists, patterns, policies).
        use_gliner: True pour activer le moteur GLiNER (lent au premier appel).
        gliner_threshold: seuil de confiance GLiNER.
        primary_language: langue principale du pipeline (langue du client /
            langue par defaut). Combinee avec doc.language pour determiner les
            recognizers et deny lists actifs. Cas d'usage : un AR allemand
            (doc.language='de') mentionne quand meme l'adresse FR du client
            (primary_language='fr') -> on active les deux jeux.

    Returns:
        DetectedDocument avec les Spans bruts (non deduplique).
    """
    text = doc.text
    spans: list[Span] = []

    # Resoudre les langues actives (doc.language + primary_language + marqueurs textuels)
    active_languages = _resolve_active_languages(
        detected=doc.language,
        primary=primary_language,
        text=text,
    )

    # 1. Regex universels (toutes langues)
    for reco in _UNIVERSAL_REGEX_RECOGNIZERS:
        spans.extend(reco(text))

    # 1bis. ORG par suffixe juridique (multilingue : GmbH, AG, Ltd, SARL, Lda.)
    spans.extend(recognize_org_suffix(text))

    # 2. Regex multilingues (dispatch interne selon active_languages)
    spans.extend(recognize_address(text, active_languages))
    spans.extend(recognize_phone(text, active_languages))
    spans.extend(recognize_names(text, active_languages))

    # 2bis. Regex UNIVERSELLES (ICC, ISO, standards mondiaux).
    # Independent of the detected language. Includes:
    #   - IncotermLocation : EXW/FCA/DAP/DDP/FOB/etc. + toponyme.
    spans.extend(recognize_incoterm_location(text))

    # 3. Language-specific regex (no dispatcher yet because
    #    no equivalent in other languages).
    if "fr" in active_languages:
        for reco in _FR_SPECIFIC_REGEX_RECOGNIZERS:
            spans.extend(reco(text))

    # 4. Deny lists multilingues par nature (organisations, personnes - noms propres)
    singletons = _extract_denylist(config, "organization_singleton")
    if singletons:
        spans.extend(
            recognize_singleton(
                text,
                singletons,
                entity_type="ORG_SINGLETON",
                recognizer_name="OrgSingleton",
            )
        )
        spans.extend(
            recognize_singleton_loose(
                text,
                singletons,
                entity_type="ORG_SINGLETON",
                recognizer_name="OrgSingletonLoose",
            )
        )

    # 4bis. ARCHITECTURE v4: we do NOT systematically tokenize
    #       supplier names (legal entities / acronyms / brands).
    #       The supplier name:
    #         - is NOT PII of the deploying client;
    #         - is useful BUSINESS information for the downstream extraction AI
    #           (AR/invoice reconciliation, brand identification);
    #         - appears in product descriptions (LYRECO, NORMAPUR, LOCTITE)
    #           where it MUST be preserved for catalog readability.
    #       GLiNER + `organizations` denylist cover cases of legal entity
    #       detected in signature/header context. No additional "closed list
    #       of 62 suppliers" layer that would over-mask product brands.

    organizations = _extract_denylist(config, "organizations")
    if organizations:
        spans.extend(recognize_organizations(text, organizations))
        spans.extend(recognize_organizations_loose(text, organizations))

    people = _extract_denylist(config, "people")
    if people:
        spans.extend(recognize_people(text, people))

    # 5. Per-language deny lists (toponyms: language-specific lists)
    places = _extract_denylist_multilang(config, "places", active_languages)
    if places:
        spans.extend(recognize_places(text, places))

    # 6. Recognizer contextuel multilingue : "Agence de X", "Office in Y", etc.
    spans.extend(recognize_contextual_location(text, active_languages))

    # 7. Bundled dictionaries (cities + firstnames). Active if the files
    #    assets/dictionaries/{cities,firstnames}/{lang}.txt exist.
    spans.extend(recognize_cities(text, active_languages))
    spans.extend(recognize_firstnames(text, active_languages))

    # 7bis. Automotive OEM + Tier-1 equipment manufacturers dictionary.
    #       Anti-re-identification by cross-reference: masks clear-text mentions
    #       of "Renault", "Bosch", "Denso", "OEM customer" etc.
    #       Universal (one dictionary for all languages).
    spans.extend(recognize_automotive_oem(text))

    # 8. GLiNER (slow)
    if use_gliner:
        try:
            from carnaval.recognizers.ai.gliner_engine import (
                recognize_with_gliner,
            )

            gliner_spans = recognize_with_gliner(text, threshold=gliner_threshold)
            gliner_spans = _drop_gliner_numeric_entities(gliner_spans)
            # R1: VAT GLiNER must have a country prefix or fiscal label.
            gliner_spans = _drop_gliner_invalid_vat(gliner_spans, text)
            # Business lexicon filter: rejects GLiNER spans that are only
            # business words (cf. root cause CR-B). Requires the lexicon
            # already loaded for table_body / allow_list - collected here
            # via the same primitive.
            from carnaval.core.allow_list import _collect_entries
            lex_words, _ = _collect_entries(config.allow_lists)
            # Union of business_lexicon (which already contains "tva",
            # "designation", etc.) and the GLiNER noise vocabulary.
            lex_simple = _GLINER_NOISE_WORDS | frozenset(
                _norm_token(w) for w in lex_words if w and " " not in w
            )
            gliner_spans = _drop_gliner_lexicon_entities(
                gliner_spans, lex_simple
            )
            spans.extend(gliner_spans)
        except ImportError:
            pass  # gliner not installed, silently ignore

    # 8bis. Propagation: a proper-name entity recognized once is
    #       marked on all its exact occurrences (e.g.: a signatory
    #       that GLiNER did not re-detect outside its context). Placed
    #       before the protection layer so that re-occurrences
    #       falling into a business zone are filtered like the others.
    spans = propagate_entities(text, spans)

    # 8ter. ORG span line extension: if a line contains an ORG span
    #       (acronym, deny-list, GLiNER), adjacent commercial word groups
    #       not yet covered on the same line are also masked (rule: "a full
    #       commercial name must always be masked entirely, never in clear
    #       on its own line").
    spans = expand_org_on_line(text, spans)

    # 8quater. PERSON span line extension: symmetric of ORG expansion.
    #          When GLiNER captures only one of two tokens of a full name
    #          ("Carine Piron" -> only "Piron" detected), extend the span to
    #          the 1-2 adjacent name-like tokens on the same line.
    spans = expand_person_on_line(text, spans)

    # 9. Protection layer: excludes spans covering a protected business
    #    zone (order numbers, product references...) declared under
    #    allow_lists/ in the profile. Prevents partial masking of an
    #    identifier.
    spans = apply_allow_list(text, spans, config.allow_lists)

    # 10. Table body: no masking on line items and totals (references,
    #     designations, quantities, amounts are not personal data). Replaces
    #     the old "currency lines" filter, which only covered GLiNER and
    #     lines with EUR.
    spans = drop_spans_in_table_body(text, spans, config.allow_lists)

    return DetectedDocument(
        source_path=doc.source_path,
        text=text,
        language=doc.language,
        spans=tuple(spans),
        metadata=doc.metadata,
    )
