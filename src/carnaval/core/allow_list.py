# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Protection layer: regions of text that must never be masked.

A profile declares, under `allow_lists/`, two types of protection:

- **Regex patterns** (order numbers, product references, etc.): any string
  declared outside the `business_lexicon` key;
- A **business lexicon** under the `business_lexicon` key: literal words
  (quantity, price, discount, etc.) that no recognizer should mask, so that
  the document structure remains readable by downstream extraction services.

Any detection span that overlaps a protected region — either a regex pattern
or a lexicon word — is discarded before masking.

The lexicon matching is case- and accent-insensitive. A word is bounded by
word boundaries, except in Chinese writing (no separators), where matching
is performed as a direct substring.
"""

from __future__ import annotations

import re
from typing import Any

from carnaval.core.span import Span

# Cle reservee : son contenu est un lexique de mots litteraux, pas des regex.
_LEXICON_KEY = "business_lexicon"


# Recognizers dont les spans NE SONT JAMAIS ecartes par apply_allow_list :
# leur signature est trop forte pour qu'on les confonde avec une reference
# produit ou un libelle metier qui les chevaucherait incidemment. Sans
# cette exemption, un pattern allow_list comme "\\d{4} \\d{2} \\d{2}"
# (reference produit a groupes numeriques) happe un telephone UK
# "+44 1208 81 47 14" et la PII fuit. Idem pour les nouveaux recognizers
# d'identifiants nationaux (NI Number, URSSAF, HMRC, NIR, ...) qui
# matchent un format explicitement contextualise.
_ALLOW_LIST_EXEMPT_RECOGNIZERS: frozenset[str] = frozenset({
    # Signatures fortes
    "EmailRegex", "UrlRegex",
    "IbanRegex", "BicRegex",
    "RibFrRegex", "RibFrFieldsRegex",
    # Identifiants nationaux contextualises (libelle obligatoire)
    "NationalIdRegex",
    "SocialSecurityFrRegex", "UrssafRegex",
    "UkNiNumberRegex", "UkDrivingLicenceRegex", "UkUtrRegex",
    "HmrcRefRegex",
    "EsDniRegex", "EsNieRegex", "EsCifRegex", "EsCccRegex",
    "PtNifRegex", "PtCcRegex", "PtNissRegex",
    "PlNipRegex", "PlRegonRegex", "PlKrsRegex", "PlPeselRegex",
    "DeHandelsregisterRegex", "DeNationalIdRegex",
    "TrTcknRegex", "TrVknRegex", "TrSgkRegex", "TrSicilRegex",
    "CzRodneCisloRegex", "CzIcoRegex", "CzDicRegex", "CzOpRegex",
    "CzCsszRegex",
    "CnIdRegex", "CnUsccRegex", "CnHkidRegex", "CnPassportRegex",
    "BankAccountByContextRegex",
    "JpMaiNumberRegex", "JpHojinBangoRegex",
    "JpDriverLicenceRegex", "JpPassportRegex",
    "JpHealthInsuranceRegex", "JpToukiBangouRegex",
    "KrBusinessRegistrationRegex", "KrRrnRegex",
    "ItCodiceFiscaleRegex", "ItCodiceSdiRegex",
    "ItRegulatoryRegex", "ItTesseraSanitariaRegex",
    "BgEgnRegex", "BgEikRegex", "BgLnchRegex",
    "BgIdCardRegex", "BgHealthInsuranceRegex",
    # Anti-reidentification par recoupement (audit P1)
    "OrderRefByContextRegex", "PlantCodeRegex", "TrackingRegex",
    "AutomotiveOemDict",
    # Audit P2
    "ApeCodeRegex", "CapitalRegex", "InternalRefRegex", "PostalEuRegex",
    # Audit P3
    "OrgStructureRegex",
    # Audit v2 P3 (v4 : SupplierDenyList retire)
    "CommercialCellRegex", "ParenContentRegex", "ClientCodeRegex",
    "CompactDateRegex", "AddressFragmentRegex", "TableColumnsRegex",
    # Audit v3 P4
    "AffairNumberRegex",
    # PII personnelles RGPD
    "DateOfBirthRegex", "MaidenNameRegex",
    # Fiscal / org confirmes par contexte
    "VatFrRegex", "SirenRegex", "SiretRegex", "OrgSuffixRegex",
    # Deny-lists privees (declarees par le client dans son profil)
    "OrgSingleton", "OrgSingletonLoose",
    "OrganizationsDenyList", "OrganizationsLooseDenyList",
    "PeopleDenyList",
    # Telephones avec prefix international (signature univoque)
    "PhoneUkRegex", "PhoneBeRegex", "PhoneOceRegex",
    "PhoneInternationalRegex",
})

# Depliage des accents -> ASCII. Chaque caractere accentue est remplace par
# un seul caractere : la longueur est preservee, les positions ne bougent
# pas. Couvre les diacritiques FR/ES/PT/PL/TR utiles au lexique.
_DEACCENT = str.maketrans(
    # Latin: FR / ES / IT / PT / DE / NL / TR (minuscules)
    "àâäáãåèéêëìíîïòóôöõùúûüýÿçñşğı"
    # Polonais : a/c/e/l/n/o/s/z (ogonek, kreska, cedille...)
    "ąćęłńóśźż"
    # Tcheque / slovaque : carons (hacek) + kroužek.
    # ě→e, š→s, č→c, ř→r, ž→z, ť→t, ď→d, ň→n, ů→u
    "ěščřžťďňů"
    # Majuscules turques : İ -> I (dotted I), Ş -> S, Ğ -> G.
    # Ç/Ö/Ü majuscules sont traites par .lower() avant translate.
    "İŞĞ",
    "aaaaaaeeeeiiiiooooouuuuyycnsgi"
    "acelnoszz"
    "escrztdnu"
    "ISG",
)

# Caracteres han : un mot qui en contient est appari sans limite de mot
# (l'ecriture chinoise n'a pas de separateur de mots).
_CJK_PATTERN = re.compile(r"[一-鿿㐀-䶿]")


def _normalize(text: str) -> str:
    """Lowercase + de-accented, preserving character length one-to-one."""
    return text.lower().translate(_DEACCENT)


def _collect_entries(node: Any, in_lexicon: bool = False) -> tuple[list[str], list[str]]:
    """Separate lexicon words from regex patterns.

    Any string found under the `business_lexicon` key is treated as a literal word;
    any other string is treated as a regex pattern.

    Returns:
        (lexicon_words, regex_patterns)
    """
    words: list[str] = []
    patterns: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            w, p = _collect_entries(value, in_lexicon or key == _LEXICON_KEY)
            words += w
            patterns += p
    elif isinstance(node, list):
        for item in node:
            w, p = _collect_entries(item, in_lexicon)
            words += w
            patterns += p
    elif isinstance(node, str):
        (words if in_lexicon else patterns).append(node)
    return words, patterns


def _regex_zones(text: str, patterns: list[str]) -> list[tuple[int, int]]:
    """Return intervals covered by the regex patterns. Invalid patterns are ignored."""
    zones: list[tuple[int, int]] = []
    for pattern in patterns:
        try:
            compiled = re.compile(pattern)
        except re.error:
            continue  # motif invalide : ignore, ne casse pas le pipeline
        for match in compiled.finditer(text):
            if match.end() > match.start():
                zones.append((match.start(), match.end()))
    return zones


def _lexicon_zones(text: str, words: list[str]) -> list[tuple[int, int]]:
    """Return intervals covered by lexicon words (case/accent insensitive)."""
    if not words:
        return []
    norm_text = _normalize(text)
    zones: list[tuple[int, int]] = []
    for word in words:
        stripped = word.strip()
        if not stripped:
            continue
        norm_word = _normalize(stripped)
        if _CJK_PATTERN.search(stripped):
            # Ecriture chinoise : appariement direct, sans limite de mot.
            start = norm_text.find(norm_word)
            while start != -1:
                zones.append((start, start + len(norm_word)))
                start = norm_text.find(norm_word, start + len(norm_word))
        else:
            # Limites de mot tolerantes : (?<!\w) / (?!\w) acceptent qu'un mot
            # finisse par un caractere non alphanumerique (ex : "p.u").
            rx = re.compile(r"(?<!\w)" + re.escape(norm_word) + r"(?!\w)")
            for match in rx.finditer(norm_text):
                zones.append((match.start(), match.end()))
    return zones


# Seuil de recouvrement pour le lexique : un span couvert a AU MOINS ce
# taux par des mots du lexique est ecarte. En-deca, il est conserve - un
# mot incident dans une URL ne doit pas empecher de la masquer.
#
# Calibre a 0.5 (et non 0.8) : un span GLiNER qui deborde sur un saut de
# ligne ou un mot adjacent ("Commande\nPage", "Incoterms DAP" mange en
# bloc) dilue le ratio en-dessous de 80 % alors que le mot metier en
# represente la moitie. Abaisser le seuil rattrape ces debordements ;
# le risque d'ecarter a tort une URL ou un email contenant incidemment
# un mot du lexique est marginal en pratique (ces spans font typiquement
# 2-3 fois la longueur du mot incident).
_OVERLAP_THRESHOLD = 0.5


def _covered_ratio(span: Span, covered: set[int]) -> float:
    """Return the fraction of the span's characters that fall inside protected zones, in [0, 1]."""
    length = span.end - span.start
    if length <= 0:
        return 0.0
    inside = sum(1 for i in range(span.start, span.end) if i in covered)
    return inside / length


def apply_allow_list(
    text: str, spans: list[Span], allow_lists: dict[str, Any]
) -> list[Span]:
    """Remove spans that fall inside protected business zones.

    Two regimes depending on zone type:

    - **Regex pattern** (product reference, order number, date): describes
      precise structured data. Any span that touches it, even partially,
      is discarded — it is a false positive from a recognizer that matched
      a fragment of the protected data.
    - **Lexicon word**: a business label. The span is only discarded if it
      is covered at or above `_OVERLAP_THRESHOLD`. A lexicon word appearing
      incidentally inside a URL or email must not prevent masking of the
      actual PII.

    Args:
        text: Source text.
        spans: Spans detected by the recognizers.
        allow_lists: The `allow_lists` block from the resolved configuration.

    Returns:
        The input spans, with those falling in protected zones removed.
    """
    words, patterns = _collect_entries(allow_lists)
    regex_zones = _regex_zones(text, patterns)
    lexicon_zones = _lexicon_zones(text, words)
    if not regex_zones and not lexicon_zones:
        return spans
    lexicon_covered: set[int] = set()
    for z0, z1 in lexicon_zones:
        lexicon_covered.update(range(z0, z1))
    kept: list[Span] = []
    for s in spans:
        # Un recognizer a signature forte (email, IBAN, BIC, PII a libelle
        # contextuel obligatoire, deny-list...) est exempte du filtrage :
        # son span est conserve quoi qu'il arrive. Sans cela, un pattern
        # de protection de reference produit happerait un telephone
        # international, un IBAN ou un NI Number qui s'en approcherait.
        if s.recognizer in _ALLOW_LIST_EXEMPT_RECOGNIZERS:
            kept.append(s)
            continue
        if any(not (s.end <= z0 or z1 <= s.start) for z0, z1 in regex_zones):
            continue  # contact avec une donnee structuree -> faux positif
        if _covered_ratio(s, lexicon_covered) >= _OVERLAP_THRESHOLD:
            continue  # span majoritairement constitue de libelles metier
        kept.append(s)
    return kept
