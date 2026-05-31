# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer pour les numeros d'identite nationaux.

Les pieces d'identite (CNI, passeport, registre national) sont des PII
critiques RGPD. Les formats varient par pays mais on dispose toujours
d'un libelle qui annonce le numero - on l'utilise comme ancre pour
eviter les faux positifs (un code interne peut ressembler a un numero
de CNI dans le vide).

Couverture initiale (a etendre selon les flux reels) :
- FR : CNI = 12 chiffres / 9 chiffres / format mixte lettres+chiffres
  (anciennes CNI). Libelle : "CNI n°", "carte d'identite", "n° de CNI".
- BE : Registre national = 11 chiffres formates JJ.MM.AA-NNN.CC.
- ES : DNI = 8 chiffres + 1 lettre.
- DE : Personalausweis = 9-10 caracteres alphanumeriques.

Strategie : libelle + sequence d'identifiant qui suit. Seule la sequence
est masquee (le libelle reste).
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelles ancrant un numero d'identite. Multilingue.
_ID_LABEL = (
    r"(?P<label>"
    # FR
    r"CNI\s*n[°o]?"
    r"|carte\s+(?:nationale\s+)?d['’]identit[ée]\s*(?:n[°o]?)?"
    r"|num[ée]ro\s+de\s+CNI"
    r"|n[°o]\s+de\s+CNI"
    r"|pi[èe]ce\s+d['’]identit[ée]\s+communiqu[ée]e\s*(?::|\-)?\s*CNI"
    # BE
    r"|registre\s+national"
    r"|num[ée]ro\s+national"
    # ES
    r"|DNI\s*n[°o]?"
    r"|NIF\s*n[°o]?"
    # DE - tolere "Personalausweis Nr.", "Personalausweis-Nr." et
    # "PersonalausweisNr." (avec ou sans separateur).
    r"|Personalausweis(?:[\s\-]*Nr\.?)?"
    r"|Ausweisnummer"
    # TR - Nüfus cüzdanı (carte d'identite turque). Formats observes :
    # "Nüfus cüzdanı seri/no: A22 845116", "Nüfus cüzdanı no", etc.
    r"|N[üu]fus\s+c[üu]zdan[ıi](?:\s+seri/?no)?(?:\s*no)?"
    # EN
    r"|national\s+ID(?:\s*number)?"
    r"|ID\s+card\s+number"
    r"|passport\s+(?:number|n[°o])"
    r")"
)

# Tolerance entre le libelle et l'identifiant : separateur, ponctuation,
# eventuel mot court ("numero", "communiqué", ":"...). Maximum 30 chars.
_SEP = r"[^\d\nA-Z]{0,30}"

# Identifiant : sequence alphanumerique de longueur 8-20, autorisant les
# tirets / points / espaces internes (formats FR / BE / etc.).
# On exige au moins 6 caracteres apres normalisation pour eviter les
# matches courts (ex: "n° 12").
_ID_VALUE = r"(?P<id>[A-Z0-9][A-Z0-9.\- ]{6,22}[A-Z0-9])"

_NATIONAL_ID_PATTERN = re.compile(
    rf"{_ID_LABEL}{_SEP}{_ID_VALUE}",
    re.IGNORECASE,
)


# Numero de securite sociale francais (NIR / NNI) : 15 chiffres au total
# repartis 1 + 2 + 2 + 2 + 3 + 3 + 2 (la cle). Sequenes typiques :
#   "1 78 04 88 044 022 / 47" (avec / avant cle)
#   "1780488044022 / 47" / "178 04 88 044 022 47" (cle accolee)
# On exige au moins un libelle court ("securite sociale" / "NIR" / "NNI"
# / "sécu" / "assure social") dans les 40 caracteres precedents pour
# eviter les faux positifs sur des references commerciales.
_SOCSEC_FR_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?P<value>"
    r"[12](?:\s|\.)?\d{2}(?:\s|\.)?\d{2}(?:\s|\.)?\d{2}"
    r"(?:\s|\.)?\d{3}(?:\s|\.)?\d{3}(?:\s|\.|/|\s/)?\s?\d{2}"
    r")"
    r"(?!\d)"
)
_SOCSEC_FR_LABEL_CONTEXT = re.compile(
    r"(?i)(?:securite\s+sociale|s[ée]curit[ée]\s+sociale|s[ée]cu"
    r"|NIR|NNI|num[ée]ro\s+(?:de\s+)?s[ée]cu|assur[ée]\s+social"
    # ES (le n° de SS FR peut etre cite dans un AR ES pour un
    # travailleur transfrontalier).
    r"|seguridad\s+social|n[úu]mero\s+(?:de\s+)?seguridad"
    # PT
    r"|seguran[çc]a\s+social"
    # IT
    r"|sicurezza\s+sociale"
    r")"
)

# Numero de Cuenta de Cotizacion (CCC) espagnol : 12 chiffres groupes
# souvent en "39 0008118 44" (regime 39 + code + cle). Toujours
# precede du libelle "Cuenta cotizacion" / "CCC".
_ES_CCC_PATTERN = re.compile(
    r"(?i)(?:cuenta\s+(?:de\s+)?cotizaci[oó]n|CCC|Reg\.?\s*Esp\.?\s*Aut[oó]nomos)"
    r"[\s\-:.\w]{0,30}?"
    r"(?P<value>\d{2}[\s\-/]?\d{6,8}[\s\-/]?\d{1,2})"
)


# URSSAF FR : numero d'identification employeur. Format typique
# "880-8118-44" ou "880 8118 44". Toujours precede du libelle URSSAF.
_URSSAF_PATTERN = re.compile(
    r"(?i)n[°o]?\s*URSSAF\s*[:\-]?\s*"
    r"(?P<value>\d{3}[\s\-]?\d{4}[\s\-]?\d{2})"
)

# UK National Insurance Number (NINO). Format officiel HMRC :
#   2 lettres prefixe + 6 chiffres + 1 lettre suffixe.
#   Exemples : "AB 12 34 56 C", "AB123456C", "AB 12 34 56 C / 78"
# Prefixes interdits : "BG", "GB", "NK", "KN", "TN", "NT", "ZZ" (mais
# on ne filtre pas pour rester permissif).
_UK_NI_PATTERN = re.compile(
    r"(?<![A-Z])"
    r"(?P<value>[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-Z])"
    r"(?![A-Z])"
)
# Le NINO est ambigu sans contexte (un code matricule de la meme forme
# pourrait exister). On exige un libelle "National Insurance" / "NI"
# / "NINO" dans les 60 caracteres precedents.
_UK_NI_CONTEXT = re.compile(
    r"(?i)(?:national\s+insurance|NINO|NI\s+number|NI\s+no)"
)

# UK driving licence : 16 caracteres alphanumeriques (5 lettres du nom
# + 6 chiffres date + 1 lettre + 2 lettres prenom + 1 controle). On
# reste tolerant : 12-18 caracteres alphanumeriques avec libelle
# explicite "driving licence" / "driver's licence".
_UK_DRIVER_LICENCE = re.compile(
    r"(?i)driv(?:ing|er.?s)\s+licen[sc]e\s*(?:n[°o]?\.?)?\s*"
    r"(?P<value>[A-Z0-9]{10,18})"
)

# UK Unique Taxpayer Reference (UTR) : 10 chiffres, parfois groupes en
# "851 887 002 X". Toujours precede du libelle "UTR" / "Unique
# Taxpayer Reference".
_UK_UTR_PATTERN = re.compile(
    r"(?i)(?:UTR|Unique\s+Taxpayer\s+Reference)\s*[:\-]?\s*"
    r"(?P<value>\d{3}[\s\-]?\d{3}[\s\-]?\d{3,4})"
)

# HMRC self-assessment ID : format "HMRC-XXX-XXXX-XX" ou variantes.
_HMRC_REF_PATTERN = re.compile(
    r"(?i)(?:HMRC[\s\-:]+)"
    r"(?P<value>(?:self[\s\-]assessment\s+ID\s+)?HMRC[\s\-]\d{3}[\s\-]?\d{4}[\s\-]?\d{2})"
)
_HMRC_VALUE_PATTERN = re.compile(
    r"(?i)\bHMRC[\s\-]\d{3}[\s\-]?\d{4}[\s\-]?\d{2}\b"
)


def recognize_social_security_fr(text: str, score: float = 0.95) -> list[Span]:
    """Detecte les numeros de securite sociale FR (NIR / NNI).

    Le format complet (15 chiffres) avec ou sans separateurs est capture
    en un seul span - sans cela, un fragment ("04 88 044 022") est pris
    pour un telephone et le reste du numero ("1 78", "/ 47") reste en
    clair.
    """
    spans: list[Span] = []
    for m in _SOCSEC_FR_PATTERN.finditer(text):
        # Contexte exigeant : un libelle social a moins de 60 caracteres
        # avant le candidat. Sans contexte, on filtre.
        window = text[max(0, m.start() - 60): m.start()]
        if not _SOCSEC_FR_LABEL_CONTEXT.search(window):
            continue
        start, end = m.span("value")
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="SocialSecurityFrRegex",
            )
        )
    return spans


def recognize_urssaf(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les numeros d'identification employeur URSSAF."""
    spans: list[Span] = []
    for m in _URSSAF_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="UrssafRegex",
            )
        )
    return spans


def recognize_uk_national_insurance(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les UK National Insurance Numbers (`AB 12 34 56 C`).

    Le contexte est obligatoire : libelle "National Insurance" /
    "NINO" / "NI Number" dans les 60 caracteres precedents. Sans cela
    on rejette pour eviter les faux positifs sur des codes matricules
    de meme forme.
    """
    spans: list[Span] = []
    for m in _UK_NI_PATTERN.finditer(text):
        window = text[max(0, m.start() - 60): m.start()]
        if not _UK_NI_CONTEXT.search(window):
            continue
        start, end = m.span("value")
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="UkNiNumberRegex",
            )
        )
    return spans


def recognize_uk_driving_licence(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les numeros de permis de conduire britanniques precedes
    du libelle 'driving licence' / 'driver's licence'.
    """
    spans: list[Span] = []
    for m in _UK_DRIVER_LICENCE.finditer(text):
        start, end = m.span("value")
        value = m.group("value")
        # On exige au moins UN chiffre dans le numero (sinon c'est un
        # mot suiveur du libelle).
        if not any(c.isdigit() for c in value):
            continue
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="NATIONAL_ID",
                text=value,
                score=score,
                recognizer="UkDrivingLicenceRegex",
            )
        )
    return spans


def recognize_uk_utr(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les UK Unique Taxpayer Reference (UTR)."""
    spans: list[Span] = []
    for m in _UK_UTR_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="UkUtrRegex",
            )
        )
    return spans


def recognize_hmrc_ref(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les references HMRC (self-assessment ID, format
    HMRC-XXX-XXXX-XX)."""
    spans: list[Span] = []
    for m in _HMRC_VALUE_PATTERN.finditer(text):
        spans.append(
            Span(
                start=m.start(),
                end=m.end(),
                entity_type="NATIONAL_ID",
                text=m.group(0),
                score=score,
                recognizer="HmrcRefRegex",
            )
        )
    return spans


# ES DNI : 8 chiffres + 1 lettre de controle (sans separateur).
#    "12345678Z"
# ES NIE : X/Y/Z + 7 chiffres + 1 lettre.
#    "X1234567L"
# ES CIF / NIF entreprise : 1 lettre [ABCDEFGHJNPQRSUVW] + 8 chiffres
# (la derniere etant parfois une lettre).
#    "B95187721"  ou  "A78845671"  ou  "G12345678"
#
# Le pattern est sensible au contexte : sans libelle explicite, un
# code 8-chiffres+lettre peut etre une reference produit. On exige
# le libelle "DNI", "NIE", "NIF", "CIF", "C.I.F" (avec separateurs).
_ES_DNI_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?P<value>\d{8}[A-HJ-NP-TV-Z])(?![A-Z0-9])"
)
_ES_NIE_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?P<value>[XYZ]\d{7}[A-HJ-NP-TV-Z])(?![A-Z0-9])"
)
_ES_CIF_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?P<value>[ABCDEFGHJNPQRSUVW][\s\-]?\d{8})(?![A-Z0-9])"
)
_ES_ID_LABEL_CONTEXT = re.compile(
    r"(?i)\b(?:DNI|NIE|NIF|CIF|C\.I\.F)\b"
)


def recognize_es_dni(text: str, score: float = 0.9) -> list[Span]:
    """DNI espagnol (8 chiffres + lettre de controle), contexte requis."""
    spans: list[Span] = []
    for m in _ES_DNI_PATTERN.finditer(text):
        window = text[max(0, m.start() - 40): m.start()]
        if not _ES_ID_LABEL_CONTEXT.search(window):
            continue
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="EsDniRegex",
            )
        )
    return spans


def recognize_es_nie(text: str, score: float = 0.9) -> list[Span]:
    """NIE espagnol (X/Y/Z + 7 chiffres + lettre)."""
    spans: list[Span] = []
    for m in _ES_NIE_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="EsNieRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# Allemagne
# ---------------------------------------------------------------------
# Handelsregister (HRB = Handelsregister B / HRA = Handelsregister A) :
# numero d'inscription au registre de commerce allemand. Format :
# "HRB 188044" / "HRA 4422" / "HRB-Eintrag: HRB 4422". Toujours
# precede du libelle HRB ou HRA.
_DE_HR_PATTERN = re.compile(
    r"(?i)\bHR[AB]\b[\s:nr.\-]{0,15}(?P<value>\d{3,8})"
)


def recognize_de_handelsregister(text: str, score: float = 0.9) -> list[Span]:
    """Numero d'inscription au Handelsregister allemand (HRB / HRA)."""
    spans: list[Span] = []
    for m in _DE_HR_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="DeHandelsregisterRegex",
            )
        )
    return spans


# Identifiants nationaux DE precedes d'un libelle :
#   - Sozialversicherungsnummer / SVNR / SV-Nr (n° secu sociale)
#   - Steuer-Identifikationsnummer / Steuer-ID (n° fiscal personnel
#     11 chiffres)
#   - Rentenversicherungsnummer / RVNR
#   - Mitgliedsnummer / Mitgliedsnr (n° d'adhesion mutuelle/assurance)
# Le format suivant le libelle est tres variable (collé, espace,
# lettre alphanumerique intercalee comme "14 041169 F 028"). On
# capture une sequence alphanumerique avec separateurs admis, de 8 a
# 25 caracteres.
_DE_ID_PATTERN = re.compile(
    # Libelle IGNORECASE. PAS de \b a la fin : "Mitgliedsnr." finit
    # par "." (non-\w) et `\b` echouerait au bord ".".
    r"(?i)\b(?:"
    r"Sozialversicherungs(?:nummer|nr\.?)|SVN[Rr]|SV[\.\-]?N[rR]\.?"
    r"|Renten(?:versicherungs)?nummer|RVN[rR]"
    r"|Steuer[\s\-]?Identifikations(?:nummer|nr\.?)|Steuer[\s\-]?ID"
    r"|Mitglieds(?:nummer|nr\.?)"
    r"|Krankenversicherungs(?:nummer|nr\.?)"
    r")"
    # Separateur tolerant : ponctuation + petits mots intercalaires
    # ("(lebenslang)" entre Steuer-ID et la valeur).
    r"[\s:\-\(\)\w]{0,30}?"
    # Valeur : strictement majuscules et chiffres (marqueur (?-i:...)
    # qui retire IGNORECASE), pour ne pas que la lazy consomme un mot
    # en minuscules comme "lebenslang".
    r"(?P<value>(?-i:[A-Z0-9])(?:[\s\-/]?(?-i:[A-Z0-9])){7,24})"
)


def recognize_de_national_id(text: str, score: float = 0.9) -> list[Span]:
    """Identifiants nationaux allemands precedes de leur libelle :
    Sozialversicherungsnummer, Steuer-ID, Rentenversicherungsnummer,
    Mitgliedsnr, Krankenversicherungsnummer.
    """
    spans: list[Span] = []
    for m in _DE_ID_PATTERN.finditer(text):
        start, end = m.span("value")
        value = m.group("value")
        # Le span doit contenir au moins 6 chiffres pour exclure les
        # mots ordinaires happes par le pattern.
        if sum(1 for c in value if c.isdigit()) < 6:
            continue
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=value,
                score=score,
                recognizer="DeNationalIdRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# Chine (PRC) et Hong-Kong
# ---------------------------------------------------------------------
# Carte d'identite chinoise (Resident Identity Card, 居民身份证) :
# 18 caracteres = 17 chiffres + 1 cle (chiffre OU lettre X).
# PII personnelle critique (PIPL).
#   "身份证号码: 110105199001011234"
#   "ID 110105199001011234"
#   "Shenfenzheng: 11010519900101123X"
_CN_ID_PATTERN = re.compile(
    r"(?:身份证(?:号码?)?|身份证号|身分證(?:號碼?)?|身份證(?:號)?"
    r"|居民身份证|shenfenzheng|ID\s*card|ID\s*No\.?|ID)"
    # Tolere du texte intermediaire entre le libelle et la valeur :
    # parentheses pleines-largeur "（...）" + ":" / "：" + sauts de
    # ligne (l'extraction PDF chinoise peut couper la ligne entre le
    # libelle et la valeur sur 18 chiffres). Limite 30 chars.
    r"[^\d]{0,30}?"
    r"(?P<value>\d{17}[\dXx])"
)


# Passeport chinois : 1 ou 2 lettres + 7 ou 8 chiffres.
# Format observe : "护照编号 G88451167" (G + 8 chiffres),
# "护照编号 E12345678" (E + 8 chiffres), "MA1234567".
# Libelle obligatoire (sans cela, un code commercial alphanumerique
# de meme forme matcherait a tort).
_CN_PASSPORT_PATTERN = re.compile(
    r"(?:护照(?:编号|号码)?|護照(?:編號|號碼)?|passport\s+(?:number|n[°o])?)"
    r"[^\dA-Z\n]{0,15}?"
    r"(?P<value>[A-Z]{1,2}\d{7,8})"
)


def recognize_cn_passport(text: str, score: float = 0.9) -> list[Span]:
    """Passeport chinois (1-2 lettres + 7-8 chiffres, libelle obligatoire)."""
    spans: list[Span] = []
    for m in _CN_PASSPORT_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CnPassportRegex",
            )
        )
    return spans

# Code de credit social uniforme (Unified Social Credit Code -
# 统一社会信用代码) : 18 caracteres alphanumeriques (chiffres +
# lettres majuscules). Equivalent SIRET/SIREN chinois.
#   "统一社会信用代码: 91110000100000000X"
_CN_USCC_PATTERN = re.compile(
    r"(?:统一社会信用代码|统一信用代码|社会信用代码"
    r"|Unified\s+Social\s+Credit\s+Code|USCC)"
    r"\s*[:：\-]?\s*"
    r"(?P<value>[0-9A-HJ-NP-RT-Y]{18})"
)

# Hong Kong ID (HKID) : 1 ou 2 lettres + 6 chiffres + 1 chiffre/lettre
# avec parenthese sur le dernier (typique).
#   "HKID A123456(7)" ou "HKID AB1234567"
_CN_HKID_PATTERN = re.compile(
    r"(?i)\bHKID\s*[:\-]?\s*"
    r"(?P<value>[A-Z]{1,2}\d{6}\(?\d|[A-Z]\)?)"
)


def recognize_cn_id(text: str, score: float = 0.95) -> list[Span]:
    """Carte d'identite chinoise (resident ID, 18 caracteres)."""
    spans: list[Span] = []
    for m in _CN_ID_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CnIdRegex",
            )
        )
    return spans


def recognize_cn_uscc(text: str, score: float = 0.9) -> list[Span]:
    """Unified Social Credit Code chinois (18 caracteres)."""
    spans: list[Span] = []
    for m in _CN_USCC_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CnUsccRegex",
            )
        )
    return spans


def recognize_cn_hkid(text: str, score: float = 0.85) -> list[Span]:
    """Hong Kong Identity Card number."""
    spans: list[Span] = []
    for m in _CN_HKID_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CnHkidRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# Japon
# ---------------------------------------------------------------------
# Mai Number (マイナンバー / 個人番号) : numero d'identification
# individuel japonais, 12 chiffres. PII personnelle critique
# (APPI - Act on Protection of Personal Information).
#   "マイナンバー: 123456789012"
#   "個人番号: 1234 5678 9012"
_JP_MAI_NUMBER_PATTERN = re.compile(
    r"(?:マイナンバー|個人番号|My\s*Number)"
    # Tolere texte intermediaire (parentheses pleines-largeur "（...）"
    # + ":" / "：" + sauts de ligne).
    r"[^\d]{0,30}?"
    r"(?P<value>\d{4}[\s\-]?\d{4}[\s\-]?\d{4})"
)

# Hojin Bango (法人番号 - Corporate Number) : 13 chiffres,
# equivalent SIRET japonais.
#   "法人番号: 1234567890123"
_JP_HOJIN_BANGO_PATTERN = re.compile(
    r"(?:法人番号|Corporate\s+Number|Hojin\s+Bango)"
    r"\s*[:：\-]?\s*"
    r"(?P<value>\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d|\d{13})"
)

# Permis de conduire japonais (運転免許証番号) : 12 chiffres.
_JP_DRIVER_LICENCE_PATTERN = re.compile(
    r"(?:運転免許証(?:番号)?|運転免許番号|driver.s?\s+licen[sc]e)"
    r"\s*[:：\-]?\s*"
    r"(?P<value>\d{12})"
)

# Passeport japonais : 2 lettres + 7 chiffres.
_JP_PASSPORT_PATTERN = re.compile(
    r"(?:パスポート(?:番号)?|旅券番号|passport\s+(?:number|n[°o])?)"
    r"\s*[:：\-]?\s*"
    r"(?P<value>[A-Z]{2}\d{7})"
)


# Numero de compte bancaire general (pays sans IBAN ou format non
# normalise) : libelle obligatoire. Couvre :
#   - JP : "口座番号: 1234567" (avec ou sans tirets)
#   - SG / HK : "Account No. 0011-4422-8814-7841"
#   - CN : "账号" + chiffres / "银行账号"
# Le pattern est restrictif : libelle bancaire explicite + au moins
# 8 chiffres (separateurs admis). Sans cela un n° de bon de commande
# matcherait a tort.
_BANK_ACCOUNT_PATTERN = re.compile(
    r"(?i)(?:口座番号|銀行口座|振込先口座"
    r"|账[号户]|银行账[号户]|开户行账[号户]"
    r"|Account\s*(?:No\.?|Number)?|A/?C\s*No\.?"
    r"|N[°o]\s*(?:de\s+)?compte)"
    r"[\s:：\-]{0,5}"
    # Valeur : commence par chiffre OU lettre majuscule, accepte
    # melange chiffres + lettres + tirets + espaces (formats KR-...
    # /SWIFT-like, JP, SG). Doit finir par un chiffre. Contrainte sur
    # le nombre de chiffres totaux verifiee apres match.
    r"(?P<value>[A-Z0-9][A-Z0-9\s\-]{6,30}\d)"
)


def recognize_bank_account_by_context(text: str, score: float = 0.85) -> list[Span]:
    """Numero de compte bancaire precede d'un libelle explicite
    (口座番号, 账号, Account No., N° de compte, etc.). Couvre les pays
    sans IBAN officiel (JP / CN / SG / HK / etc.) ou les comptes
    formates differemment.
    """
    spans: list[Span] = []
    for m in _BANK_ACCOUNT_PATTERN.finditer(text):
        start, end = m.span("value")
        value = m.group("value").strip()
        # Exiger au moins 8 chiffres parmi la valeur (apres strip des
        # separateurs) pour ecarter les chaines courtes.
        digit_count = sum(1 for c in value if c.isdigit())
        if digit_count < 8:
            continue
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=value,
                score=score,
                recognizer="BankAccountByContextRegex",
            )
        )
    return spans


def recognize_jp_mai_number(text: str, score: float = 0.95) -> list[Span]:
    """My Number japonais (マイナンバー / 個人番号) - PII critique."""
    spans: list[Span] = []
    for m in _JP_MAI_NUMBER_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="JpMaiNumberRegex",
            )
        )
    return spans


def recognize_jp_hojin_bango(text: str, score: float = 0.9) -> list[Span]:
    """Hojin Bango (法人番号) - identifiant entreprise japonais."""
    spans: list[Span] = []
    for m in _JP_HOJIN_BANGO_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="JpHojinBangoRegex",
            )
        )
    return spans


def recognize_jp_driver_licence(text: str, score: float = 0.9) -> list[Span]:
    """Permis de conduire japonais (運転免許証番号)."""
    spans: list[Span] = []
    for m in _JP_DRIVER_LICENCE_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="JpDriverLicenceRegex",
            )
        )
    return spans


def recognize_jp_passport(text: str, score: float = 0.9) -> list[Span]:
    """Passeport japonais (2 lettres + 7 chiffres)."""
    spans: list[Span] = []
    for m in _JP_PASSPORT_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="JpPassportRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# JP - Carte d'assurance sante (健康保険証番号)
# ---------------------------------------------------------------------
# Libelle "健康保険証番号" ou "保険証番号" suivi d'un numero variable
# (souvent 8 chiffres + 1-3 chiffres separes par tiret). PII medicale
# sensible RGPD/APPI : permet de remonter a la personne via la securite
# sociale japonaise. On capture par libelle contextuel ferme : tolere
# repetition du libelle ("健康保険証番号：健康保険証番号 12345678-901")
# et accepte separateurs varies. Au moins 6 chiffres exiges.
_JP_HEALTH_INSURANCE_PATTERN = re.compile(
    r"(?:健康保険証番号|保険証番号|健康保険番号)"
    r"[^\d\n]{0,30}?"
    r"(?P<value>\d{4,12}[\s\-]?\d{1,8})"
)


def recognize_jp_health_insurance(text: str, score: float = 0.9) -> list[Span]:
    """Numero de carte d'assurance maladie japonaise."""
    spans: list[Span] = []
    for m in _JP_HEALTH_INSURANCE_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="JpHealthInsuranceRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# JP - Numero de registre commercial (法人登記番号 / 商業登記番号)
# ---------------------------------------------------------------------
# Different du My Number entreprise (法人番号 13 chiffres) : c'est le
# numero d'inscription au registre commercial, format XXXXXX-XXXXXXX
# (6 + 7 chiffres, separe par tiret). Identifiant unique d'entreprise.
# Capture par libelle contextuel.
_JP_TOUKI_BANGOU_PATTERN = re.compile(
    r"(?:法人登記番号|商業登記番号|会社法人等番号|登記番号)"
    r"[^\d\n]{0,20}?"
    r"(?P<value>\d{4}\-\d{2}\-\d{6}|\d{6}\-\d{6,7}|\d{12,13})"
)


def recognize_jp_touki_bangou(text: str, score: float = 0.9) -> list[Span]:
    """Numero de registre commercial japonais (法人登記番号)."""
    spans: list[Span] = []
    for m in _JP_TOUKI_BANGOU_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="JpToukiBangouRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# KR - Numero d'enregistrement entreprise (사업자등록번호)
# ---------------------------------------------------------------------
# Equivalent SIRET/VAT coreen, 10 chiffres au format XXX-XX-XXXXX.
# Identifiant unique d'entreprise. Capture par libelle contextuel.
_KR_BUSINESS_REG_PATTERN = re.compile(
    r"(?:사업자등록번호|법인등록번호)"
    r"[^\d\n]{0,20}?"
    r"(?P<value>\d{3}\-\d{2}\-\d{5}|\d{6}\-\d{7})"
)


def recognize_kr_business_registration(text: str, score: float = 0.9) -> list[Span]:
    """Numero d'enregistrement entreprise/personne morale coreen."""
    spans: list[Span] = []
    for m in _KR_BUSINESS_REG_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="KrBusinessRegistrationRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# KR - Numero d'enregistrement resident (주민등록번호 / RRN)
# ---------------------------------------------------------------------
# Equivalent My Number coreen, PII personnelle critique. Format
# YYMMDD-NNNNNNN (6 + 7 chiffres). Le 7e chiffre indique sexe/siecle.
# Detection autonome par format ferme + libelle.
_KR_RRN_PATTERN = re.compile(
    r"(?:주민등록번호|RRN)"
    r"[^\d\n]{0,20}?"
    r"(?P<value>\d{6}\-[1-8]\d{6})"
)


def recognize_kr_rrn(text: str, score: float = 0.95) -> list[Span]:
    """Numero d'enregistrement resident coreen (PII critique)."""
    spans: list[Span] = []
    for m in _KR_RRN_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="KrRrnRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# IT - Codice Fiscale (CF) - identifiant fiscal personnel italien
# ---------------------------------------------------------------------
# Format strict 16 caracteres : 6 lettres (nom-prenom) + 2 chiffres
# (annee) + 1 lettre (mois) + 2 chiffres (jour, +40 si femme) + 1 lettre
# + 3 chiffres (commune) + 1 lettre de controle. Tres specifique, faux
# positifs rares. PII RGPD critique (equivalent INSEE).
# Detection autonome par format ferme - libelle optionnel.
_IT_CF_PATTERN = re.compile(
    r"\b(?P<value>[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])\b"
)


def recognize_it_codice_fiscale(text: str, score: float = 0.95) -> list[Span]:
    """Codice Fiscale italien (CF) - PII personnelle critique."""
    spans: list[Span] = []
    for m in _IT_CF_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="ItCodiceFiscaleRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# IT - Codice SDI (Sistema di Interscambio) / Codice Univoco
# ---------------------------------------------------------------------
# Identifiant a 7 caracteres alphanumeriques attribue par l'Agenzia
# delle Entrate pour la facturation electronique italienne. PII
# commerciale (lie a entreprise). Capture par libelle contextuel
# ferme pour eviter les faux positifs sur tout token de 7 chars.
_IT_SDI_PATTERN = re.compile(
    r"(?i)(?:Codice\s+(?:SDI|SdI|destinatario|univoco)"
    r"|SDI|SdI)"
    r"\s*[:\-]?\s*"
    r"(?P<value>[A-Z0-9]{7})\b"
)


def recognize_it_codice_sdi(text: str, score: float = 0.9) -> list[Span]:
    """Codice SDI italien (facturation electronique)."""
    spans: list[Span] = []
    for m in _IT_SDI_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="ItCodiceSdiRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# IT - Matricules registres officiels (Albo, INPS Artigiani, INAIL, EORI)
# ---------------------------------------------------------------------
# Les entreprises italiennes sont referencees dans plusieurs registres
# qui encapsulent le P.IVA dans une matricule structuree :
#   - Albo Nazionale Gestori Ambientali : "AN-44-08412780633"
#   - INPS Artigiani : "NA-44-08412780633"
#   - INAIL : "44.087.812-CT"
#   - EORI italien : "ITIT12345670966" (IT pays + IT + 11 chiffres)
# Le P.IVA principal est deja capture par fiscal_labeled, mais ses
# reoccurrences encapsulees passent au travers. Capture par libelle
# contextuel ferme.
_IT_REGULATORY_PATTERN = re.compile(
    r"(?i)(?:Albo(?:\s+Nazionale)?(?:\s+Gestori\s+Ambientali)?"
    r"|INPS(?:\s+(?:Artigiani|Gestione|Commercianti))?"
    r"|INAIL"
    r"|Iscrizione(?:\s+(?:al\s+)?(?:Albo|INPS|INAIL|Registro))?"
    r"|matricola"
    r"|EORI(?:\s+IT)?)"
    # On tolere un saut de ligne dans le separateur car les libelles
    # Albo/INPS/INAIL/matricola peuvent etre coupes en fin de ligne
    # ("n. matricola\nAN-44-08412780633"). Le \n ne peut pas
    # introduire de chiffre intempestif vu la borne 30 chars.
    r"[^\d]{0,30}?"
    r"(?P<value>"
    r"IT\d{11}"                          # EORI brut italien
    r"|[A-Z]{2}\-?\d{2,3}\-\d{6,12}"     # AN-44-08412780633
    r"|\d{2,3}\.\d{3}\.\d{3}\-?[A-Z]{0,2}" # 44.087.812-CT
    r"|\d{10,13}"                         # 11 chiffres bruts
    r")"
)


def recognize_it_regulatory_number(text: str, score: float = 0.9) -> list[Span]:
    """Matricules registres officiels italiens (Albo, INPS, INAIL, EORI)."""
    spans: list[Span] = []
    for m in _IT_REGULATORY_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="ItRegulatoryRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# IT - Tessera Sanitaria (carte d'assurance maladie italienne)
# ---------------------------------------------------------------------
# Format : 20 chiffres (ou 20 + "/" + 2). PII medicale RGPD critique.
# Libelle contextuel ferme.
_IT_TESSERA_PATTERN = re.compile(
    r"(?i)Tessera\s+Sanitaria"
    r"[^\d\n]{0,20}?"
    r"(?P<value>\d{10,20}(?:[/\-]\d{1,3})?)"
)


def recognize_it_tessera_sanitaria(text: str, score: float = 0.9) -> list[Span]:
    """Tessera Sanitaria italienne (carte d'assurance maladie)."""
    spans: list[Span] = []
    for m in _IT_TESSERA_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="ItTesseraSanitariaRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# BG - Bulgarie (alphabet cyrillique)
# ---------------------------------------------------------------------
# ЕГН (Единен граждански номер) = identifiant personnel bulgare,
# 10 chiffres. Format : YYMMDDXXXX avec controle algorithmique.
# PII personnelle critique RGPD (equivalent NIR/PESEL/RC).
# Libelle obligatoire (sans libelle, ambiguite avec ЕИК / autres ID).
_BG_EGN_PATTERN = re.compile(
    r"(?:ЕГН|EGN|Единен\s+граждански\s+номер)"
    r"[^\d]{0,20}?"
    r"(?P<value>\d{10})"
)


def recognize_bg_egn(text: str, score: float = 0.95) -> list[Span]:
    """ЕГН (Единен граждански номер) - identifiant personnel BG."""
    spans: list[Span] = []
    for m in _BG_EGN_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="BgEgnRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# BG - ЕИК / БУЛСТАТ : identifiant entreprise bulgare
# ---------------------------------------------------------------------
# 9 chiffres (entreprise principale) ou 13 chiffres (avec succursale).
# Equivalent SIRET / IČO. Libelle contextuel ferme.
_BG_EIK_PATTERN = re.compile(
    r"(?:ЕИК|EIK|БУЛСТАТ|BULSTAT"
    r"|Единен\s+идентификационен\s+код)"
    r"[^\d]{0,20}?"
    r"(?P<value>\d{9}(?:\d{4})?)"
)


def recognize_bg_eik(text: str, score: float = 0.9) -> list[Span]:
    """ЕИК/БУЛСТАТ - identifiant entreprise bulgare."""
    spans: list[Span] = []
    for m in _BG_EIK_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="BgEikRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# BG - ЛНЧ : Личен номер на чужденец (resident etranger)
# ---------------------------------------------------------------------
# 10 chiffres, equivalent NIE espagnol. PII personnelle critique.
_BG_LNCH_PATTERN = re.compile(
    r"(?:ЛНЧ|LNCH|Личен\s+номер\s+на\s+чужденец)"
    r"[^\d]{0,20}?"
    r"(?P<value>\d{10})"
)


def recognize_bg_lnch(text: str, score: float = 0.95) -> list[Span]:
    """ЛНЧ - numero personnel d'etranger bulgare."""
    spans: list[Span] = []
    for m in _BG_LNCH_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="BgLnchRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# BG - Лична карта (carte d'identite) / Паспорт
# ---------------------------------------------------------------------
# Carte d'identite bulgare : 9 chiffres. Passeport BG : 9 chiffres.
# Capture par libelle contextuel (sinon ambiguite avec ЕИК).
_BG_ID_CARD_PATTERN = re.compile(
    r"(?:Лична\s+карта"
    r"|карта\s+за\s+самоличност"
    r"|Паспорт"
    r"|Passport)"
    r"[^\d\n]{0,30}?"
    r"(?:№|N|No|номер|серия)?"
    r"\s*[:\-]?\s*"
    r"(?P<value>[A-Z]?\d{9}|\d{9})"
)


def recognize_bg_id_card(text: str, score: float = 0.9) -> list[Span]:
    """Carte d'identite / passeport bulgare."""
    spans: list[Span] = []
    for m in _BG_ID_CARD_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="BgIdCardRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# BG - НЗОК (Национална здравноосигурителна каса)
# ---------------------------------------------------------------------
# Numero d'assurance maladie bulgare. PII medicale critique RGPD.
_BG_HEALTH_INSURANCE_PATTERN = re.compile(
    r"(?:НЗОК|NZOK"
    r"|Здравна\s+книжка"
    r"|Здравноосигурителен\s+номер)"
    r"[^\d]{0,30}?"
    r"(?P<value>\d{8,12})"
)


def recognize_bg_health_insurance(text: str, score: float = 0.9) -> list[Span]:
    """НЗОК - numero d'assurance maladie bulgare."""
    spans: list[Span] = []
    for m in _BG_HEALTH_INSURANCE_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="BgHealthInsuranceRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# Republique tcheque / Slovaquie
# ---------------------------------------------------------------------
# RC (Rodne cislo) : numero d'identification personnel
# tcheque/slovaque, format JJMMYY/CCCC (9 ou 10 chiffres,
# avec ou sans slash). Equivalent du PESEL polonais ou du
# NIR francais. PII personnelle critique RGPD.
#   "Rodne cislo: 781104/1234"
#   "Rodne cislo (pro osobni ruceni): 691104/4477"  <- texte intermediaire
#   "RC: 7811041234"
_CZ_RC_PATTERN = re.compile(
    r"(?i)\b(?:Rodn[éeě]\s+[čc]íslo|R[ČC])"
    r"(?:[^0-9\n]{0,30})"
    r"(?P<value>\d{6}[\s/\-]?\d{3,4})"
)

# ICO (Identifikacni cislo osoby) : numero d'identification
# d'entreprise tcheque/slovaque, 8 chiffres. Equivalent du
# SIREN francais.
#   "ICO: 12345678"
_CZ_ICO_PATTERN = re.compile(
    r"(?i)\b(?:I[ČC]O|Identifika[čc]n[íi]\s+[čc]íslo(?:\s+osoby)?)"
    r"\s*[:\-]?\s*(?P<value>\d{8})"
)

# DIC (Danove identifikacni cislo) : numero fiscal tcheque/
# slovaque, format CZ/SK + 8-10 chiffres.
#   "DIC: CZ12345678", "DIC: SK1234567890"
_CZ_DIC_PATTERN = re.compile(
    r"(?i)\b(?:DI[ČC]|Da[ňn]ov[éeě]\s+identifika[čc]n[íi]\s+[čc]íslo)"
    r"\s*[:\-]?\s*(?P<value>(?:CZ|SK)\s?\d{8,10})"
)

# Numero d'OP (carte d'identite / obcansky prukaz) : 9 chiffres
# ou format alphanumerique. Tolere format "208 845 116" (groupes
# de 3) et le mot intermediaire "č." (cislo).
#   "Cislo OP: 123456789"
#   "Obcansky prukaz c. 208 845 116"
_CZ_OP_PATTERN = re.compile(
    r"(?i)\b(?:Ob[čc]ansk[éý]\s+pr[ůu]kaz|[ČC][íi]slo\s+OP|OP\s+[čc][íi]slo)"
    r"[\s:\-čc.íi]{0,15}?"
    r"(?P<value>\d{3}[\s\-]?\d{3}[\s\-]?\d{3}|[A-Z0-9]{6,12})"
)


# CSSZ (Ceska sprava socialniho zabezpeceni) : organisme de
# securite sociale tcheque. Format variable : "ev. č. RČ",
# reference "CSSZ-YYYY-XXXXXX-XXX", numero d'inscription
# employeur. On capture la valeur qui suit le libelle.
_CZ_CSSZ_PATTERN = re.compile(
    r"(?i)\b(?:[ČC]SSZ(?:\s+ev\.?\s*[čc]\.?)?|Eviden[čc]n[íi]\s+[čc]\.?\s*[ČC]SSZ)"
    r"[\s:\-\.]{0,15}?"
    r"(?P<value>"
    # "2026-118744-852" ou similaire (annee + suite + cle)
    r"\d{4}[\-\s]\d{4,8}[\-\s]\d{2,4}"
    # "691104/4477" (RC format reused)
    r"|\d{6}[\s/\-]\d{3,4}"
    # 8-12 chiffres colles ou avec separateurs
    r"|\d{2}[\s\-]?\d{6,12}"
    r"|\d{8,14}"
    r")"
)


def recognize_cz_cssz(text: str, score: float = 0.9) -> list[Span]:
    """Numero d'inscription CSSZ (securite sociale tcheque)."""
    spans: list[Span] = []
    for m in _CZ_CSSZ_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CzCsszRegex",
            )
        )
    return spans


def recognize_cz_rodne_cislo(text: str, score: float = 0.95) -> list[Span]:
    """RC tcheque/slovaque (Rodne cislo) - PII personnelle critique."""
    spans: list[Span] = []
    for m in _CZ_RC_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CzRodneCisloRegex",
            )
        )
    return spans


def recognize_cz_ico(text: str, score: float = 0.9) -> list[Span]:
    """ICO tcheque/slovaque (identifiant entreprise, 8 chiffres)."""
    spans: list[Span] = []
    for m in _CZ_ICO_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CzIcoRegex",
            )
        )
    return spans


def recognize_cz_dic(text: str, score: float = 0.9) -> list[Span]:
    """DIC tcheque/slovaque (numero fiscal, prefixe CZ/SK + chiffres)."""
    spans: list[Span] = []
    for m in _CZ_DIC_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="CzDicRegex",
            )
        )
    return spans


def recognize_cz_op(text: str, score: float = 0.85) -> list[Span]:
    """Numero d'Obcansky prukaz tcheque (carte d'identite)."""
    spans: list[Span] = []
    for m in _CZ_OP_PATTERN.finditer(text):
        start, end = m.span("value")
        value = m.group("value")
        # Exiger au moins un chiffre.
        if not any(c.isdigit() for c in value):
            continue
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=value,
                score=score,
                recognizer="CzOpRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# Turquie
# ---------------------------------------------------------------------
# TCKN (T.C. Kimlik Numarasi) : numero d'identification national
# turc, 11 chiffres. PII personnelle critique. Libelles courants :
# "T.C. Kimlik No", "TC Kimlik No", "TCKN", "Kimlik Numarasi".
_TR_TCKN_PATTERN = re.compile(
    r"(?i)\b(?:T\.?C\.?\s*Kimlik\s*N(?:o|umaras[ıi])?|TCKN|Kimlik\s+N(?:o|umaras[ıi]))"
    r"\s*[:\-]?\s*(?P<value>\d{11})"
)

# VKN (Vergi Kimlik Numarasi) : numero fiscal, 10 chiffres
# (entreprises + personnes physiques). Libelles : "Vergi No",
# "VKN", "Vergi Kimlik No", "Vergi Numarasi".
_TR_VKN_PATTERN = re.compile(
    r"(?i)\b(?:VKN|Vergi\s+(?:Kimlik\s+)?N(?:o|umaras[ıi]))"
    r"\s*[:\-]?\s*(?P<value>\d{10})"
)

# SGK (Sosyal Guvenlik Kurumu - securite sociale) : numero
# d'assure. Plusieurs formats observes :
#   - 10-14 chiffres consecutifs
#   - 15 chiffres groupes FR-like avec "/" final : "1 78 04 88 044 022 / 47"
#   - Format alphanumerique de reference : "SGK-2026-118744-852"
#   - N° employeur format court : "32-8118-44"
_TR_SGK_PATTERN = re.compile(
    r"(?i)\b(?:SGK(?:\s+(?:i[şs]veren\s+)?N(?:o|umaras[ıi]))?"
    r"|Sosyal\s+G[üu]venlik(?:\s+(?:i[şs]veren\s+)?N(?:o|umaras[ıi]))?)"
    r"\s*[\-:]?\s*"
    r"(?P<value>"
    # Format complet 15 chiffres avec separateurs et cle "/ XX"
    r"\d{1,2}\s\d{2}\s\d{2}\s\d{2}\s\d{3}\s\d{3}\s*/?\s*\d{2}"
    # Format reference alphanumerique "2026-XXXXXX-XXX"
    r"|\d{4}[\-\s]\d{4,8}[\-\s]\d{2,4}"
    # Format court "32-8118-44"
    r"|\d{2}[\-\s]\d{4,6}[\-\s]\d{2,4}"
    # Format colle 10-14 chiffres
    r"|\d{10,14}"
    r")"
)

# Sicil No (Ticaret Sicil Numarası) : numero d'inscription au
# registre du commerce. Couvre aussi MERSIS / MERSİS (Merkezi Sicil
# Kayıt Sistemi), 16 chiffres - identifiant central d'entreprise.
_TR_SICIL_PATTERN = re.compile(
    r"(?i)\b(?:Ticaret\s+Sicil\s+N(?:o|umaras[ıi])?"
    r"|Sicil\s+N(?:o|umaras[ıi])"
    r"|MERS[İI]S(?:\s+N(?:o|umaras[ıi]))?)"
    r"\s*[:\-]?\s*(?P<value>\d{4,18})"
)


def recognize_tr_tckn(text: str, score: float = 0.95) -> list[Span]:
    """T.C. Kimlik Numarasi turc (TCKN, 11 chiffres) - PII critique."""
    spans: list[Span] = []
    for m in _TR_TCKN_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="TrTcknRegex",
            )
        )
    return spans


def recognize_tr_vkn(text: str, score: float = 0.9) -> list[Span]:
    """VKN turc (Vergi Kimlik Numarasi, 10 chiffres)."""
    spans: list[Span] = []
    for m in _TR_VKN_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="TrVknRegex",
            )
        )
    return spans


def recognize_tr_sgk(text: str, score: float = 0.9) -> list[Span]:
    """SGK turc (Sosyal Guvenlik Kurumu, securite sociale)."""
    spans: list[Span] = []
    for m in _TR_SGK_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="TrSgkRegex",
            )
        )
    return spans


def recognize_tr_sicil(text: str, score: float = 0.85) -> list[Span]:
    """Ticaret Sicil Numarasi turc (registre du commerce)."""
    spans: list[Span] = []
    for m in _TR_SICIL_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="TrSicilRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# Pologne
# ---------------------------------------------------------------------
# NIP (Numer Identyfikacji Podatkowej) : 10 chiffres. Format souvent
# groupe en "XXX-XXX-XX-XX" ou "XXX-XX-XX-XXX" ou colle.
_PL_NIP_PATTERN = re.compile(
    # Tolere jusqu'a 30 caracteres non-chiffres entre le libelle NIP et
    # la valeur (cas "NIP osoby fizycznej PL ..." ou "NIP UE: PL ...").
    # Sans cela un autre recognizer (PhoneEsRegex) hapte les 10 chiffres
    # en telephone par erreur.
    r"(?i)\bNIP\b(?:[^0-9\n]{0,30})"
    r"(?P<value>(?:PL\s?)?\d{3}[\s\-]?\d{2,3}[\s\-]?\d{2,3}[\s\-]?\d{2,3})"
)

# REGON (Rejestr Gospodarki Narodowej) : 9 ou 14 chiffres.
_PL_REGON_PATTERN = re.compile(
    r"(?i)\bREGON\s*[:\-]?\s*"
    r"(?P<value>\d{9}(?:\d{5})?)"
)

# KRS (Krajowy Rejestr Sadowy) : 10 chiffres precedes de zeros.
_PL_KRS_PATTERN = re.compile(
    r"(?i)\bKRS\s*[:\-]?\s*"
    r"(?P<value>\d{10})"
)

# PESEL (Powszechny Elektroniczny System Ewidencji Ludnosci) :
# 11 chiffres. PII personnelle critique. Toujours precede du libelle.
_PL_PESEL_PATTERN = re.compile(
    r"(?i)\bPESEL\s*[:\-]?\s*"
    r"(?P<value>\d{11})"
)


def recognize_pl_nip(text: str, score: float = 0.95) -> list[Span]:
    """NIP PL (Numer Identyfikacji Podatkowej)."""
    spans: list[Span] = []
    for m in _PL_NIP_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="PlNipRegex",
            )
        )
    return spans


def recognize_pl_regon(text: str, score: float = 0.9) -> list[Span]:
    """REGON PL (Rejestr Gospodarki Narodowej)."""
    spans: list[Span] = []
    for m in _PL_REGON_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="PlRegonRegex",
            )
        )
    return spans


def recognize_pl_krs(text: str, score: float = 0.9) -> list[Span]:
    """KRS PL (Krajowy Rejestr Sadowy)."""
    spans: list[Span] = []
    for m in _PL_KRS_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="PlKrsRegex",
            )
        )
    return spans


def recognize_pl_pesel(text: str, score: float = 0.95) -> list[Span]:
    """PESEL PL (numero d'identification personnelle, 11 chiffres)."""
    spans: list[Span] = []
    for m in _PL_PESEL_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="PlPeselRegex",
            )
        )
    return spans


# ---------------------------------------------------------------------
# Portugal
# ---------------------------------------------------------------------
# NIF / NIPC PT : 9 chiffres seuls (sans prefixe lettre, contrairement
# au CIF ES). Toujours precede du libelle NIF / NIPC / Contribuinte
# / IVA intracom. PT.
_PT_NIF_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?P<value>\d{3}[\s\-]?\d{3}[\s\-]?\d{3})(?![A-Z0-9])"
)
_PT_NIF_LABEL_CONTEXT = re.compile(
    r"(?i)\b(?:NIPC|NIF|n[úu]mero\s+(?:de\s+)?contribuinte|contribuinte"
    r"|IVA\s+intracom\.?\s*PT|IVA\s+PT)\b"
)

# Cartao de Cidadao portugais : 9 chiffres (groupes 3-3-3) + 2 lettres
# + 1 chiffre (controle). Format observe : "200 842 587 ZZ4".
# Tolere les espaces internes entre groupes.
_PT_CC_PATTERN = re.compile(
    r"(?i)(?:cart[ãa]o\s+(?:de\s+)?cidad[ãa]o(?:\s*\(CC\))?|\bCC\b)"
    r"[\s\-:nº.º]{0,15}?"
    r"(?P<value>\d{3}\s?\d{3}\s?\d{3}\s?[A-Z]{2}\s?\d?)"
)

# NISS Portugal (numero de identificacao da Seguranca Social).
# Format officiel : 11 chiffres. Le cas fictif ici fait 17 chiffres
# groupes "117 8048800 4422 047". On accepte 11-17 chiffres consecutifs.
_PT_NISS_PATTERN = re.compile(
    r"(?i)(?:NISS|n[úu]mero\s+(?:da\s+)?seguran[çc]a\s+social"
    r"|seguran[çc]a\s+social\s*n[úu]mero|seguran[çc]a\s+social)"
    r"[\s\-:n°.º]{0,15}?"
    r"(?P<value>\d{2,3}(?:[\s\-]?\d){9,15})"
)


def recognize_pt_nif(text: str, score: float = 0.9) -> list[Span]:
    """NIF / NIPC PT (9 chiffres precedes du libelle NIF / NIPC /
    Contribuinte / IVA intracom. PT)."""
    spans: list[Span] = []
    for m in _PT_NIF_PATTERN.finditer(text):
        window = text[max(0, m.start() - 30): m.start()]
        if not _PT_NIF_LABEL_CONTEXT.search(window):
            continue
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="PtNifRegex",
            )
        )
    return spans


def recognize_pt_cc(text: str, score: float = 0.9) -> list[Span]:
    """Cartao de Cidadao portugais (CC) precede du libelle."""
    spans: list[Span] = []
    for m in _PT_CC_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="PtCcRegex",
            )
        )
    return spans


def recognize_pt_niss(text: str, score: float = 0.9) -> list[Span]:
    """NISS Portugal (numero da Seguranca Social, 11+ chiffres)."""
    spans: list[Span] = []
    for m in _PT_NISS_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="PtNissRegex",
            )
        )
    return spans


def recognize_es_ccc(text: str, score: float = 0.9) -> list[Span]:
    """Numero de Cuenta de Cotizacion espagnole (CCC) - 12 chiffres
    precedes du libelle 'Cuenta cotizacion' ou 'Reg. Esp. Autonomos'.
    """
    spans: list[Span] = []
    for m in _ES_CCC_PATTERN.finditer(text):
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="EsCccRegex",
            )
        )
    return spans


def recognize_es_cif(text: str, score: float = 0.9) -> list[Span]:
    """CIF / NIF entreprise espagnol ([ABCDEFGHJNPQRSUVW] + 8 chiffres).

    Sans libelle explicite, le pattern serait trop permissif (un code
    "B95187721" pourrait etre une reference). On exige donc soit le
    libelle CIF/NIF/C.I.F a proximite (40 chars avant), soit un libelle
    "IVA intracom" / "VAT" qui precede souvent ce numero.
    """
    # Contexte plus large : "CIF", "NIF", "IVA" (sans suffixe "intracom"
    # car frequent en ES de voir "IVA ES B...."), "VAT".
    label_ctx = re.compile(
        r"(?i)\b(?:CIF|NIF|C\.I\.F|IVA|VAT|N\.?I\.?F)\b"
    )
    spans: list[Span] = []
    for m in _ES_CIF_PATTERN.finditer(text):
        window = text[max(0, m.start() - 40): m.start()]
        if not label_ctx.search(window):
            continue
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="NATIONAL_ID",
                text=m.group("value"),
                score=score,
                recognizer="EsCifRegex",
            )
        )
    return spans


def recognize_national_id(text: str, score: float = 0.85) -> list[Span]:
    """Detecte les numeros d'identite nationaux.

    Le Span couvre uniquement l'identifiant ; le libelle reste en clair
    pour la lisibilite du document anonymise. Sans contexte de libelle,
    on ne produit aucun span (eviter les faux positifs sur des codes
    internes alphanumeriques courts).

    Args:
        text: texte source.
        score: confiance du recognizer.

    Returns:
        Liste de Spans `NATIONAL_ID`.
    """
    spans: list[Span] = []
    for m in _NATIONAL_ID_PATTERN.finditer(text):
        start, end = m.span("id")
        value = m.group("id")
        # Filtre : l'identifiant doit contenir au moins UN chiffre (un
        # mot purement alphabetique apres "carte d'identite : " est
        # probablement un nom ou une mention "non communiquee").
        if not any(c.isdigit() for c in value):
            continue
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="NATIONAL_ID",
                text=value,
                score=score,
                recognizer="NationalIdRegex",
            )
        )
    return spans
