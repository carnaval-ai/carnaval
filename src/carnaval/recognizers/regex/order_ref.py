# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de numero de commande / bon de commande client.

Detecte les references de PO (Purchase Order) emises par le destinataire
d'un AR. Ces numeros suivent souvent un format propre a l'ERP du client
(ex: SAP avec plage 42xxxxxxxx ou 47xxxxxxxx) et constituent une
**signature d'identification client** : un customer SAP PO 4200xxxxxx est
caracteristique, idem un PO Renault 8xxxxxx, un PO Stellantis OPT-xxxx.

Vecteur d'attaque red-team : sans masquage, l'attaquant identifie
le destinataire en 1 grep sur les conventions ERP du marche.

Strategie : masquer par libelle contextuel multilingue, plutot que par
format de valeur. Le libelle est l'ancre - tout chiffre 6-15 caracteres
apres "Votre commande / Your order / Ihre Bestellung..." est une PO.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span

# Libelles de reference commande / bon de commande, multilingues.
# Couvre les 12 langues du pipeline (FR/EN/ES/PT/IT/DE/PL/TR/CZ/CN/JP/BG).
# Les libelles courts ("PO", "Ref") doivent etre precedes d'une bordure
# pour eviter les matches dans des mots ("import"...).
_ORDER_LABEL = (
    r"(?:"
    # FR
    r"Votre\s+(?:commande|r[ée]f[ée]rence|n[°o]\s*de\s+commande|cde)"
    r"|N[°o]\s*(?:de\s+)?commande\s+client"
    r"|R[ée]f[ée]rences?\s+(?:commande|client|cde|du\s+client)"
    r"|R[ée]f\.?\s*(?:client|commande|cde)"
    r"|N[°o]\s*cde\s+client"
    r"|N[°o]\s*ordre(?:\s+client)?"
    r"|Vos\s+r[ée]f[ée]rences?"
    r"|Vos\s+r[ée]f\.?"
    r"|Vos\s+(?:n[°o]\s+de\s+)?cde"
    r"|Bon\s+de\s+commande\s+(?:client|n[°o])"
    r"|BCD\s+N[°o]"
    r"|N[°o]\s*BCD"
    r"|Cde\s+client"
    r"|Commande\s+(?:client|n[°o])"
    # EN
    r"|Your\s+(?:order|purchase\s+order|PO|reference)"
    r"|Customer\s+(?:order|reference|PO)"
    r"|Client\s+reference"
    r"|Purchase\s+order\s+(?:no\.?|number|#)?"
    r"|Order\s+(?:reference|number|no\.?)"
    # DE
    r"|Ihre\s+(?:Bestellung|Bestellnummer|Bestell-Nr\.?|Bestell\s+Nr\.?|Referenz)"
    r"|Bestellnummer\s+Kunde"
    r"|Kunden(?:bestellung|nummer|referenz)"
    # ES
    r"|Su\s+(?:pedido|orden|referencia)"
    r"|N[°o]\s*(?:de\s+)?pedido\s+(?:cliente|del\s+cliente)"
    r"|Referencia\s+(?:del\s+)?cliente"
    r"|Pedido\s+cliente"
    # IT
    r"|Vostro\s+(?:ordine|numero\s+ordine|riferimento)"
    r"|Vs\.?\s*ordine"
    r"|Riferimento\s+cliente"
    # PT
    r"|Vossa\s+(?:encomenda|referência|referencia|ordem)"
    r"|Refer[êe]ncia\s+(?:do\s+)?cliente"
    r"|N[°ºo]\s*(?:de\s+)?encomenda"
    # PL
    r"|Wasze\s+(?:zam[óo]wienie|zamowienie|odniesienie)"
    r"|Numer\s+zam[óo]wienia\s+klienta"
    r"|Referencja\s+klienta"
    # TR
    r"|Sipari[şs]\s+(?:no|numaras[ıi])"
    r"|M[üu][şs]teri\s+sipari[şs]"
    r"|Referans\s+no"
    # CZ
    r"|Va[šs]e\s+(?:objedn[áa]vka|reference|číslo\s+objedn[áa]vky)"
    r"|[ČC][íi]slo\s+objedn[áa]vky"
    # CN (simplifie + traditionnel)
    r"|您的(?:订单|採購單|採购单|订货号)"
    r"|客户(?:订单|订货号)号?"
    r"|採購單號"
    r"|采购订单"
    # JP
    r"|お客様の?注文(?:番号)?"
    r"|貴注文番号"
    r"|注文書番号"
    # BG (cyrillique)
    r"|Ваша(?:та)?\s+поръчка"
    r"|Номер\s+на\s+поръчка"
    r"|Клиентска\s+поръчка"
    r")"
)

# Separateur tolere entre le libelle et la valeur : `: # / N°/n° espace`.
# R1 : PAS de saut de ligne (`\n`) dans le separateur. Sinon la
# strategie 1 (libelle + valeur immediate) traverse une ligne et
# ramasse la valeur d'un AUTRE label (bug IFM v7 : "Votre commande\n
# 0241414242\nN° tel client" -> 0241414242 capture comme PO alors
# qu'il appartient au label "N° tel client" suivant).
_SEP = r"[ \t:#/.\-]{0,5}"

# Valeur : 6 a 15 caracteres alphanumeriques, contenant au moins 5 chiffres
# (un PO contient toujours majoritairement des chiffres). Tolere un suffixe
# alphabetique court (ex: "PO12345-A", "REF1234567-1").
_VALUE = r"(?P<value>[A-Z0-9](?:[A-Z0-9\-/]){4,14})"

# Pattern complet : libelle + sep + valeur.
_ORDER_REF_PATTERN = re.compile(
    rf"(?ui){_ORDER_LABEL}{_SEP}{_VALUE}\b"
)

# Pattern de signature SAP STRICT (configurable per client) : 10 chiffres au format
# `4200xxxxxx` ou `4700xxxxxx` - tranche SAP attribuee au client
# . Le format ferme + validation contextuelle (libelle
# PO dans +/- 10 lignes) constitue une IDENTIFICATION FORMELLE au sens
# de la directive Patrice (v4) :
#   - le pattern numerique seul n'est PAS suffisant (risque montant ou
#     reference produit fortuit) ;
#   - mais combine avec un libelle PO dans la fenetre, on prouve la
#     nature de cellule.
# Cas typique : layout tableau ou les labels sont en bloc 1 (lignes
# 20-25) et les valeurs en bloc 2 (lignes 30-35), trop loin pour la
# strategie 1 (libelle immediat).
_ORDER_REF_SAP_SIGNATURE = re.compile(
    r"(?<!\d)(?P<value>4[27]00\d{6})(?!\d)"
)

# Pour la validation contextuelle (strategie 2 : signature SAP + fenetre)
# on accepte des libelles plus courts qui sont trop ambigus pour la
# strategie 1 (ils generent des faux positifs si combines directement
# avec une valeur, mais sont des indices contextuels valides).
_ORDER_LABEL_LOOSE = (
    rf"(?:{_ORDER_LABEL}"
    # FR libelles courts
    r"|N[°o]\s*(?:de\s+)?[Cc]ommande"
    r"|N[°o]\s*[Cc]de"
    r"|N[°o]\s*comm\.?"  # abreviation : N° comm. / N°comm.
    r"|N[°o]?comm\."
    r"|[Cc]ommande\s+(?:n[°o]|client|du|de)"
    r"|^\s*[Cc]ommande\s*$"
    r"|\b[Cc]ommande\b(?=\s*[A-Z0-9])"  # "Commande 4200xxx"
    r"|Votre\s+ref\.?\s+du"
    r"|Votre\s+n[°o]\s+de\s+cde"
    r"|V\s*/\s*Cde"           # V/Cde N° XXX
    r"|VCde|V\.?Cde"
    r"|R[ée]f\.?\s+(?:du\s+)?(?:client|commande)"
    r"|R[ée]f[ée]rence\s*:?\s*$"  # libelle "Reference:" seul en tableau
    r"|N[°o]\s+de\s+[Cc]ommande"
    r"|no\.?\s+de\s+l['’]?\s*ordre"
    # CDE prefix dans la ligne
    r"|CDE\s+\d"
    # EN libelles courts
    r"|Order\s*(?:no\.?|n[°o]\.?|number|#)"
    r"|^Order\s*$"
    r")"
)
_ORDER_LABEL_COMPILED = re.compile(rf"(?uim){_ORDER_LABEL_LOOSE}")


def _has_min_digits(value: str, minimum: int = 5) -> bool:
    """True si la valeur contient au moins `minimum` chiffres."""
    return sum(1 for c in value if c.isdigit()) >= minimum


def _has_order_context(text: str, pos: int, window_lines: int = 10) -> bool:
    """True si un libelle PO est present dans une fenetre de +/-
    `window_lines` lignes autour de `pos`. Sert a valider une PO isolee
    (cas layout tableau ou libellé est séparé de la valeur)."""
    cursor = pos
    for _ in range(window_lines):
        nl = text.rfind("\n", 0, cursor)
        if nl < 0:
            cursor = 0
            break
        cursor = nl
    window_start = cursor
    cursor = pos
    for _ in range(window_lines + 1):
        nl = text.find("\n", cursor + 1)
        if nl < 0:
            cursor = len(text)
            break
        cursor = nl
    window_end = cursor
    return bool(_ORDER_LABEL_COMPILED.search(text[window_start:window_end]))


def recognize_order_ref_by_context(text: str, score: float = 0.92) -> list[Span]:
    """Detecte les references de PO emises par le destinataire de l'AR.

    Deux strategies cumulatives :

    1. **Libelle ancre + valeur proche** : "Votre commande : 4200xxxxxx"
       sur la meme ligne ou tres pres (sep <= 5 chars).
    2. **Signature SAP isolee** : 10 chiffres exactement, 1er chiffre
       3-9, avec un libelle PO present dans une fenetre +/- 10 lignes.
       Couvre le cas du layout tableau ou les labels sont separes des
       valeurs par serialisation PDF colonne par colonne (ex :
       "Votre Référence\\n...\\n...\\n4700004224").

    Le S4 resolve deduplique les chevauchements eventuels.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Liste de Span de type ORDER_REF.
    """
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()

    # Detection self-referent : si le doc est lui-meme un AR/Confirmation,
    # le libelle "Commande client" peut designer la commande RECUE par le
    # fournisseur (cote AR), donc le numero qui suit n'est pas un PO
    # client a anonymiser mais un identifiant metier du document.
    # Dans ce cas : on ne masque QUE les valeurs qui matchent le format
    # customer PO strict (4[27]00\d{6}).
    from .internal_refs import _is_self_referent_ar_document
    strict_only = _is_self_referent_ar_document(text)
    _PO_STRICT_RE = re.compile(r"^4[27]00\d{6}$")

    # Strategie 1 : libelle ancre + valeur sur meme ligne.
    for m in _ORDER_REF_PATTERN.finditer(text):
        value = m.group("value")
        if not _has_min_digits(value, 5):
            continue
        # En mode self-referent strict : on masque seulement le format PO
        # standard. SO000389066 (Gravotech) / CC/24541 (Ideatec) sont des
        # numeros AR fournisseur, pas des PO clients.
        if strict_only and not _PO_STRICT_RE.match(value):
            continue
        start, end = m.span("value")
        if (start, end) in seen:
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="ORDER_REF",
                text=value,
                score=score,
                recognizer="OrderRefByContextRegex",
            )
        )

    # Strategie 3 : libelle PO STRICT cote client + valeur dans fenetre
    # courte. Couvre le layout entrelace (label / date / sep / valeur).
    #
    # R1 (refonte v7) : fenetre RESTREINTE a 2 lignes maximum, et la valeur
    # doit etre SUR LA MEME LIGNE ou la ligne IMMEDIATEMENT SUIVANTE. Au-
    # dela, le risque est trop fort de ramasser la valeur d'un AUTRE label
    # (cas IFM v7 : "Votre commande" suivi 5 lignes plus loin du n° de tel
    # "0241414242" du libelle "N° tel client" inverse).
    #
    # Strategie 3 utilise `_ORDER_LABEL` (strict cote client), pas `_LOOSE`
    # qui contient des variantes ambigues. Contraintes :
    #   - fenetre max 2 lignes apres le libelle (vs 5 avant) ;
    #   - valeur = 5 a 15 chiffres ininterrompus ;
    #   - on stoppe au premier autre libelle (PO OU client) rencontre ;
    #   - on saute les valeurs precedees de virgule decimale (montants) ;
    #   - on saute si une autre valeur numerique 5+ chiffres est presente
    #     ENTRE le label et la valeur candidate (= valeur appartient
    #     probablement a un autre label).
    _ORDER_LABEL_STRICT = re.compile(rf"(?uim){_ORDER_LABEL}")
    _NUMERIC_VALUE = re.compile(r"(?<![\d,.])(?P<value>\d{5,15})(?!\d)")
    # Tout label de cluster (PO, client, contact, fax) qui invalide la
    # valeur si rencontre IMMEDIATEMENT APRES (layout vertical inverse).
    _ANY_CLUSTER_LABEL = re.compile(
        rf"(?uim)(?:{_ORDER_LABEL}"
        r"|N[°o]\s*t[ée]l|N[°o]\s+t[ée]l[ée]phone|T[ée]l[ée]phone"
        r"|Numero\s+de\s+t[ée]l|N[°o]\s+fax|Fax"
        r"|N[°o]\s+client|Code\s+client|Numero\s+client|Num[ée]ro\s+client"
        r"|Customer\s+(?:no|number)|Kundennummer|N[°o]\s+cliente"
        r"|Date(?:[ \t]+(?:de|du|d['’]))?"
        r"|Demandeur|Contact|Acheteur"
        r")"
    )
    for m_label in _ORDER_LABEL_STRICT.finditer(text):
        label_end = m_label.end()
        # Borne haute : 3 lignes max (compromis : permet SICK 40a33876
        # ou la valeur est 3 lignes apres le label, sans aller trop loin).
        cursor = label_end
        for _ in range(3):
            nl = text.find("\n", cursor + 1)
            if nl < 0:
                cursor = len(text)
                break
            cursor = nl
        window_end = cursor
        # Stop sur le prochain label cluster (entre label et valeur).
        next_label = _ANY_CLUSTER_LABEL.search(text, label_end + 1, window_end)
        if next_label:
            window_end = min(window_end, next_label.start())
        window = text[label_end:window_end]
        v = _NUMERIC_VALUE.search(window)
        if not v:
            continue
        v_start = label_end + v.start("value")
        v_end = label_end + v.end("value")
        if (v_start, v_end) in seen:
            continue
        if text[max(0, v_start - 1):v_start] == "[":
            continue
        # Self-referent : si le doc est lui-meme un AR, on masque
        # uniquement les valeurs au format customer PO standard (10 chiffres
        # 4[27]00xxxxxx). Cas Gravotech "Commande client\nSO000389066" :
        # 000389066 commence par 0 -> pas un PO -> on ne masque pas.
        if strict_only and not _PO_STRICT_RE.match(v.group("value")):
            continue
        # R1 : verifier que la valeur n'est PAS immediatement suivie d'un
        # autre label de cluster (layout vertical inverse). Si "valeur\n
        # Label" alors la valeur appartient probablement au Label suivant,
        # pas a notre order_ref.
        after_end = text.find("\n", v_end)
        if after_end < 0:
            after_end = len(text)
        next_line_start = after_end + 1
        # Verifier sur les 2 lignes suivantes :
        check_end = next_line_start
        for _ in range(2):
            nl = text.find("\n", check_end + 1)
            if nl < 0:
                check_end = len(text)
                break
            check_end = nl
        after_block = text[next_line_start:check_end]
        if _ANY_CLUSTER_LABEL.search(after_block):
            continue  # valeur appartient probablement au label suivant
        seen.add((v_start, v_end))
        spans.append(
            Span(
                start=v_start, end=v_end,
                entity_type="ORDER_REF",
                text=v.group("value"),
                score=score * 0.90,
                recognizer="OrderRefByContextRegex",
            )
        )

    # Strategie 2 : signature SAP STRICT (customer-specific) (4200xxxxxx/4700xxxxxx)
    # + libelle PO dans une fenetre +/- 10 lignes. Couvre les layouts
    # tableau ou les labels sont séparés des valeurs (cas frequent en
    # extraction PDF colonne par colonne).
    # Le format `4[27]00\d{6}` est suffisamment specifique au client pour
    # qualifier d'identification formelle quand un libelle PO est present
    # dans la fenetre contextuelle.
    for m in _ORDER_REF_SAP_SIGNATURE.finditer(text):
        start, end = m.span("value")
        if (start, end) in seen:
            continue
        if not _has_order_context(text, start):
            continue
        seen.add((start, end))
        spans.append(
            Span(
                start=start, end=end,
                entity_type="ORDER_REF",
                text=m.group("value"),
                score=score * 0.95,
                recognizer="OrderRefByContextRegex",
            )
        )

    return spans
