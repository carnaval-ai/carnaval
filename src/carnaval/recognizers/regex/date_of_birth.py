# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer pour les dates de naissance.

PII sensible RGPD : une date complete (jour + mois + annee) accolee a un
libelle de naissance permet de re-identifier une personne meme lorsque
son nom est masque. Doit etre masquee systematiquement.

Strategie : on detecte le LIBELLE (ne / nee / born / geboren / date de
naissance / etc.) puis on capture la date qui suit. Seule la date est
remontee comme Span ; le libelle reste en clair pour la lisibilite du
document anonymise.

Couvre :
- FR : "Né le 04/11/1969", "née le 02-03-2004", "Date de naissance : 17/09/1982"
- EN : "born on 1969-11-04", "Date of birth: 04/11/1969"
- DE : "geboren am 04.11.1969", "Geburtsdatum: 04.11.1969"

Formats de date geres :
- JJ/MM/AAAA, JJ-MM-AAAA, JJ.MM.AAAA (FR/DE)
- AAAA-MM-JJ (ISO 8601, anglais)
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Pattern de libelle "naissance" multilingue. Le mot-cle est suivi
# d'un separateur optionnel (le / la / on / am / am / : / des deux-points)
# puis de la date. On admet jusqu'a 15 caracteres entre le libelle et le
# debut de la date pour absorber "Né le ", "Date de naissance : ", etc.
_LABEL = (
    r"(?P<label>"
    # FR : ne / nee / nees (accents tolerants)
    r"n[ée]+s?\s+le"
    r"|date\s+de\s+naissance"
    # EN : born on, date of birth, DOB (abbreviation tres frequente sur
    # les documents UK / EI / sole trader)
    r"|born(?:\s+on)?"
    r"|date\s+of\s+birth"
    r"|DOB"
    # DE : geboren am, Geburtsdatum
    r"|geboren\s+am"
    r"|geburtsdatum"
    # ES : nacido/nacida el, fecha de nacimiento
    r"|nacid[oa]s?\s+el"
    r"|fecha\s+de\s+nacimiento"
    # IT : nato/nata il, data di nascita
    r"|nat[oa]s?\s+il"
    r"|data\s+di\s+nascita"
    # PT : nascido em / nascido a, data de nascimento
    r"|nascid[oa]s?\s+(?:em|a)"
    r"|data\s+de\s+nascimento"
    # PL : ur. (abreviation), urodzony/urodzona, data urodzenia
    r"|ur\.(?=\s+\d)"
    r"|urodzon[ya]"
    r"|data\s+urodzenia"
    # TR : dogum tarihi (date de naissance), dogdu/dogmus (ne),
    # ou libelle court "Doğum:" (sans "tarihi"). `g/G` couvre aussi ğ
    # apres deaccent ; en regex `IGNORECASE` ne gere PAS l'equivalence
    # accent/non-accent, on liste les variantes avec ğ et avec g.
    r"|do[ğg]um\s+tarihi"
    r"|do[ğg]um(?=\s*[:：]?\s*\d)"
    r"|do[ğg]du"
    r"|do[ğg]mu[şs]"
    # CZ/SK : narozen[ý/á/é], datum narozeni, nar. (abreviation).
    # On liste les variantes avec/sans accents et avec/sans caron.
    r"|narozen[yýáaéeoóée]?"
    r"|datum\s+narozen[íi]"
    r"|nar\.(?=\s+\d)"
    # CN : 出生日期 / 出生年月日 / 出生 (date suivante au format
    # YYYY/MM/DD ou YYYY-MM-DD). 出生 seul ambigu, on exige
    # 出生 immediatement suivi de chiffres ou de l'un des suffixes.
    r"|出生日期"
    r"|出生年月日"
    r"|出生(?=\s*[:：]?\s*\d)"
    # JP : 生年月日 (date de naissance complete). Format souvent
    # YYYY年MM月DD日 mais aussi YYYY/MM/DD.
    r"|生年月日"
    # BG : Дата на раждане / Роден / Родена / Родени.
    # Caracteres cyrilliques (pas affectes par IGNORECASE qui ne
    # gere que latin ; on liste les variantes Maj/min explicitement).
    r"|[Дд]ата\s+на\s+раждане"
    r"|[Рр]оден[ао]?(?=\s*(?:на|в|\d|:))"
    r")"
)

# Separateur entre libelle et date.
# Tolere jusqu'a 50 caracteres entre le libelle et la date : couvre les
# variantes "Date de naissance declaree pour assurance dommages : ...",
# "Date de naissance du gerant declaree : ...", etc. Le contenu absorbe
# ne doit pas contenir de chiffre (pour ne pas matcher la mauvaise date
# si plusieurs dates voisinent) ni de saut de ligne (sinon on traverse
# tout le paragraphe).
_SEP = r"[^\d\n]{0,50}"

# Date au format jour-mois-annee (FR/DE) ou annee-mois-jour (ISO/EN).
# Tolere un espace optionnel apres chaque separateur : format "JJ. MM.
# AAAA" est standard en CZ/SK ("11. 04. 1978").
_DATE_DMY = r"(?P<dmy>\d{1,2}[/.\-]\s?\d{1,2}[/.\-]\s?\d{2,4})"
_DATE_YMD = r"(?P<ymd>\d{4}[/.\-]\s?\d{1,2}[/.\-]\s?\d{1,2})"
# Format CJK : "1969年04月11日" (annee-mois-jour avec ideogrammes).
_DATE_CJK = r"(?P<cjk>\d{4}年\d{1,2}月\d{1,2}日)"

# Pattern complet : libelle + sep + date (un format ou l'autre).
_DOB_PATTERN = re.compile(
    rf"{_LABEL}{_SEP}(?:{_DATE_DMY}|{_DATE_YMD}|{_DATE_CJK})",
    re.IGNORECASE,
)

# Pattern POSTFIX : date IMMEDIATEMENT SUIVIE d'un libelle "ne".
# Langues agglutinantes / suffixees (turc surtout) construisent la
# qualification apres la valeur :
#   "22/06/1961 Smolensk, RU doğumlu - 04/12/1994'te ..."
# La date est alors precedee de "(" + lieu et suivie par "doğumlu".
# On capture la date qui precede de PRES (jusqu'a 50 chars) un libelle
# suffixe.
_DATE_BEFORE_LABEL_PATTERN = re.compile(
    r"(?P<dmy>"
    # Date DMY (FR/DE/CZ/SK avec separateurs varies)
    r"\d{1,2}[/.\-]\s?\d{1,2}[/.\-]\s?\d{2,4}"
    # Date CJK "1969年04月11日"
    r"|\d{4}年\d{1,2}月\d{1,2}日"
    r")"
    r"[^\d\n]{0,50}?"
    # Libelles en suffixe (langues a syntaxe agglutinante ou
    # ordre inverse) :
    # - TR : doğumlu / dogumlu
    # - CN : 生于 / 生於 (ne a) - tres specifique, faux positifs nuls
    r"(?:do[ğg]umlu|生[于於])",
    re.IGNORECASE,
)


def recognize_date_of_birth(text: str, score: float = 0.9) -> list[Span]:
    """Detecte les dates de naissance.

    Le Span couvre uniquement la date (pas le libelle "Né le"). C'est
    suffisant pour empecher la re-identification : connaitre "Né le"
    sans date est inoffensif, tandis que la date seule annonce par le
    libelle est la donnee sensible.

    Args:
        text: texte source.
        score: confiance du recognizer.

    Returns:
        Liste de Spans `DATE_OF_BIRTH`.
    """
    spans: list[Span] = []
    for m in _DOB_PATTERN.finditer(text):
        # On recupere le groupe de date qui a matche (DMY, YMD ou CJK).
        date_text = m.group("dmy") or m.group("ymd") or m.group("cjk")
        if not date_text:
            continue
        # La position du span = position de la date capturee, pas du
        # libelle. On utilise les bornes du groupe nomme correspondant.
        if m.group("dmy"):
            start, end = m.span("dmy")
        elif m.group("ymd"):
            start, end = m.span("ymd")
        else:
            start, end = m.span("cjk")
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="DATE_OF_BIRTH",
                text=date_text,
                score=score,
                recognizer="DateOfBirthRegex",
            )
        )
    # Pattern postfix (TR : "JJ/MM/AAAA ... doğumlu").
    seen = {(s.start, s.end) for s in spans}
    for m in _DATE_BEFORE_LABEL_PATTERN.finditer(text):
        start, end = m.span("dmy")
        if (start, end) in seen:
            continue
        spans.append(
            Span(
                start=start,
                end=end,
                entity_type="DATE_OF_BIRTH",
                text=m.group("dmy"),
                score=score,
                recognizer="DateOfBirthRegex",
            )
        )
    return spans
