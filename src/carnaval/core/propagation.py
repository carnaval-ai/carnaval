# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Propagation of proper-name entities to their re-occurrences.

A recognizer — GLiNER in particular — may detect an entity in one place
and miss it elsewhere: a name framed by a title is detected, but the same
name alone on the signature line is not. PII then leaks in clear text.

This step closes the gap: as soon as a string is recognized as a person
or organization name, its remaining exact occurrences in the document are
marked with the same type. Only applies to proper names (PERSON / ORG) —
an exact re-occurrence is, barring coincidence, the same entity. Title
prefixes (M., Sra., 先生...) are stripped from the reference string,
because a recognizer sometimes includes them inside the span.
"""

from __future__ import annotations

from carnaval.core.span import Span

# Propagated types: proper names AND PII with deterministic signature.
# An EXACT re-occurrence of a phone, IBAN, or tax ID is necessarily the
# same entity: masking it on page 2 when it was masked on page 1 prevents
# leaks due to GLiNER windowing or detection variability.
_PROPAGATABLE_TYPES = frozenset(
    {"PERSON", "ORGANIZATION", "ORG", "ORG_SINGLETON", "COMPANY",
     "LOCATION", "ADDRESS",
     "PHONE", "EMAIL", "IBAN", "BIC", "RIB",
     "SIREN", "SIRET", "VAT",
     # Anti-recoupement (audit v2) : codes specifiques au client/document
     # qui doivent etre propages page-a-page (occurrence en page 2 d'un
     # code client masque en page 1).
     "CLIENT_CODE", "ORDER_REF", "INTERNAL_REF", "TRACKING",
     "CAPITAL", "APE_CODE"}
)

# Titles / honorifics sometimes absorbed into a name span. Stripped from
# the reference string to find the bare name elsewhere in the document.
_TITLE_PREFIXES = (
    "monsieur", "madame", "mademoiselle", "mr.", "mrs.", "ms.", "m.",
    "mr", "mrs", "ms", "mme", "mlle", "sra.", "sr.", "sra", "sr",
    "sig.", "sig", "herr", "frau", "pan", "pani", "sayin", "dr.", "dr",
    "me",  # avocat / maitre
    # BG : г-н (gospodin = M.), г-жа (gospozha = Mme), г-ца
    # (gospozhitsa = Mlle), господин / госпожа / госпожица.
    "г-н", "г-жа", "г-ца",
    "господин", "госпожа", "госпожица",
)
_TITLE_SUFFIXES = (
    # CN : Monsieur / Madame / Mademoiselle / Madame
    "先生", "女士", "小姐", "夫人",
    # JP : sama (poli), san (neutre), kun (familier masc.), dono
    # (officiel), chan (familier diminutif), shi (formel ecrit).
    "様", "さん", "君", "殿", "ちゃん", "氏",
    "サン",  # katakana "san" (utilise pour les etrangers)
)

# Stopwords discarded when decomposing a multi-token name into
# propagatable sub-tokens. Without this filter, "de la Chanterie" would
# propagate "de" and "la" across the whole document. Minimal multilingual set.
#
# Also includes ambiguous BUSINESS TERMS: field labels (Point, Date, Code...)
# that often appear inside a hallucinated PERSON span from GLiNER
# (e.g. "Shipping Point", "Bank Code"). When propagated everywhere they
# would mask ordinary fragments. These are specifically labels from tables
# or headers that we NEVER want to propagate as person names.
_TOKEN_STOPWORDS = frozenset({
    # Particules nobiliaires / connecteurs (multilingue)
    "de", "du", "des", "la", "le", "les", "el", "los", "las",
    "von", "van", "der", "den", "ter", "ten", "zur", "zum",
    "di", "da", "do", "dos", "das",
    "y", "et", "and", "und", "of", "the",
    "ne", "nee", "née", "born",
    # Mots metier (libelles de champ / en-tete tabulaire) en anglais.
    # Tous LOWERCASE car le filtre normalise via .lower().
    "point", "place", "date", "time", "hour", "number", "code", "item",
    "service", "type", "class", "level", "name", "title",
    "total", "amount", "price", "quantity", "value", "unit",
    "shipping", "unloading", "loading", "receiving", "sending",
    "delivery", "pickup", "transport", "freight",
    "bank", "branch", "agency", "office",
    "party", "parties", "vendor", "buyer", "seller", "customer", "client",
    "supplier", "manufacturer",
    "order", "purchase", "invoice", "contract", "agreement",
    "page", "line", "column", "row",
    # Equivalents francais / allemands courants.
    "service", "client", "fournisseur", "acheteur", "vendeur",
    "partie", "parties", "commande", "facture", "contrat",
    "numero", "numéro", "reference", "référence", "designation",
    "désignation", "quantite", "quantité", "unite", "unité",
    "montant", "remise", "transporteur", "destinataire", "expediteur",
    "signataire", "interlocuteur", "responsable",
    "kunde", "lieferant", "kaufer", "verkaufer", "rechnung", "bestellung",
})

# Minimum length of a sub-token for it to be propagated on its own.
# Below this, collision risk with ordinary words is too high.
_MIN_TOKEN_LEN = 4

# ASCII unaccent table used for acronym calculation on organization names:
# an acronym like "J.E.L" does not contain the accent on the E of
# "Elastomeres" — the initial must therefore be de-accented before matching.
_DEACCENT_TABLE = str.maketrans(
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

# Legal suffixes removed when computing an organization name acronym.
# "Joints Elastomeres Lorraine SAS" -> acronym computed on (Joints,
# Elastomeres, Lorraine), not on (Joints, Elastomeres, Lorraine, SAS).
_LEGAL_SUFFIX_TOKENS: frozenset[str] = frozenset({
    "SA", "SAS", "SASU", "SARL", "SARLU", "SNC", "SCS", "SCA", "SCOP",
    "SCI", "SELARL", "SELAS", "SCP", "EURL", "EIRL", "EI",
    "GMBH", "AG", "KG", "OHG", "GBR", "EG", "EV", "MBH",
    "LTD", "LLC", "LLP", "PLC", "INC", "CORP", "CO",
    "SPA", "SRL", "SAPA", "SNS", "SAS",
    "BV", "NV", "VOF",
    "AB", "OY", "AS",
    "SP", "SPRL", "BVBA", "SPRLU", "SCRL", "SCRI",
    "LDA", "SA", "S.A", "S.A.S", "S.A.R.L", "S.A.S.U",
    "AKTIENGESELLSCHAFT", "GESELLSCHAFT",
})


def _strip_titles(value: str) -> str:
    """Strip a title / honorific from the head or tail of the string."""
    changed = True
    while changed:
        changed = False
        low = value.lower()
        for pref in _TITLE_PREFIXES:
            if low.startswith(pref + " "):
                value = value[len(pref):].lstrip()
                changed = True
                break
        for suf in _TITLE_SUFFIXES:
            if value.endswith(suf):
                value = value[: -len(suf)].rstrip()
                changed = True
                break
    return value


def _word_bounded(text: str, start: int, end: int) -> bool:
    """True if the occurrence is not adjacent to an alphanumeric character.

    Prevents propagating a name onto a fragment of a longer word.
    """
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    return not (before.isalnum() or after.isalnum())


def _split_person_subtokens(value: str) -> list[str]:
    """Decompose a multi-token person name into propagatable sub-tokens.

    A PERSON span detected as `Solene Vandermeer` must also mask a later
    occurrence of `Vandermeer` alone (signature or apostrophe case:
    "Madame Vandermeer,"). Same for `Belkhadra` in "nee Belkhadra".

    Selection criteria:
      - length >= `_MIN_TOKEN_LEN`
      - not in `_TOKEN_STOPWORDS`
      - first letter uppercase (disambiguates proper names from
        intervening common words)

    We split on whitespace AND hyphens so that a compound name like
    "Martineau-Chassaing" also propagates "Martineau" and "Chassaing".
    """
    sub: list[str] = []
    # Split on whitespace, hyphens, dots, parentheses, commas:
    # any common punctuation that delimits juxtaposed name parts.
    raw: list[str] = []
    for chunk in value.replace("’", "'").split():
        for sep in (".", "-", "(", ")", ",", ";", ":", "/"):
            chunk = chunk.replace(sep, " ")
        for part in chunk.split():
            raw.append(part)
    for tok in raw:
        if len(tok) < _MIN_TOKEN_LEN:
            continue
        if tok.lower() in _TOKEN_STOPWORDS:
            continue
        if not tok[0].isupper():
            continue
        sub.append(tok)
    return sub


def propagate_entities(text: str, spans: list[Span]) -> list[Span]:
    """Add a Span for every exact re-occurrence of a detected proper name.

    Args:
        text: source text.
        spans: detected spans (raw, before resolution).

    Returns:
        The original spans, augmented with the propagated occurrences.
    """
    if not spans:
        return spans

    occupied: list[tuple[int, int]] = [(s.start, s.end) for s in spans]

    # Reference string (bare name) -> best-scoring span that carries it.
    references: dict[str, Span] = {}
    for s in spans:
        if s.entity_type not in _PROPAGATABLE_TYPES:
            continue
        value = _strip_titles(s.text.strip())
        if len(value) < 2:
            continue
        current = references.get(value)
        if current is None or s.score > current.score:
            references[value] = s

    added: list[Span] = []

    # Normalized text (lowercase + ASCII) to match case/accent variants.
    # Same positions as the original text (translate maps 1 char -> 1 char;
    # .lower() does the same for Latin characters).
    #
    # IMPORTANT: translate BEFORE lower (not the other way around). The
    # Turkish `İ` (U+0130 LATIN CAPITAL LETTER I WITH DOT ABOVE) has a
    # `.lower()` that produces TWO codepoints (`i` + combining dot U+0307),
    # which would shift lowercase positions relative to the original text.
    # By doing translate FIRST (`İ → I` is in the table), we guarantee
    # length preservation.
    text_norm_lower = text.translate(_DEACCENT_TABLE).lower()

    def _propagate_string(value: str, ref: Span, *, tolerant: bool = False) -> None:
        """Find all uncovered occurrences of `value`.

        Args:
            value: string to search for.
            ref: reference span (will be copied onto the propagated occurrences).
            tolerant: if True, matching ignores case AND accents.
                Required so that an uppercase source span without accents
                (ALL CAPS PDF extraction) can propagate onto lowercase
                accented occurrences elsewhere in the document.
        """
        if len(value) < 2:
            return
        if tolerant:
            # Translate AVANT lower (cf. note sur `İ` ci-dessus).
            needle = value.translate(_DEACCENT_TABLE).lower()
            haystack = text_norm_lower
        else:
            needle = value
            haystack = text
        idx = haystack.find(needle)
        while idx != -1:
            end = idx + len(needle)
            covered = any(not (end <= z0 or z1 <= idx) for z0, z1 in occupied)
            if not covered and _word_bounded(text, idx, end):
                added.append(
                    Span(
                        start=idx,
                        end=end,
                        entity_type=ref.entity_type,
                        text=text[idx:end],  # texte ORIGINAL, pas la
                                             # version normalisee
                        score=ref.score,
                        recognizer="EntityPropagation",
                        metadata={"propagated_from": ref.recognizer},
                    )
                )
                occupied.append((idx, end))
            idx = haystack.find(needle, end)

    # 1) Propagation of EXACT occurrences (full string).
    for value, ref in references.items():
        _propagate_string(value, ref)

    # 2) Propagation of SUB-TOKENS from multi-token PERSON spans.
    #    Without this, "Madame Vandermeer," stays in clear when "Solene
    #    Vandermeer" was detected elsewhere as PERSON.
    person_subtokens: dict[str, Span] = {}
    person_initial_forms: dict[str, Span] = {}
    for value, ref in references.items():
        if ref.entity_type != "PERSON":
            continue
        sub = _split_person_subtokens(value)
        for tok in sub:
            current = person_subtokens.get(tok)
            if current is None or ref.score > current.score:
                person_subtokens[tok] = ref
        # Abbreviated form "initials + surname": for "Jean-Pascal Tremeau",
        # we also look for "JP. Tremeau", "J.P. Tremeau", "J. Tremeau"
        # (common stamp signature pattern).
        # Requires at least one given name (>= 1 token) and a propagatable
        # surname (>= 4 chars, starting with uppercase).
        if len(sub) >= 2:
            surname = sub[-1]                    # dernier token = nom
            firsts = sub[:-1]                    # tokens precedents
            initials_letters = [f[0].upper() for f in firsts if f]
            if initials_letters and len(surname) >= _MIN_TOKEN_LEN:
                # Variantes : "JP. Surname", "J.P. Surname", "J. Surname"
                bare = "".join(initials_letters)            # "JP"
                pointed = ".".join(initials_letters) + "."   # "J.P."
                short = initials_letters[0] + "."            # "J."
                for prefix in (bare + ".", pointed, short):
                    candidate = f"{prefix} {surname}"
                    cur = person_initial_forms.get(candidate)
                    if cur is None or ref.score > cur.score:
                        person_initial_forms[candidate] = ref
    # Abbreviated form propagated FIRST: otherwise the "Tremeau" sub-token
    # would already mask the area and the longer "JP. Tremeau" match would
    # be rejected due to overlap. Tolerant mode: an uppercase source span
    # without accents ("M. JEAN-PASCAL TREMEAU", ALL CAPS extraction) must
    # be able to propagate onto the occurrence "JP. Trémeau"
    # (mixed case + accent).
    for candidate, ref in person_initial_forms.items():
        _propagate_string(candidate, ref, tolerant=True)
    for tok, ref in person_subtokens.items():
        _propagate_string(tok, ref, tolerant=True)

    # 3) Propagation of SUB-TOKENS and ACRONYMS from multi-token ORG spans.
    #    Covered cases:
    #    - "VIS316 Visserie Inox" detected as ORG -> "VIS316" alone propagated
    #    - "Joints Elastomeres Lorraine SAS" detected as ORG -> "Joints",
    #      "Elastomeres", "Lorraine" propagated + initial-based acronym "JEL"
    #      also searched as "J.E.L", "J.E.L.", "JEL".
    org_subtokens: dict[str, Span] = {}
    org_acronyms: dict[str, Span] = {}
    for value, ref in references.items():
        if ref.entity_type not in {"ORGANIZATION", "ORG", "ORG_SINGLETON"}:
            continue
        # 3a) sous-tokens (memes regles que PERSON)
        sub = _split_person_subtokens(value)
        for tok in sub:
            current = org_subtokens.get(tok)
            if current is None or ref.score > current.score:
                org_subtokens[tok] = ref
        # 3b) acronyms: initials of meaningful sub-tokens, excluding legal
        #     suffixes (SA, SAS, SARL, ...). We form a pure acronym (JEL)
        #     and a dotted one (J.E.L). Acronyms are only generated if
        #     >= 2 initials: a single "S" would be too ambiguous.
        meaningful = [
            t for t in sub
            if t.upper() not in _LEGAL_SUFFIX_TOKENS
        ]
        if len(meaningful) >= 2:
            # Initiales en majuscules ASCII (sans accent). Sans
            # desaccentuation, "Joints Elastomeres Lorraine" produirait
            # "J.É.L" that does not match the printed acronym "J.E.L".
            letters = [
                t[0].upper().translate(_DEACCENT_TABLE) for t in meaningful if t
            ]
            if len(letters) >= 2:
                bare = "".join(letters)        # "JEL"
                pointed = ".".join(letters)    # "J.E.L"
                pointed_dot = pointed + "."    # "J.E.L."
                for variant in (bare, pointed, pointed_dot):
                    current = org_acronyms.get(variant)
                    if current is None or ref.score > current.score:
                        org_acronyms[variant] = ref
    for tok, ref in org_subtokens.items():
        _propagate_string(tok, ref, tolerant=True)
    for acro, ref in org_acronyms.items():
        _propagate_string(acro, ref, tolerant=True)

    return spans + added
