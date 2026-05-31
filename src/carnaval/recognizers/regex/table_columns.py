# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de tableau colonnaire : labels et valeurs serialises.

Vecteur d'attaque red-team v2 : dans certains AR, l'extraction PDF
serialise les colonnes d'un tableau ligne par ligne. Les LABELS sont
groupes en tete du bloc, puis les VALEURS suivent (1 valeur par ligne).
Exemple observe (Serv) :

    Date              <- label[0]
    Numero piece      <- label[1]
    Client            <- label[2]
    Votre reference   <- label[3]
    Commercial        <- label[4]
    --- separation ---
    15/05/2024        <- value[0] (matche Date)
    24202357          <- value[1] (matche Numero piece)
    C0001065          <- value[2] (matche Client)
    [ORDER_REF_1]     <- value[3] (matche Votre reference)
    DUBUT             <- value[4] (matche Commercial)

Les patterns "libelle + valeur proche" classiques ne couvrent pas ce
layout car le label et la valeur sont separes de 5-10 lignes.

Strategie : detecter un cluster de labels (>= 3 labels consecutifs sur
des lignes courtes), suivi d'un cluster de valeurs (>= 3 valeurs sur
des lignes courtes). Apparier label[i] avec value[i].

Tokenise les valeurs dont le label est dans une liste cible (Client,
Commercial, Acheteur, Code client, etc.).
"""

from __future__ import annotations

import re

from carnaval.core.span import Span


# Libelles cibles qui declenchent la tokenisation de leur valeur
# associee. Cle = libelle (normalise lower), Valeur = entity_type
# du span genere.
_TABLE_LABELS = {
    # Personne (commerciaux, acheteurs, contacts) - multilingue v6.
    # FR
    "commercial": "PERSON",
    "commerciale": "PERSON",
    "vendeur": "PERSON",
    "acheteur": "PERSON",
    "contact": "PERSON",
    "suivi par": "PERSON",
    "responsable": "PERSON",
    "representant": "PERSON",
    "représentant": "PERSON",
    "demandeur": "PERSON",
    "signataire": "PERSON",
    "assistant(e)": "PERSON",
    "assistant": "PERSON",
    "assistante": "PERSON",
    "interlocuteur": "PERSON",
    "à l'attention de": "PERSON",
    "a l'attention de": "PERSON",
    # EN
    "sales rep": "PERSON",
    "sales representative": "PERSON",
    "salesperson": "PERSON",
    "buyer": "PERSON",
    "purchaser": "PERSON",
    "account manager": "PERSON",
    "attention": "PERSON",
    "attn": "PERSON",
    "attn.": "PERSON",
    "for the attention of": "PERSON",
    "to the attention of": "PERSON",
    # DE
    "ansprechpartner": "PERSON",
    "kontakt": "PERSON",
    "verkäufer": "PERSON",
    "verkaeufer": "PERSON",
    "einkäufer": "PERSON",
    "einkaeufer": "PERSON",
    "vertreter": "PERSON",
    "zu händen": "PERSON",
    "z.hd.": "PERSON",
    "z. hd.": "PERSON",
    # ES
    "contacto": "PERSON",
    "vendedor": "PERSON",
    "comprador": "PERSON",
    "representante": "PERSON",
    "a la atencion de": "PERSON",
    "a la atención de": "PERSON",
    # IT
    "contatto": "PERSON",
    "venditore": "PERSON",
    "acquirente": "PERSON",
    "rappresentante": "PERSON",
    "all'attenzione di": "PERSON",
    # PT
    "contacto": "PERSON",
    "vendedor": "PERSON",
    "comprador": "PERSON",
    "à atenção de": "PERSON",
    "a atencao de": "PERSON",
    # NL
    "contactpersoon": "PERSON",
    "verkoper": "PERSON",
    "ter attentie van": "PERSON",
    "t.a.v.": "PERSON",
    # Code client
    "client": "CLIENT_CODE",
    "n° client": "CLIENT_CODE",
    "no client": "CLIENT_CODE",
    "no. client": "CLIENT_CODE",
    "no.client": "CLIENT_CODE",
    "n°client": "CLIENT_CODE",
    "code client": "CLIENT_CODE",
    "numero client": "CLIENT_CODE",
    "numéro client": "CLIENT_CODE",
    # Audit v5-bis : variantes avec "de"
    "numero de client": "CLIENT_CODE",
    "numéro de client": "CLIENT_CODE",
    "n° de client": "CLIENT_CODE",
    "no de client": "CLIENT_CODE",
    "client n°": "CLIENT_CODE",
    "client no": "CLIENT_CODE",
    "client no.": "CLIENT_CODE",
    "compte client": "CLIENT_CODE",
    "compte adresse": "CLIENT_CODE",
    "sold to": "CLIENT_CODE",
    "code fournisseur": "CLIENT_CODE",
    "n° fournisseur": "CLIENT_CODE",
    "no fournisseur": "CLIENT_CODE",
    "no.fournisseur": "CLIENT_CODE",
    # Audit v6 - symetrie multilingue : codes client par langue
    # EN
    "customer no": "CLIENT_CODE",
    "customer no.": "CLIENT_CODE",
    "customer number": "CLIENT_CODE",
    "customer code": "CLIENT_CODE",
    "customer id": "CLIENT_CODE",
    "customer account": "CLIENT_CODE",
    "customer reference": "CLIENT_CODE",
    "client no": "CLIENT_CODE",
    "client no.": "CLIENT_CODE",
    "client number": "CLIENT_CODE",
    "client code": "CLIENT_CODE",
    "account no": "CLIENT_CODE",
    "account number": "CLIENT_CODE",
    "sold to": "CLIENT_CODE",
    "bill to": "CLIENT_CODE",
    "ship to": "CLIENT_CODE",
    "delivery to": "CLIENT_CODE",
    "delivery address": "CLIENT_CODE",
    "billing address": "CLIENT_CODE",
    "buyer": "CLIENT_CODE",
    "recipient": "CLIENT_CODE",
    "your customer no": "CLIENT_CODE",
    "your customer number": "CLIENT_CODE",
    "your reference": "CLIENT_CODE",
    # DE
    "kundennummer": "CLIENT_CODE",
    "kunden-nr": "CLIENT_CODE",
    "kunden-nr.": "CLIENT_CODE",
    "kunden nr": "CLIENT_CODE",
    "kontonummer": "CLIENT_CODE",
    "konto-nr": "CLIENT_CODE",
    "kundenkonto": "CLIENT_CODE",
    "rechnungsempfänger": "CLIENT_CODE",
    "rechnungsempfaenger": "CLIENT_CODE",
    "rechnungsadresse": "CLIENT_CODE",
    "lieferadresse": "CLIENT_CODE",
    "lieferanschrift": "CLIENT_CODE",
    "lieferung an": "CLIENT_CODE",
    "versand an": "CLIENT_CODE",
    "ihre kundennummer": "CLIENT_CODE",
    "ihre kunden-nr": "CLIENT_CODE",
    # ES
    "n° cliente": "CLIENT_CODE",
    "no cliente": "CLIENT_CODE",
    "numero cliente": "CLIENT_CODE",
    "número cliente": "CLIENT_CODE",
    "n° de cliente": "CLIENT_CODE",
    "numero de cliente": "CLIENT_CODE",
    "número de cliente": "CLIENT_CODE",
    "codigo cliente": "CLIENT_CODE",
    "código cliente": "CLIENT_CODE",
    "codigo de cliente": "CLIENT_CODE",
    "código de cliente": "CLIENT_CODE",
    "cuenta cliente": "CLIENT_CODE",
    "direccion de entrega": "CLIENT_CODE",
    "dirección de entrega": "CLIENT_CODE",
    "direccion de facturacion": "CLIENT_CODE",
    "dirección de facturación": "CLIENT_CODE",
    "entrega a": "CLIENT_CODE",
    "facturar a": "CLIENT_CODE",
    "facturacion a": "CLIENT_CODE",
    "facturación a": "CLIENT_CODE",
    # IT
    "codice cliente": "CLIENT_CODE",
    "codice di cliente": "CLIENT_CODE",
    "n° di cliente": "CLIENT_CODE",
    "numero di cliente": "CLIENT_CODE",
    "conto cliente": "CLIENT_CODE",
    "indirizzo di consegna": "CLIENT_CODE",
    "indirizzo di spedizione": "CLIENT_CODE",
    "indirizzo di fatturazione": "CLIENT_CODE",
    "consegna a": "CLIENT_CODE",
    "fatturare a": "CLIENT_CODE",
    "fatturazione a": "CLIENT_CODE",
    # PT
    "no de cliente": "CLIENT_CODE",
    "n° do cliente": "CLIENT_CODE",
    "codigo do cliente": "CLIENT_CODE",
    "código do cliente": "CLIENT_CODE",
    "conta do cliente": "CLIENT_CODE",
    "endereco de entrega": "CLIENT_CODE",
    "endereço de entrega": "CLIENT_CODE",
    "endereco de faturacao": "CLIENT_CODE",
    "endereço de faturação": "CLIENT_CODE",
    "entrega a": "CLIENT_CODE",
    "faturar a": "CLIENT_CODE",
    # NL
    "klantnummer": "CLIENT_CODE",
    "klant-nr": "CLIENT_CODE",
    "klantcode": "CLIENT_CODE",
    "leveringsadres": "CLIENT_CODE",
    "verzendadres": "CLIENT_CODE",
    "factuuradres": "CLIENT_CODE",
    "afleveren aan": "CLIENT_CODE",
    # Reference commande (customer PO). NB : le N° de commande emetteur
    # (= ref fournisseur, "no commande" tout court) reste NON-TARGET car
    # info metier (rapprochement AR/facture, directive Patrice v4).
    # On ne tokenise que ce qui pointe vers la customer PO (votre + cde
    # client).
    "votre référence": "ORDER_REF",
    "votre reference": "ORDER_REF",
    "votre commande": "ORDER_REF",
    "votre cde": "ORDER_REF",
    "votre n° de commande": "ORDER_REF",
    "votre no de commande": "ORDER_REF",
    "votre n° commande": "ORDER_REF",
    "votre no commande": "ORDER_REF",
    "n° cde client": "ORDER_REF",
    "no cde client": "ORDER_REF",
    "n° cde": "ORDER_REF",
    "no cde": "ORDER_REF",
    "réf cde": "ORDER_REF",
    "ref cde": "ORDER_REF",
    # customer PO : variantes multilingues (Audit v6 - symetrie)
    # EN
    "your order": "ORDER_REF",
    "your reference": "ORDER_REF",
    "your purchase order": "ORDER_REF",
    "your order no": "ORDER_REF",
    "your order number": "ORDER_REF",
    "your po": "ORDER_REF",
    "po number": "ORDER_REF",
    "p.o. number": "ORDER_REF",
    "purchase order no": "ORDER_REF",
    "purchase order number": "ORDER_REF",
    "customer po": "ORDER_REF",
    "customer po no": "ORDER_REF",
    "order ref": "ORDER_REF",
    "order reference": "ORDER_REF",
    # DE
    "ihre bestellung": "ORDER_REF",
    "ihre bestellnummer": "ORDER_REF",
    "ihre bestell-nr": "ORDER_REF",
    "ihre bestell nr": "ORDER_REF",
    "ihre referenz": "ORDER_REF",
    "kundenbestellung": "ORDER_REF",
    "bestellnummer kunde": "ORDER_REF",
    # ES
    "su pedido": "ORDER_REF",
    "su referencia": "ORDER_REF",
    "pedido cliente": "ORDER_REF",
    "n° de pedido cliente": "ORDER_REF",
    "referencia del cliente": "ORDER_REF",
    # IT
    "vostro ordine": "ORDER_REF",
    "vostro numero ordine": "ORDER_REF",
    "vostro riferimento": "ORDER_REF",
    "vs ordine": "ORDER_REF",
    "vs. ordine": "ORDER_REF",
    "riferimento cliente": "ORDER_REF",
    # PT
    "vossa encomenda": "ORDER_REF",
    "vossa referencia": "ORDER_REF",
    "vossa referência": "ORDER_REF",
    "referencia do cliente": "ORDER_REF",
    "referência do cliente": "ORDER_REF",
    # NL
    "uw bestelling": "ORDER_REF",
    "uw referentie": "ORDER_REF",
    "uw ordernummer": "ORDER_REF",
    # N° d'affaire / dossier client (multilingue v6).
    # FR
    "affaire": "AFFAIR_NUMBER",
    "n° affaire": "AFFAIR_NUMBER",
    "no affaire": "AFFAIR_NUMBER",
    "n° d'affaire": "AFFAIR_NUMBER",
    "n° daffaire": "AFFAIR_NUMBER",
    "dossier": "AFFAIR_NUMBER",
    "n° dossier": "AFFAIR_NUMBER",
    "no dossier": "AFFAIR_NUMBER",
    "réf affaire": "AFFAIR_NUMBER",
    "ref affaire": "AFFAIR_NUMBER",
    "réf dossier": "AFFAIR_NUMBER",
    "ref dossier": "AFFAIR_NUMBER",
    # EN
    "project no": "AFFAIR_NUMBER",
    "project number": "AFFAIR_NUMBER",
    "project ref": "AFFAIR_NUMBER",
    "case no": "AFFAIR_NUMBER",
    "case number": "AFFAIR_NUMBER",
    "file no": "AFFAIR_NUMBER",
    "file number": "AFFAIR_NUMBER",
    # DE
    "projektnummer": "AFFAIR_NUMBER",
    "projekt-nr": "AFFAIR_NUMBER",
    "aktenzeichen": "AFFAIR_NUMBER",
    # ES
    "n° expediente": "AFFAIR_NUMBER",
    "numero expediente": "AFFAIR_NUMBER",
    # IT
    "n° pratica": "AFFAIR_NUMBER",
    "numero pratica": "AFFAIR_NUMBER",
}

# Libelles tabulaires "non-cibles" : on les reconnait comme libelles
# (pour former un cluster) mais on NE TOKENISE PAS leur valeur associee
# (car non sensible : Date, Numero piece, Quantite...).
_TABLE_LABELS_NON_TARGET = frozenset({
    # Dates et numerotation generique - multilingue v6.
    # FR
    "date", "date de cde", "date de commande", "date de réception",
    "date de reception", "date d'expédition", "date d'expedition",
    "date d'émission", "date d'emission", "date de livraison",
    "date d'echeance", "date d'échéance", "date prévisionnelle",
    "date previsionnelle", "date prévue", "date prevue", "prévue le",
    "prevue le", "imprimé le", "imprime le", "edité le", "édité le",
    "date de livraison estimée", "date de livraison estimee",
    "date livraison", "expedition prevue", "expédition prévue",
    "modifié le", "modifie le",
    "page", "type", "code",
    "numéro / date", "numero / date", "n° / date", "no / date",
    # EN
    "date document", "document date", "order date", "delivery date",
    "shipping date", "ship date", "due date", "invoice date",
    "issue date", "expected delivery date", "estimated delivery date",
    "modified on", "printed on", "issued on",
    # DE
    "datum", "auftragsdatum", "lieferdatum", "versanddatum",
    "rechnungsdatum", "fälligkeitsdatum", "faelligkeitsdatum",
    "ausstellungsdatum", "voraussichtliches lieferdatum",
    "geändert am", "geaendert am", "gedruckt am",
    # ES
    "fecha", "fecha de pedido", "fecha de entrega", "fecha de envío",
    "fecha de envio", "fecha de factura", "fecha de vencimiento",
    "fecha de emisión", "fecha de emision",
    # IT
    "data", "data ordine", "data consegna", "data spedizione",
    "data fattura", "data scadenza", "data emissione",
    # PT
    "data", "data pedido", "data entrega", "data envio",
    "data fatura", "data vencimento", "data emissão", "data emissao",
    # Montants / quantites - multilingue v6.
    # FR
    "remise", "ttc", "ht", "tva", "vat",
    "prix", "montant", "total", "sous-total",
    "quantite", "quantité", "qte", "qt", "q",
    "unite", "unité", "u", "u.v.", "uv", "u.v",
    "p.u", "pu", "pu ht", "p.u.", "puht", "prix unit", "prix unitaire",
    "prix net ht", "prix net", "montant ht", "montant uc",
    "valeur",
    # EN
    "price", "amount", "subtotal", "qty", "quantity",
    "unit", "unit price", "net price", "gross", "net",
    "value", "discount", "tax",
    # DE
    "preis", "menge", "anzahl", "einheit", "stück", "stueck",
    "einzelpreis", "gesamtpreis", "betrag", "rabatt", "mehrwertsteuer",
    "mwst", "netto", "brutto", "wert",
    # ES
    "precio", "importe", "cantidad", "unidad", "ud", "uds",
    "precio unitario", "descuento", "iva", "neto", "bruto",
    # IT
    "prezzo", "importo", "quantità", "quantita", "unità", "unita",
    "prezzo unitario", "sconto", "iva", "netto", "lordo",
    # PT
    "preço", "preco", "quantidade", "unidade", "valor",
    "preço unitário", "preco unitario", "iva", "líquido", "liquido",
    # Refs produits (NON-TARGET : info metier conservee) - multilingue v6.
    # FR
    "numero piece", "numéro pièce", "numero", "numéro",
    "n°", "n", "no", "no.", "num",
    "reference", "référence", "ref.", "réf.", "ref", "réf",
    "designation", "désignation",
    "article", "code article", "n° article", "no article",
    "désignation article", "designation article",
    "numéro article", "numero article",
    "numero article / article client", "numéro article / article client",
    "commentaire", "commentaires",
    "poste", "position", "pos", "pos.",
    # EN
    "description", "item", "part no", "part number", "part",
    "sku", "model", "model no", "comments", "remarks", "notes",
    "line", "line no", "line item",
    # DE
    "artikel", "artikelnummer", "art.-nr", "artikel-nr",
    "bezeichnung", "beschreibung", "bemerkung", "bemerkungen",
    "position", "pos.", "modell", "teilenummer",
    # ES
    "artículo", "articulo", "codigo articulo", "código artículo",
    "descripción", "descripcion", "observaciones", "comentarios",
    "posicion", "posición", "modelo", "referencia",
    # IT
    "articolo", "codice articolo", "descrizione",
    "osservazioni", "commenti", "posizione", "modello",
    # PT
    "artigo", "código artigo", "codigo artigo",
    "descrição", "descricao", "observações", "observacoes", "comentários",
    "posição", "posicao",
    # Numero de commande emetteur (= ref fournisseur, info metier).
    # Volontairement laisses NON-TARGET car ambiguite : sans "votre"
    # ou "client", on assume cote fournisseur (non sensible).
    # FR
    "commande", "command", "no commande", "n° commande",
    "no de commande", "n° de commande", "numero de commande", "numéro de commande",
    "réf commande", "ref commande", "no réf", "no ref",
    "no facture", "n° facture", "n° de facture",
    "numero du document", "numéro du document",
    "n° document", "no document", "n° de document", "no de document",
    "n° doc", "no doc",
    "date de la commande", "date de cde", "date commande", "date de réception",
    # EN
    "order no", "order number", "order ref", "document no", "document number",
    "doc no", "invoice no", "invoice number", "quote no", "quote number",
    "quotation no", "quotation number", "no", "number",
    # DE
    "bestellnummer", "bestell-nr", "bestell nr", "auftragsnummer",
    "auftrag-nr", "auftrags-nr", "dokumentnummer", "dokument-nr",
    "rechnungsnummer", "rechnung-nr", "rg-nr",
    "angebotsnummer", "angebot-nr",
    # ES
    "n° pedido", "no pedido", "numero pedido", "número pedido",
    "n° factura", "n° documento", "n° presupuesto",
    "n° de pedido", "n° de factura", "n° de documento",
    # IT
    "n° ordine", "numero ordine", "n° fattura", "n° documento",
    "n° preventivo", "n° di ordine", "n° di fattura",
    # PT
    "n° encomenda", "numero encomenda", "número encomenda",
    "n° fatura", "n° factura", "n° documento", "n° orcamento",
    # NL
    "ordernummer", "bestelnummer", "factuurnummer", "documentnummer",
    "version", "rev", "rev.", "indice", "ind", "ind.",
    "réf devis", "ref devis", "devis", "quotation", "n° devis", "no devis",
    "votre n°", "notre n°",
    "nos refs", "nos refs.", "nos références", "nos references",
    "n° cde interne", "no cde interne", "n° cde interne fournisseur",
    "n° ar", "no ar", "numéro ar", "numero ar",
    # Coordonnees / contact (libelles, valeurs deja captees par autres
    # recognizers)
    "téléphone", "telephone", "tel", "tél", "phone",
    "e-mail", "email", "mail",
    "fax", "telecopie", "télécopie",
    "fonction", "function",
    # Conditions / modes
    "mode", "mode d'expédition", "mode d'expedition", "mode de livraison",
    "mode de paiement", "mode de règlement", "mode de reglement",
    "mode de réglement",
    "cond. de règlement", "cond. de reglement", "conditions de règlement",
    "conditions de reglement", "conditions de livraison",
    "conditions de paiement", "condition d'expédition",
    "condition d'expedition",
    "incoterm", "incoterms", "incoterm 2020", "terms of payment",
    "terms", "payment terms", "delivery terms",
    "secteur", "secteur commercial",
    "destination", "destinataire", "destinateur",
    "expediteur", "expéditeur",
    "etat", "état", "statut", "status",
    "lig", "ligne", "line",
    "lieu", "lieu de livraison",
    "mission",
    # Coordonnees externes (= info metier non identifiante du destinataire)
    "vos refs", "vos refs.", "vos references", "vos références",
    # Frais / divers
    "frais", "fees", "discount", "subtotal",
    "delai", "délai", "delivery", "echeance", "échéance",
    "devise", "currency", "monnaie",
    "pays d'origine", "pays origine", "country of origin",
    "code douanier", "code douane", "tariff code",
})

# Set des libelles cibles + non-cibles : tous reconnus comme labels.
_LABEL_SET_TARGET = set(_TABLE_LABELS.keys())
_LABEL_SET = _LABEL_SET_TARGET | _TABLE_LABELS_NON_TARGET

# Une "ligne courte" : <= 35 chars, contient 1-3 mots significatifs.
_MAX_LINE_LEN = 40

# Mots metier / unites tres communs a NE PAS prendre pour valeur
# (lignes de "date" tabulaire), considerees comme NON-VALEUR.
_NOT_A_VALUE = frozenset({
    "date", "page", "type", "code", "remise", "ttc", "ht", "tva",
    "qte", "qty", "u", "kg", "g", "ml", "l", "m", "mm", "cm",
    "eur", "usd", "gbp", "non", "oui", "yes", "no",
    "n/a", "tbd", "ras", "ok", "ko",
    "client",  # Si "client" apparait dans une valeur, c'est un label deplacé
    # Mots metier de remplissage
    "facture", "commande", "livraison",
})


def _is_short_line(line: str) -> bool:
    """True si la ligne est courte (potentiel label ou valeur unique)."""
    stripped = line.strip()
    return 1 <= len(stripped) <= _MAX_LINE_LEN


def _normalize_label(line: str) -> str:
    """Normalise un label : lower, strip, sans ponctuation finale."""
    return line.strip().lower().rstrip(":.;-").strip()


def _is_value_candidate(line: str) -> bool:
    """True si la ligne ressemble a une valeur de cellule (pas un libelle
    deguise ni un mot de remplissage)."""
    stripped = line.strip()
    if not (1 <= len(stripped) <= _MAX_LINE_LEN):
        return False
    norm = stripped.lower().rstrip(":.;-").strip()
    if norm in _LABEL_SET:
        return False
    if norm in _NOT_A_VALUE:
        return False
    # Si la ligne ne contient PAS au moins une lettre OU un chiffre,
    # c'est probablement une separation ("---", "***").
    if not any(c.isalnum() for c in stripped):
        return False
    return True


def recognize_table_columns(text: str, score: float = 0.82) -> list[Span]:
    """Detecte les valeurs de tableau colonnaire serialise.

    Algorithme :
        1. Decoupe le texte en lignes.
        2. Trouve les clusters de >= 3 LABELS courts consecutifs.
        3. Pour chaque cluster, cherche immediatement apres (skip lignes
           vides) un cluster de >= K VALEURS courtes consecutives, ou
           K = nombre de labels.
        4. Apparie label[i] avec value[i] et masque les valeurs dont
           le label est dans `_TABLE_LABELS`.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Liste de Span (PERSON / CLIENT_CODE / ORDER_REF selon le label).
    """
    lines = text.split("\n")
    # Positions absolues du debut de chaque ligne dans le texte
    line_offsets: list[int] = []
    pos = 0
    for ln in lines:
        line_offsets.append(pos)
        pos += len(ln) + 1  # +1 pour le \n

    spans: list[Span] = []
    i = 0
    n_lines = len(lines)

    while i < n_lines:
        # 1. Detecter un cluster de labels consecutifs.
        labels_in_cluster: list[tuple[int, str]] = []  # (line_idx, label_norm)
        j = i
        while j < n_lines and _is_short_line(lines[j]):
            norm = _normalize_label(lines[j])
            if norm in _LABEL_SET:
                labels_in_cluster.append((j, norm))
                j += 1
            else:
                # Tolere 1 ligne VIDE (whitespace seul) entre 2 labels.
                # Refuser tout autre contenu : evite que du bruit numerique
                # (":0", "-", etc.) soit assimile a un saut intra-cluster
                # et decale l'appariement label/valeur (vecteur cas C v4).
                if (
                    labels_in_cluster
                    and not lines[j].strip()
                    and j + 1 < n_lines
                ):
                    next_norm = _normalize_label(lines[j + 1])
                    if next_norm in _LABEL_SET:
                        j += 1
                        continue
                break
        # Au moins 2 labels cibles dans le cluster pour qu'on l'exploite
        if len(labels_in_cluster) < 2:
            i = j + 1 if j == i else j
            continue

        # 2. Apres le cluster de labels, chercher un cluster de valeurs.
        # Tolerer quelques lignes intermediaires (sous-titres / separateurs).
        k = j
        # Skip lignes vides ou non-value
        while k < n_lines and not _is_value_candidate(lines[k]):
            k += 1
            if k - j > 5:
                break  # Trop loin, abandonne
        else:
            # Cluster de valeurs candidates
            values_in_cluster: list[tuple[int, str]] = []
            while k < n_lines and _is_value_candidate(lines[k]):
                values_in_cluster.append((k, lines[k].strip()))
                k += 1

            # 3. Apparier label[idx] avec value[idx] dans l'ordre observe.
            num_labels = len(labels_in_cluster)
            num_values = len(values_in_cluster)
            if num_values >= 2:
                # On apparie autant que possible (min des deux)
                for idx in range(min(num_labels, num_values)):
                    label_idx, label_norm = labels_in_cluster[idx]
                    value_line_idx, value_text = values_in_cluster[idx]
                    entity_type = _TABLE_LABELS.get(label_norm)
                    if entity_type is None:
                        continue
                    # Trouver la position absolue de la valeur
                    line_start = line_offsets[value_line_idx]
                    raw_line = lines[value_line_idx]
                    # Skip whitespace de tete
                    offset = 0
                    while offset < len(raw_line) and raw_line[offset] in " \t":
                        offset += 1
                    span_start = line_start + offset
                    span_end = span_start + len(value_text)
                    spans.append(
                        Span(
                            start=span_start, end=span_end,
                            entity_type=entity_type,
                            text=value_text,
                            score=score,
                            recognizer="TableColumnsRegex",
                        )
                    )

        # Avancer apres ce bloc
        i = max(k, j + 1)

    return spans
