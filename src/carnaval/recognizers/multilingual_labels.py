# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Source unique multilingue des libelles d'extraction.

Cause racine D (audit v7) : les labels FR/EN/DE/ES/IT/PT/NL etaient
dupliques dans `client_code.py`, `table_columns.py`, `order_ref.py` etc.
sans coherence. Ajout d'une langue = duplication a 3+ endroits, oublis
inevitables.

Ce module est la **source unique de verite** pour les libelles :

    CATEGORY -> LANGUAGE -> [list of label strings]

Categories :
    CLIENT_CODE          : libelles qui designent un code/numero client
    ORDER_REF_CLIENT     : libelles qui designent une commande COTE CLIENT
                           (PO emise par le client, "Votre commande")
    ORDER_REF_VENDOR     : libelles qui designent une commande COTE
                           FOURNISSEUR ("N° commande" sans precision -
                           assume vendeur, info metier preservee)
    AFFAIR_NUMBER        : N° d'affaire / dossier client
    PERSON               : commerciaux, acheteurs, contacts
    PHONE                : telephones et fax
    DATE                 : libelles de date (non-target en general)
    AMOUNT               : montants / quantites / prix
    REFERENCE            : refs articles / designations / commentaires
    DOCUMENT             : numero/date document

Usage :
    from carnaval.recognizers.multilingual_labels import labels_for
    fr_labels = labels_for("CLIENT_CODE", "fr")
    all_lang_labels = labels_for("CLIENT_CODE")  # toutes langues

Maintenance :
    Pour ajouter un libelle, l'ajouter ICI uniquement. Les recognizers
    qui en dependent (`client_code.py`, `table_columns.py`, ...) le
    picorent automatiquement.
"""

from __future__ import annotations

# Dictionnaire CATEGORY -> LANG -> labels.
# Convention LANG : code ISO 639-1 (fr, en, de, es, it, pt, nl).
LABELS: dict[str, dict[str, list[str]]] = {
    "CLIENT_CODE": {
        "fr": [
            "N° client", "N° de client", "No client", "No. client",
            "No.Client", "N°Client", "Numéro client", "Numéro de client",
            "Code client", "N° code client",
            "Client n°", "Client no", "Client no.",
            "Compte client", "N° compte client", "Compte adresse",
            "Compte de facturation", "Compte de livraison",
            "Numéro de compte", "N° de compte",
            "Donneur d'ordre", "Adresse de livraison",
            "Livraison à", "Livré à", "Facturation à",
            "Facturer à", "Adressé à",
            "Destinataire facture", "Destinataire facturation",
            "Réceptionnaire facture", "Receptionnaire facture",
            "Client livré", "Client facturé", "Client commandé",
            "LIVRAISON A", "FACTURATION A",
            "N° RS", "Réf RS",
            "Compte RS",
        ],
        "en": [
            "Customer no", "Customer no.", "Customer number",
            "Customer code", "Customer id", "Customer account",
            "Customer reference", "Customer ref",
            "Client no", "Client number", "Client code", "Client id",
            "Account no", "Account number", "Account holder",
            "Acct no", "Acct. no",
            "Sold to", "Bill to", "Ship to",
            "Delivery to", "Delivery address",
            "Billing address", "Invoice to", "Invoice address",
            "Your customer no", "Your customer number",
            "Your reference", "Your account",
            "Recipient no", "Recipient number", "Buyer no",
        ],
        "de": [
            "Kundennummer", "Kunden-Nr", "Kunden-Nr.", "Kunden Nr",
            "Kontonummer", "Konto-Nr", "Kundenkonto",
            "Kundencode", "Kundenreferenz",
            "Rechnungsempfänger", "Rechnungsempfaenger",
            "Rechnungsadresse", "Lieferadresse", "Lieferanschrift",
            "Lieferung an", "Versand an",
            "Ihre Kundennummer", "Ihre Kunden-Nr",
        ],
        "es": [
            "N° cliente", "No cliente", "Número cliente", "Numero cliente",
            "N° de cliente", "Número de cliente", "Numero de cliente",
            "Código cliente", "Codigo cliente",
            "Cuenta cliente", "Cuenta del cliente",
            "Dirección de entrega", "Direccion de entrega",
            "Dirección de facturación", "Direccion de facturacion",
            "Entrega a", "Facturar a", "Facturación a", "Facturacion a",
        ],
        "it": [
            "N° cliente", "Numero cliente", "Numero di cliente",
            "Codice cliente", "Codice di cliente",
            "Conto cliente",
            "Indirizzo di consegna", "Indirizzo di spedizione",
            "Indirizzo di fatturazione",
            "Consegna a", "Fatturare a", "Fatturazione a",
        ],
        "pt": [
            "N° cliente", "Numero cliente", "Número do cliente",
            "Codigo do cliente", "Código do cliente",
            "Conta do cliente",
            "Endereço de entrega", "Endereco de entrega",
            "Endereço de facturação", "Endereco de faturacao",
            "Entrega a", "Faturar a",
        ],
        "nl": [
            "Klantnummer", "Klant-Nr", "Klantcode",
            "Leveringsadres", "Verzendadres", "Factuuradres",
            "Afleveren aan",
        ],
    },
    "ORDER_REF_CLIENT": {
        "fr": [
            "Votre référence", "Votre reference",
            "Votre commande", "Votre cde",
            "Votre n° de commande", "Votre no de commande",
            "Votre n° commande", "Votre no commande",
            "N° cde client", "No cde client",
            "Réf cde", "Ref cde", "Réf commande client",
            "Vos références", "Vos references", "Vos refs",
        ],
        "en": [
            "Your order", "Your reference", "Your purchase order",
            "Your order no", "Your order number", "Your PO",
            "PO number", "P.O. number",
            "Purchase order no", "Purchase order number",
            "Customer PO", "Customer PO no",
            "Order ref", "Order reference",
        ],
        "de": [
            "Ihre Bestellung", "Ihre Bestellnummer",
            "Ihre Bestell-Nr", "Ihre Referenz",
            "Kundenbestellung", "Bestellnummer Kunde",
        ],
        "es": [
            "Su pedido", "Su referencia",
            "Pedido cliente", "N° de pedido cliente",
            "Referencia del cliente",
        ],
        "it": [
            "Vostro ordine", "Vostro numero ordine", "Vostro riferimento",
            "Vs ordine", "Vs. ordine", "Riferimento cliente",
        ],
        "pt": [
            "Vossa encomenda", "Vossa referência", "Vossa referencia",
            "Referência do cliente", "Referencia do cliente",
        ],
        "nl": [
            "Uw bestelling", "Uw referentie", "Uw ordernummer",
        ],
    },
    "AFFAIR_NUMBER": {
        "fr": [
            "N° affaire", "N° d'affaire", "No affaire",
            "Affaire", "Affaire n°",
            "N° dossier", "Dossier", "Dossier n°",
            "Réf affaire", "Ref affaire", "Réf dossier", "Ref dossier",
        ],
        "en": [
            "Project no", "Project number", "Project ref",
            "Case no", "Case number",
            "File no", "File number", "File ref",
        ],
        "de": [
            "Projektnummer", "Projekt-Nr", "Aktenzeichen",
        ],
        "es": [
            "N° expediente", "Número expediente", "Numero expediente",
        ],
        "it": [
            "N° pratica", "Numero pratica",
        ],
        "pt": [],
        "nl": [],
    },
    # Vocabulaire technique - mots qui ne sont JAMAIS PERSON/ORG/LOCATION.
    # Utilise pour le filtre R3 anti-PERSON.
    "TECH_VOCABULARY": {
        "fr": [
            "page", "ligne", "colonne", "section",
            "piece", "pieces", "pce", "pces", "pcs", "unite", "unites",
            "kg", "tonne", "metre", "litre", "carton", "lot",
            "jour", "jours", "mois", "annee", "annees", "semaine", "semaines",
            "heure", "heures", "minute",
            "numero", "reference", "designation", "description",
            "quantite", "remise", "montant", "total", "tva",
            "demandeur", "destinataire", "expediteur", "transporteur",
            "signataire", "interlocuteur", "responsable",
            "vendeur", "acheteur", "fournisseur", "client", "service",
            "contact", "commercial", "logistique",
            "date", "echeance", "livraison", "expedition", "facture",
            "commande", "rendu", "destination", "lieu", "depart",
            "franco", "incoterm", "incoterms",
        ],
        "en": [
            "page", "long", "short", "mail", "gateway", "account", "plan",
            "basic", "manager", "buyer", "seller", "vendor", "carrier",
            "shipping", "delivery", "billing", "invoice", "payment",
            "tracking", "incoterm", "amount", "total", "price", "quantity",
            "piece", "item", "unit", "qty", "each", "pack",
            "day", "week", "month", "year", "hour", "minute",
            "purchase", "order", "reference", "description", "comment",
            "destination", "location", "place",
            "company", "customer", "supplier", "contact", "person",
            "named", "warehouse",
        ],
        "de": [
            "konto", "kunde", "lieferant", "rechnung", "bestellung", "betrag",
            "menge", "preis", "artikel", "stuck",
            "tag", "woche", "monat", "jahr", "stunde",
            "ansprechpartner", "kontakt", "vertreter",
            "geliefert", "verzollt", "lieferung",
        ],
        "es": [
            "cliente", "proveedor", "factura", "pedido", "cantidad",
            "precio", "importe", "descuento", "iva",
            "dia", "semana", "mes", "ano",
            "pieza", "unidad", "destino", "lugar",
            "entrega", "facturacion",
        ],
        "it": [
            "cliente", "fornitore", "fattura", "ordine", "quantita",
            "prezzo", "importo", "sconto",
            "giorno", "settimana", "mese", "anno",
            "pezzo", "unita", "consegna", "fatturazione",
        ],
        "pt": [
            "cliente", "fornecedor", "fatura", "encomenda",
            "quantidade", "preco", "desconto",
            "dia", "semana", "mes", "ano",
            "peca", "unidade", "entrega",
        ],
        "nl": [],
    },
}


def labels_for(category: str, lang: str | None = None) -> list[str]:
    """Renvoie les libelles d'une categorie, pour une langue ou TOUTES.

    Args:
        category: nom de categorie (cle de LABELS, ex: "CLIENT_CODE").
        lang: code langue ISO 639-1 ("fr", "en", ...) ou None pour
              recevoir l'union de toutes les langues.

    Returns:
        Liste de strings (potentiellement vide). Pas de doublons garantis
        (deduplication preservant l'ordre).
    """
    if category not in LABELS:
        return []
    if lang is not None:
        return list(LABELS[category].get(lang, []))
    # Union de toutes les langues (preserve l'ordre par categorie/langue).
    seen: set[str] = set()
    out: list[str] = []
    for lang_dict in LABELS[category].values():
        for lbl in lang_dict:
            key = lbl.lower()
            if key not in seen:
                seen.add(key)
                out.append(lbl)
    return out


def categories() -> list[str]:
    """Liste des categories disponibles."""
    return list(LABELS.keys())


def languages() -> list[str]:
    """Liste des codes langue presents au moins une fois."""
    seen: set[str] = set()
    for lang_dict in LABELS.values():
        seen.update(lang_dict.keys())
    return sorted(seen)
