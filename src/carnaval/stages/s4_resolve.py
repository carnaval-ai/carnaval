# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Stage 4 - Resolve: deduplication and conflict resolution for spans.

Responsibilities:
- Resolve overlapping spans (multiple recognizers matched the same
  area with different types)
- Strategy: favor the most encompassing span (longest), then score,
  then recognizer priority

R2 Architecture (v7) - Explicit hierarchy principle:

  Tier 1 - CERTIFIED SIGNATURE (priority >= 95):
    Recognized by a mathematically verifiable signature (IBAN/RIB/SIRET
    checksum) or a closed format with unambiguous prefix (VAT with
    [A-Z]{2}, BIC with [A-Z]{6}). These spans are ALWAYS kept at their
    exact bounds even if they overlap a longer probabilistic span.

  Tier 2 - LABELED FISCAL LABEL (priority 85-94):
    Recognized by an explicit fiscal label + value in a short window
    (FiscalLabeledRegex, VatFrRegex without prefix, OrderRef with
    strict label). The label MAKES the content nature certain.

  Tier 3 - PATTERN WITH CONTEXT (priority 75-84):
    Recognized by a format + adjacent context (postal address,
    street + city, phone by label, plant code with label).

  Tier 4 - DICTIONARIES / DENY-LISTS (priority varies by source)

  Tier 5 - PROBABILISTIC GLiNER (priority 30):
    Neural detection without certification, wins only if nothing overlaps.

Input: DetectedDocument
Output: ResolvedDocument
"""

from __future__ import annotations

from carnaval.core.span import Span
from carnaval.stages.documents import DetectedDocument, ResolvedDocument

# Priorite par recognizer. Plus haute = gagne en cas d'egalite de
# longueur et de score (cas rare).
DEFAULT_RECOGNIZER_PRIORITY = {
    # Tier 1 - CERTIFIED SIGNATURE (>= 95): mathematical checksum or
    # closed format signature + unambiguous prefix.
    "OrgSingleton": 100,            # Client singleton deny-list (per client)
    "HeaderSourceRegex": 95,        # Certified footer
    "IbanRegex": 96,                # IBAN checksum
    "RibFrRegex": 96,               # RIB control key
    "RibFrFieldsRegex": 96,
    "EmailRegex": 95,               # RFC 5322
    "SupplierDenyList": 95,         # Explicit deny-list (if reactivated)
    # Tier 2 - EXPLICIT FISCAL LABEL (85-94)
    "VatFrRegex": 92,               # FR + implicit checksum
    "SiretRegex": 92,               # Luhn 14 digits
    "PlacesDenyList": 92,           # Explicit places deny-list
    "OrganizationsDenyList": 90,
    "PeopleDenyList": 90,
    "FiscalLabeledRegex": 88,
    "OrgSingletonLoose": 85,
    "SirenRegex": 80,
    "PhoneFrRegex": 80,
    "BicRegex": 60,
    "PostalCityFrRegex": 75,
    "ZoneFrRegex": 75,
    "StreetFrRegex": 70,
    "BpRegex": 75,
    # DE/AT/CH
    "PostalCityDeRegex": 75,
    "StreetDeRegex": 70,
    "PostfachDeRegex": 75,
    # EN (UK, US, CA, AU)
    "PostcodeUkRegex": 80,
    "ZipUsRegex": 70,
    "PostcodeCaRegex": 80,
    "StreetEnRegex": 70,
    "PoBoxRegex": 75,
    # ES
    "PostalCityEsRegex": 75,
    "StreetEsRegex": 70,
    "ApartadoEsRegex": 75,
    # IT
    "PostalCityItRegex": 75,
    "StreetItRegex": 70,
    "CasellaPostaleItRegex": 75,
    # Telephones par langue
    "PhoneDeRegex": 80,
    "PhoneUkRegex": 80,
    "PhoneUsRegex": 80,
    "PhoneOceRegex": 80,
    "PhoneEsRegex": 80,
    "PhoneLatamRegex": 80,
    "PhoneItRegex": 75,
    # Titres / civilites par langue
    "TitleDeRegex": 80,
    "ContextualPersonDeRegex": 75,
    "TitleEnRegex": 80,
    "ContextualPersonEnRegex": 75,
    "TitleEsRegex": 80,
    "ContextualPersonEsRegex": 75,
    "TitleItRegex": 80,
    "ContextualPersonItRegex": 75,
    # Bundled GeoNames / INSEE dictionaries
    "CityDict_fr": 65,
    "CityDict_de": 65,
    "CityDict_en": 65,
    "CityDict_es": 65,
    "CityDict_it": 65,
    "FirstnameDict_fr": 55,
    "FirstnameDict_de": 55,
    "FirstnameDict_en": 55,
    "FirstnameDict_es": 55,
    "FirstnameDict_it": 55,
    "FirstnameDict_pt": 55,
    "CityDict_pt": 65,
    # PT regex
    "PostalCityPtRegex": 75,
    "CepBrRegex": 75,
    "StreetPtRegex": 70,
    "ApartadoPtRegex": 75,
    "PhonePtRegex": 75,
    "PhoneBrRegex": 75,
    "TitlePtRegex": 80,
    "ContextualPersonPtRegex": 75,
    # ORG by legal suffix
    "OrgSuffixRegex": 88,
    "NameCommaRegex": 75,
    "InitialSurnameDict": 75,
    "CiviliteRegex": 75,
    "PrenomNomRegex": 65,
    "PrenomNomGluedRegex": 40,
    "ContextualPersonRegex": 75,
    "StreetGluedRegex": 60,
    "PlacesDenyList": 92,
    "ContextualLocationRegex": 78,
    "UrlRegex": 50,
    "GLiNER": 30,
    # Anti-reidentification by cross-referencing (audit P1) - high priority
    # because of closed format signature + anchored label.
    "OrderRefByContextRegex": 90,
    "PlantCodeRegex": 88,
    "TrackingRegex": 88,
    "AutomotiveOemDict": 82,
    # Audit P2
    "ApeCodeRegex": 90,
    "CapitalRegex": 88,
    "InternalRefRegex": 85,
    "PostalEuRegex": 80,
    # Audit P3
    "OrgStructureRegex": 75,
    # Audit v2 P3 - supplier deny list
    "SupplierDenyList": 95,
    "CommercialCellRegex": 86,
    "ParenContentRegex": 78,
    "ClientCodeRegex": 88,
    "CompactDateRegex": 82,
    "AddressFragmentRegex": 76,
    "TableColumnsRegex": 87,
    # Audit v3 P4 - Patrice directive "N° d'A"
    "AffairNumberRegex": 90,
}


def _span_priority(span: Span, priority_map: dict[str, int]) -> int:
    return priority_map.get(span.recognizer, 0)


# Recognizers whose span boundary is mathematically certain
# (IBAN checksum, RIB control key) or explicitly declared by
# the user in a private deny-list. In case of overlap with
# a longer probabilistic span (encompassing GLiNER LOCATION), their
# span takes precedence: we prefer to clip the encompassing span to preserve the
# certified data rather than losing it.
#
# Lyreco case: "49180 ST BARTHELEMY D ANJOU BP 70039" - GLiNER detects
# a LOCATION covering "49180 ST BARTHELEMY D ANJOU BP" which overlaps
# the singleton "BP 70039" on the last 3 characters (" BP"). Without
# singleton certification, the (longer) LOCATION wins and
# "70039" remains exposed in the output.
_CERTIFIED_RECOGNIZERS = frozenset({
    "IbanRegex", "RibFrRegex",
    # Email: closed format signature (simplified RFC 5322). A detected
    # email must be treated ATOMICALLY - otherwise the tokenizer produces
    # "[PERSON_n].[PERSON_m]@[ORG][EMAIL_p]" which reveals the
    # firstname.lastname@domain convention (audit P2 V8).
    "EmailRegex",
    # Private explicit deny-lists: the user has declared these entities
    # as mandatory to mask; their span is a ground truth.
    "OrgSingleton", "OrgSingletonLoose",
    "OrganizationsDenyList", "OrganizationsLooseDenyList",
    "PeopleDenyList", "PlacesDenyList",
    "SupplierDenyList",
})


def _clip_around_certified(
    span: Span, certified: list[Span], text: str
) -> Span | None:
    """Clip `span` so that it does not overlap any already accepted certified span.

    An improperly bounded probabilistic span (GLiNER) that has swallowed an IBAN/RIB
    is thus shortened rather than lost: the certified data keeps its
    exact boundaries, and the rest of the span (e.g., an address) remains
    masked. Returns the largest remaining fragment, or None if nothing remains,
    or the unchanged span if it does not overlap any certified span.
    """
    covered: set[int] = set()
    for c in certified:
        covered.update(range(c.start, c.end))
    if not any(i in covered for i in range(span.start, span.end)):
        return span
    # Largest sub-interval of [span.start, span.end] outside of `covered`.
    best_start = best_end = 0
    run_start: int | None = None
    for i in range(span.start, span.end + 1):
        free = i < span.end and i not in covered
        if free:
            if run_start is None:
                run_start = i
        elif run_start is not None:
            if i - run_start > best_end - best_start:
                best_start, best_end = run_start, i
            run_start = None
    if best_end <= best_start:
        return None
    if best_start == span.start and best_end == span.end:
        return span
    return Span(
        start=best_start,
        end=best_end,
        entity_type=span.entity_type,
        text=text[best_start:best_end],
        score=span.score,
        recognizer=span.recognizer,
        metadata=span.metadata,
    )


def resolve(
    doc: DetectedDocument,
    priority_map: dict[str, int] | None = None,
) -> ResolvedDocument:
    """Deduplicate overlapping Spans.

    Sorting criteria (descending for acceptance):
        1. Length (most encompassing wins)
        2. Score
        3. Recognizer priority
        4. Position (left first)
    """
    pmap = priority_map if priority_map is not None else DEFAULT_RECOGNIZER_PRIORITY

    # Trim boundary whitespaces of each span BEFORE arbitration: a span
    # that has encompassed the final trailing space would stick its placeholder to
    # the next token ("[ADDR]Tel."). Trimming tightens the span on its substance
    # and makes the sorting length criterion below more reliable.
    trimmed_spans = []
    for s in doc.spans:
        t = s.trim_whitespace()
        if t is not None:
            trimmed_spans.append(t)

    # Sort for acceptance. A "certified" span (IBAN validated by checksum,
    # RIB by key) has a certain boundary: it is processed first and
    # cannot be evicted by a longer but probabilistic span.
    sorted_spans = sorted(
        trimmed_spans,
        key=lambda s: (
            0 if s.recognizer in _CERTIFIED_RECOGNIZERS else 1,
            -s.length,
            -s.score,
            -_span_priority(s, pmap),
            s.start,
        ),
    )

    accepted: list[Span] = []
    certified: list[Span] = []
    for s in sorted_spans:
        clipped = _clip_around_certified(s, certified, doc.text)
        if clipped is None:
            continue
        if any(clipped.overlaps(a) for a in accepted):
            continue
        accepted.append(clipped)
        if clipped.recognizer in _CERTIFIED_RECOGNIZERS:
            certified.append(clipped)

    # Reorder by position (ascending start) for the rest of the pipeline
    accepted.sort(key=lambda s: s.start)

    return ResolvedDocument(
        source_path=doc.source_path,
        text=doc.text,
        language=doc.language,
        spans=tuple(accepted),
        metadata={
            **doc.metadata,
            "raw_spans_count": len(doc.spans),
            "resolved_spans_count": len(accepted),
        },
    )
