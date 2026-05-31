# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Detection du corps de tableau d'un document commercial.

Un accuse de reception comporte un tableau de postes (references, designations,
quantites, prix, montants) encadre par une ligne d'en-tete de colonnes et une
cascade de lignes de total. Ce corps ne contient aucune donnee personnelle :
le masquer nuit a la lecture du document. Or des references articles, des codes
douaniers ou des montants y ressemblent a des telephones ou des numeros fiscaux
et sont masques a tort.

Ce module repere les lignes du corps de tableau pour qu'aucun recognizer n'y
applique de masquage. Il raisonne LIGNE PAR LIGNE (et non par intervalle
continu) : une ligne d'adresse, un nom ou un numero fiscal intercales dans le
tableau - frequent avec une extraction PDF multi-pages qui desordonne les blocs
- conservent le masquage normal.

Strategie :
    1. Borne haute : une ligne d'en-tete de tableau = forte densite de libelles
       de colonne issus du lexique metier (>= 4 termes, >= 45% des mots).
    2. Borne basse : fin de la cascade de lignes de total ; garde-fou sur un
       marqueur non ambigu de pied de page rencontre avant toute cascade.
    3. Entre les bornes, une ligne est protegee SAUF si c'est une ligne
       d'exception : email/URL, numero de TVA formate, ou absence de tout
       signal tabulaire (prix, code, quantite) - signe d'une ligne d'adresse
       ou de prose.
"""

from __future__ import annotations

import re

from carnaval.core.allow_list import _collect_entries
from carnaval.core.span import Span

# Depliage accents -> ASCII, longueur preservee (cf. allow_list).
_DEACCENT = str.maketrans(
    "àâäáãåèéêëìíîïòóôöõùúûüýÿçñ"
    "ąćęłńóśźż"
    "şğı"                                   # turc minuscules
    "ěščřžťďňů",                            # tcheque/slovaque minuscules
    "aaaaaaeeeeiiiiooooouuuuyycn"
    "acelnoszz"
    "sgi"
    "escrztdnu",
)


def _norm(text: str) -> str:
    """Minuscule + accents deplies."""
    return text.lower().translate(_DEACCENT)


# En-tete de tableau : seuils de densite de libelles de colonne.
_HEADER_MIN_TERMS = 4
_HEADER_MIN_RATIO = 0.45

# En-tete VERTICAL : extraction PyMuPDF par blocs separes (blocks-sorted)
# eclate frequemment chaque cellule d'en-tete sur sa propre ligne. Le
# detecteur "ligne dense" ne voit alors aucun en-tete car chaque ligne ne
# porte qu'1-3 mots. On detecte ce cas comme un CLUSTER de cellules courtes
# consecutives, chacune libellee.
_VERTICAL_MIN_CELLS = 4         # taille minimale du cluster
_VERTICAL_MAX_TOKENS = 3        # une cellule d'en-tete = libelle court

# Abreviations courantes d'en-tetes de colonne (multilingue). Volontairement
# hors de `business_lexicon` (apply_allow_list) : ces formes courtes sont
# trop ambigues pour proteger un span ailleurs ("no", "art", "pos"), mais
# tres discriminantes quand ELLES SE GROUPENT sur une ligne d'en-tete.
_HEADER_ABBREVIATIONS = frozenset({
    "pos", "position",
    "réf", "ref", "art", "no", "n°", "n",
    "qte", "qté", "qty", "qtd", "qtite", "qtité",
    "anz", "mng",
    "uq", "um", "un",
    "mt", "pu", "p.u",
    "surcout", "surcoût",   # libelles HOFFMANN
})

# Termes de total (normalises) marquant la cascade de cloture. Multilingue.
_TOTAL_TERMS = frozenset({
    "total", "totaux", "somme", "montant", "a payer", "sous-total",
    "amount", "subtotal", "grand total", "total amount",
    "summe", "gesamt", "gesamtbetrag", "gesamtsumme", "endbetrag",
    "zwischensumme", "rechnungsbetrag",
    "importe", "totale", "valor total",
})

# Marqueurs non ambigus de pied de page (garde-fou de borne basse).
# Volontairement sans "tva", "taxe", "transport", "frais de port" : ces mots
# vivent aussi dans les lignes de total ou de poste du tableau.
_FOOTER_MARKERS = frozenset({
    "incoterm", "incoterms",
    "conditions generales", "conditions de paiement", "conditions de livraison",
    "reglement", "sanctions", "siret", "code ape", "code naf",
    "terms and conditions", "payment terms",
    "zahlungsbedingungen", "lieferbedingungen", "gerichtsstand",
})

# Signaux d'une ligne tabulaire (poste, total).
# Prix : un nombre a exactement 2 decimales (113,75 / 48,91). Le nombre doit
# etre ISOLE : ni precede ni suivi d'un autre chiffre ou separateur decimal.
# Sans ce garde-fou, "04.50.25.35.45" (telephone formate a points) etait
# matche fragment par fragment et la ligne du telephone passait pour une
# ligne tabulaire ; le telephone etait alors protege et fuyait au masquage.
_RX_PRICE = re.compile(r"(?<![.,\d])\d+[.,]\d{2}(?![.,\d])")
# Suite numerique longue : reference, code douanier, numero d'article.
_RX_LONGNUM = re.compile(r"\d{6,}")
# Quantite + unite.
_RX_QTY_UNIT = re.compile(
    r"\b\d{1,4}(?:[.,]\d{1,3})?[  ]?"
    r"(?:pce|pcs|pc|un|ea|st|stk|stck|stuck|pz|kg|m|ml|l|pr|box|set|m2|m3)\b",
    re.IGNORECASE,
)
# Numero de TVA intracom FR : signe une ligne d'identite, pas un poste.
_RX_VAT_FR = re.compile(r"\bFR\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b")
# Email / URL.
_RX_CONTACT = re.compile(r"@|www\.|https?://", re.IGNORECASE)


def _lines_with_offsets(text: str) -> list[tuple[int, int, str]]:
    """Decoupe le texte en (start, end, contenu) par ligne, offsets absolus."""
    out: list[tuple[int, int, str]] = []
    pos = 0
    for line in text.split("\n"):
        out.append((pos, pos + len(line), line))
        pos += len(line) + 1
    return out


def _contains_term(norm_line: str, terms: frozenset[str]) -> bool:
    """True si l'un des termes (deja normalises) apparait, borne par des mots."""
    for term in terms:
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", norm_line):
            return True
    return False


def _header_term_count(line: str, lex_simple: frozenset[str]) -> tuple[int, int]:
    """Renvoie (nb de libelles de colonne distincts, nb de mots de la ligne).

    Tolere le pluriel : un mot finissant par 's' compte si son singulier est
    dans le lexique (References -> reference, Delais -> delai).
    """
    tokens = [t.strip(".,;:()%-") for t in re.split(r"[ \t/]+", _norm(line))]
    tokens = [t for t in tokens if t]
    hits: set[str] = set()
    for tok in tokens:
        if tok in lex_simple:
            hits.add(tok)
        elif tok.endswith("s") and tok[:-1] in lex_simple:
            hits.add(tok[:-1])
    return len(hits), len(tokens)


def _is_header_line(line: str, lex_simple: frozenset[str]) -> bool:
    """True si la ligne est un en-tete de tableau (densite de libelles)."""
    n_terms, n_words = _header_term_count(line, lex_simple)
    if n_terms < _HEADER_MIN_TERMS or n_words == 0:
        return False
    return n_terms / n_words >= _HEADER_MIN_RATIO


def _is_vertical_header_cell(line: str, lex_header: frozenset[str]) -> bool:
    """True si la ligne ressemble a UNE cellule d'en-tete tabulaire isolee.

    Cas typique des extractions PyMuPDF par blocs : chaque libelle de
    colonne arrive sur sa propre ligne. Une cellule valide compte
    1 a `_VERTICAL_MAX_TOKENS` mots, dont au moins UN est un libelle de
    colonne (lexique metier ou abreviation reconnue).
    """
    s = line.strip()
    if not s:
        return False
    tokens = [t.strip(".,;:()%-") for t in re.split(r"[ \t/]+", _norm(s))]
    tokens = [t for t in tokens if t]
    if not tokens or len(tokens) > _VERTICAL_MAX_TOKENS:
        return False
    return any(
        t in lex_header or (t.endswith("s") and t[:-1] in lex_header)
        for t in tokens
    )


def _is_table_row_signal(line: str) -> bool:
    """True si la ligne porte un signal FORT de ligne de poste : prix decimal
    isole OU quantite avec unite explicite. Distinct de `_has_table_signal`
    qui accepte aussi un simple code long ou un numero, pour eviter de
    confondre un bloc d'adresse avec une vraie ligne de poste."""
    return bool(_RX_PRICE.search(line)) or bool(_RX_QTY_UNIT.search(line))


def _has_price_or_qty_within(
    lines: list[tuple[int, int, str]], start_idx: int, look_ahead: int
) -> bool:
    """True si au moins une ligne dans la fenetre [start_idx; start_idx+look_ahead[
    porte un signal fort de ligne de poste."""
    end = min(start_idx + look_ahead, len(lines))
    for i in range(start_idx, end):
        if _is_table_row_signal(lines[i][2]):
            return True
    return False


# Fenetre de validation apres un cluster vertical : un VRAI en-tete de
# tableau est suivi d'un bloc de postes dans ses lignes proches. Sans cette
# validation, un cluster de metadonnees d'en-tete de document (Date /
# N° client / N° document / ...) est pris pour un en-tete de tableau et
# shielde les adresses qui se trouvent en aval jusqu'au footer.
_POSTE_LOOK_AHEAD = 20


def _find_vertical_clusters(
    lines: list[tuple[int, int, str]],
    lex_header: frozenset[str],
    horizontal_headers: set[int],
) -> list[list[int]]:
    """Repere les clusters de cellules d'en-tete verticales consecutives.

    Tolere une seule ligne vide intercalee entre deux cellules. Un cluster
    de moins de `_VERTICAL_MIN_CELLS` cellules est rejete (signal trop
    faible : risque de matcher quelques mots courts dans la prose). Un
    cluster non suivi d'un signal fort de ligne de poste dans la fenetre
    `_POSTE_LOOK_AHEAD` est egalement rejete (cas du bloc de metadonnees).
    """
    n = len(lines)
    clusters: list[list[int]] = []
    i = 0
    while i < n:
        if i in horizontal_headers:
            i += 1
            continue
        cluster: list[int] = []
        j = i
        while j < n:
            line = lines[j][2]
            if _is_vertical_header_cell(line, lex_header):
                cluster.append(j)
                j += 1
            elif cluster and not line.strip():
                # Tolerer une ligne vide intercalee.
                j += 1
            else:
                break
        if len(cluster) >= _VERTICAL_MIN_CELLS and _has_price_or_qty_within(
            lines, cluster[-1] + 1, _POSTE_LOOK_AHEAD
        ):
            clusters.append(cluster)
            i = j
        else:
            i += 1
    return clusters


def _has_table_signal(line: str) -> bool:
    """True si la ligne porte un signal tabulaire (prix, code, quantite)."""
    if _RX_PRICE.search(line) or _RX_LONGNUM.search(line):
        return True
    if _RX_QTY_UNIT.search(line):
        return True
    # Code alphanumerique long (>= 8 caracteres melant lettres et chiffres) :
    # reference produit type "KHZ-DA-032-0050-M". Le seuil ecarte un code
    # postal a prefixe pays ("F-93700").
    for tok in re.split(r"[ \t]+", line):
        core = tok.strip(".,;:()")
        if (
            len(core) >= 8
            and any(c.isdigit() for c in core)
            and any(c.isalpha() for c in core)
        ):
            return True
    return False


def _is_exception_line(line: str) -> bool:
    """True si la ligne ne doit PAS etre protegee (PII probable).

    Trois cas : email/URL ; numero de TVA formate ; aucun signal tabulaire
    (ligne d'adresse, de nom ou de prose intercalee dans le tableau).
    """
    if _RX_CONTACT.search(line):
        return True
    if _RX_VAT_FR.search(line):
        return True
    return not _has_table_signal(line)


def find_table_body_lines(
    text: str, lexicon_words: list[str]
) -> list[tuple[int, int]]:
    """Repere les plages (start, end) des lignes de corps de tableau a proteger.

    Args:
        text: texte source du document.
        lexicon_words: mots du lexique metier (business_lexicon), pour
            reconnaitre les en-tetes de tableau par densite.

    Returns:
        Liste de plages d'offsets ; chaque plage couvre une ligne protegee.
    """
    lex_simple = frozenset(
        _norm(w) for w in lexicon_words if w and " " not in w
    )
    if not lex_simple:
        return []
    # On enrichit le vocabulaire de detection d'en-tete avec les abreviations
    # courantes (Pos. / Réf. / Art. / No / Qté / UQ...) : sans elles, un
    # en-tete tres abrege comme celui de BALLUFF tombe sous le seuil de
    # densite et n'est pas reconnu, et tout son tableau reste non protege.
    lex_for_header = lex_simple | frozenset(_norm(a) for a in _HEADER_ABBREVIATIONS)
    lines = _lines_with_offsets(text)
    n = len(lines)

    # Phase 1 : en-tetes "ligne dense" (cas classique, en-tete sur 1 ligne).
    horizontal_headers: set[int] = {
        i for i, (_, _, c) in enumerate(lines) if _is_header_line(c, lex_for_header)
    }
    # Phase 2 : en-tetes "verticaux" (cluster de cellules courtes consecutives,
    # tres frequents avec une extraction PyMuPDF par blocs).
    vertical_clusters = _find_vertical_clusters(
        lines, lex_for_header, horizontal_headers,
    )
    # Mapping : ligne_de_debut_du_tableau -> ligne_de_fin_du_HEADER (inclus).
    # On part de cette fin de header pour chercher la borne basse, sans quoi
    # le mot "Somme"/"Total" present DANS un en-tete vertical fermerait le
    # tableau a la premiere ligne.
    table_starts: dict[int, int] = {}
    for h in horizontal_headers:
        table_starts[h] = h
    for cluster in vertical_clusters:
        table_starts[cluster[0]] = cluster[-1]
    if not table_starts:
        return []
    all_starts = set(table_starts.keys())

    protected: list[tuple[int, int]] = []
    for h in sorted(table_starts):
        h_end = table_starts[h]
        # Borne basse : suivre la cascade de totaux ; garde-fou sur footer.
        last_total: int | None = None
        end_idx = n - 1
        for i in range(h_end + 1, n):
            if i in all_starts:                    # tableau de la page suivante
                end_idx = i - 1
                break
            nc = _norm(lines[i][2])
            if _contains_term(nc, _TOTAL_TERMS):
                last_total = i
            if _contains_term(nc, _FOOTER_MARKERS):
                end_idx = last_total + 1 if last_total is not None else i - 1
                break
        else:
            if last_total is not None:
                end_idx = last_total + 1
        end_idx = min(end_idx, n - 1)
        # Collecter les lignes protegees, en ecartant les lignes d'exception.
        for i in range(h, end_idx + 1):
            start, end, content = lines[i]
            if content.strip() and not _is_exception_line(content):
                protected.append((start, end))
    return protected


# Recognizers dont le span ne doit JAMAIS etre ecarte par la zone tableau :
# - deny-lists privees (noms/orgs declares par le profil) : entites
#   critiques a masquer en toutes circonstances, y compris collees au
#   milieu d'une ligne de poste ;
# - signatures fortes (email avec @, IBAN valide par checksum, BIC) :
#   faux positifs quasi nuls, mieux vaut masquer que rater une fuite.
_CRITICAL_RECOGNIZERS = frozenset({
    "OrgSingleton", "OrgSingletonLoose",
    "OrganizationsDenyList", "OrganizationsLooseDenyList",
    "PeopleDenyList",
    "EmailRegex",
    "IbanRegex",
    "BicRegex",
    "RibFrRegex", "RibFrFieldsRegex",
    "VatFrRegex",
    "SirenRegex", "SiretRegex",
    # Spans issus de la propagation : reprennent un type deterministe d'une
    # entite deja detectee ailleurs. Les ecarter casse la coherence
    # inter-pages (1re occurrence en clair quand la 2e est masquee).
    "EntityPropagation",
    # ORG par suffixe juridique : signature tres distinctive (GmbH, SAS,
    # AKTIENGESELLSCHAFT...). Le rater laisse fuiter le nom du fournisseur
    # ou d'une banque tierce dans le bloc "Nos references bancaires".
    "OrgSuffixRegex",
    # PII RGPD a signature contextuelle forte : numero d'identite, secu
    # sociale, URSSAF / HMRC / UTR / NI Number, date de naissance, nom
    # de jeune fille, acronyme commercial. Tous exigent deja un libelle
    # explicite pour matcher - les faux positifs sont quasi-nuls et le
    # masquage doit s'appliquer meme en plein milieu d'un bloc qui aurait
    # ete a tort detecte comme tableau.
    "DateOfBirthRegex",
    "NationalIdRegex",
    "SocialSecurityFrRegex",
    "UrssafRegex",
    "UkNiNumberRegex",
    "UkDrivingLicenceRegex",
    "UkUtrRegex",
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
    "MaidenNameRegex",
    "CompanyHeaderRegex",
    "BankByContextRegex",
    "EnumeratedNamesRegex",
    "OrgLineExpansion", "PersonLineExpansion",
    # Anti-reidentification par recoupement (audit red-team P1)
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
})

# Marqueur d'un VRAI telephone (par opposition a 10 chiffres colles qui
# pourraient etre une reference article du tableau). On ne preserve un
# span PHONE dans la zone tableau que s'il porte des signes evidents de
# formatage telephonique : prefixe international, parentheses, ou
# separateurs entre les groupes de chiffres.
_PHONE_FORMATTED = re.compile(r"[+()]|\d[ .\-]\d")

# Libelle explicite precedant le numero : "Tél : 0164390478" / "电话:..."
# lève l'ambiguïté (numero colle vs reference article) et permet de
# preserver le span PHONE meme dans une zone tableau.
#
# Multilingue : 12 langues couvertes par le pipeline (FR/EN/ES/PT/IT/PL/
# DE/TR/CZ/CN/JP/BG). Le pattern doit accepter chaque variante connue ;
# limiter aux langues latines crée une asymétrie incoherente avec la
# detection des numéros eux-mêmes (qui est multilingue via le dispatcher
# `recognize_phone`).
_PHONE_LABEL = re.compile(
    r"(?ui)(?:"
    # FR / EN
    r"\bT[ée]l(?:[ée]phone)?\b|\bPhone\b|\bFax\b|\bMobile\b|\bGSM\b"
    r"|\bMob\.?|\bTel\.?"
    # DE
    r"|\bTelefon\b|\bTelefax\b|\bMobiltelefon\b"
    # ES / PT
    r"|\bTel[ée]fono\b|\bTlf\b|\bTel[ée]fone\b|\bM[óo]vil\b|\bCelular\b"
    # IT
    r"|\bTelefono\b|\bCellulare\b"
    # PL
    r"|\bTelefon\b|\bKom\.?|\bKomórka\b"
    # TR
    r"|\bTelefonu?\b|\bCep\b"
    # CZ / SK
    r"|\bTelefon\b|\bMobil\b"
    # CN (simplifié + traditionnel) : 电话/電話 (tel), 传真/傳真 (fax),
    # 手机/手機 (mobile)
    r"|电话|電話|传真|傳真|手机|手機"
    # JP : 電話 / FAX / 携帯 (keitai = mobile)
    r"|FAX|携帯"
    # BG (cyrillique) : тел., телефон, факс, моб.
    r"|\bтел\.?|\bтелефон\b|\bфакс\b|\bмоб\.?"
    r")\s*[.:：]?\s*\(?$"
)

_PHONE_RECOGNIZERS = frozenset({
    "PhoneFrRegex", "PhoneDeRegex", "PhoneUkRegex", "PhoneUsRegex",
    "PhoneItRegex", "PhoneEsRegex", "PhoneLatamRegex",
    "PhoneOceRegex", "PhonePtRegex", "PhoneBrRegex", "PhoneBeRegex",
    "PhoneInternationalRegex",
})


def _phone_has_explicit_label_before(text: str, start: int, window: int = 15) -> bool:
    """True si le span PHONE est immediatement precede d'un libelle
    telephonique explicite (Tél, Phone, Fax, etc.). Garantit qu'on ne
    drop pas un telephone identifie sans ambiguite par son label, meme
    s'il est colle sans separateur (cas frequent en footer de page :
    'Tél : 0164390478 - Fax : 0164375768')."""
    before = text[max(0, start - window): start]
    return bool(_PHONE_LABEL.search(before))


def drop_spans_in_table_body(
    text: str, spans: list[Span], allow_lists: dict
) -> list[Span]:
    """Ecarte les spans tombant dans une ligne de corps de tableau.

    La plupart des recognizers (GLiNER, dictionnaires, regex de noms ou
    d'adresses) sont concernes : dans le corps d'un tableau de postes,
    aucun masquage n'est legitime. EXCEPTION : les recognizers dits
    `_CRITICAL_RECOGNIZERS` - deny-lists privees et signatures fortes
    (email/IBAN/BIC) - sont preserves meme dans la zone, parce qu'ils
    designent des entites a masquer en priorite RGPD.

    Args:
        text: texte source.
        spans: spans detectes.
        allow_lists: bloc `allow_lists` de la configuration (fournit le
            lexique metier servant a reperer les en-tetes).

    Returns:
        Les spans, prives de ceux situes dans le corps de tableau
        sauf ceux issus d'un recognizer critique.
    """
    words, _ = _collect_entries(allow_lists)
    ranges = find_table_body_lines(text, words)
    if not ranges:
        return spans
    kept: list[Span] = []
    for s in spans:
        if s.recognizer in _CRITICAL_RECOGNIZERS:
            kept.append(s)
            continue
        # Un span PHONE n'est conserve dans la zone tableau QUE s'il porte
        # un format telephonique evident : sinon "0822010647" (10 chiffres
        # colles = reference article) serait protege a tort. Exception :
        # un libelle explicite avant ("Tél : ", "Phone:") leve l'ambiguite
        # meme pour un numero colle.
        if s.recognizer in _PHONE_RECOGNIZERS and (
            _PHONE_FORMATTED.search(s.text)
            or _phone_has_explicit_label_before(text, s.start)
        ):
            kept.append(s)
            continue
        if any(not (s.end <= a or b <= s.start) for a, b in ranges):
            continue
        kept.append(s)
    return kept
