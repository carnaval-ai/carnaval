# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizer de code client a format variable (VN3).

Vecteur d'attaque red-team v2 VN3 : les codes clients identifient le
destinataire dans le systeme ERP du fournisseur. Formats observes :
    C0001065 / C104714 / C104715 / C104716   (prefixe C + chiffres)
    DM000888                                  (prefixe DM)
    1DEL3661 / 10003661                       (codes adresse Linx)
    2842074 / 53309 / 121604                  (purement numeriques)

Strategie : capture par libelle contextuel ferme. Les libelles sont
specifiques (N° client / Sold to / Code client / etc.) ce qui rend
le faux positif rare. La valeur peut etre tout code alphanumerique
3-15 chars contenant au moins 3 chiffres.
"""

from __future__ import annotations

import re

from carnaval.core.span import Span


# Libelles de code client (multilingue).
_CLIENT_LABEL = (
    r"(?:"
    # FR - libellés "N° client" + suffixes (audit v3 R3) :
    # facturé / livré / commandé sont des qualificatifs du client cible.
    # Le suffixe est valide à 30 chars max après "N° client" pour
    # absorber le qualificatif sans dériver.
    # Audit v5-bis : accepte aussi "No.Client" (point sans espace) et
    # "N°Client" (sans espace), "N° De Client", etc.
    r"N[°o]\.?\s*(?:de\s+)?client(?:\s+(?:factur[ée]|livr[ée]|command[ée]))?"
    r"|N[°o]\.?\s+client(?:\s+(?:factur[ée]|livr[ée]|command[ée]))?"
    r"|No\.\s*client"
    # Audit v5-bis : variante "Client n° :" / "Client no" (ordre inverse).
    # Aussi "Client" tout seul en libelle de colonne tabulaire.
    r"|Client\s+n[°o]\.?"
    r"|Client\s+no\.?\b"
    r"|Code\s+client(?:\s+(?:factur[ée]|livr[ée]|command[ée]))?"
    r"|N[°o]\s*(?:de\s+)?compte\s+client"
    r"|Compte\s+client"
    r"|Compte\s+adresse"
    r"|Compte\s+de\s+(?:facturation|livraison)"
    r"|Compte\s+fournisseur"
    # Audit v5-bis : "Votre (numéro de) compte RS", "N° de compte RS"
    # (= n° compte client chez fournisseur RS / Lyreco / etc.)
    r"|(?:Votre\s+)?Num[ée]ro\s+de\s+compte(?:\s+[A-Z]{2,5})?"
    r"|(?:Votre\s+)?N[°o]\s+de\s+compte(?:\s+[A-Z]{2,5})?"
    r"|(?:Votre\s+)?compte\s+[A-Z]{2,5}\b"
    r"|Num[ée]ro\s+(?:de\s+)?client"
    r"|N[°o]\s+fournisseur"
    r"|Code\s+fournisseur"
    r"|No\.?\s*fournisseur"
    r"|Num\.?\s+fournisseur"
    r"|Dossier(?:\s+n[°o]\.?)?(?!\s+suivi)"
    r"|Compte"
    r"|N[°o]\s*RS"
    r"|R[ée]f\.?\s*RS"
    r"|Donneur\s+d['’]ordre"
    r"|Adresse\s+(?:de\s+)?livraison"
    # Audit v5-bis : "Livraison à : 40074554", "Client livré : 40074554",
    # "Livré à: 9900012863", "Destinataire facture", "Client livraison",
    # "LIVRAISON A:" / "FACTURATION A:" (variantes majuscules sans accent).
    r"|Livraison\s+[àaAÀ]"
    r"|Facturation\s+[àaAÀ]"
    r"|Livr[ée]\s+[àaAÀ]"
    r"|Facturer?\s+[àaAÀ]"
    r"|Factur[ée]\s+[àaAÀ]"
    r"|Adress[ée]\s+[àaAÀ]"
    r"|Client\s+(?:livr[ée]|factur[ée]|command[ée])"
    r"|Destinataire\s+(?:facture|facturation|livraison)"
    r"|Receptionnaire\s+facture"
    # EN (enrichi v6 - symetrie multilingue)
    r"|Sold\s+to"
    r"|Bill\s+to"
    r"|Ship\s+to"
    r"|Delivery\s+(?:to|address)"
    r"|Billing\s+(?:to|address)"
    r"|Invoice\s+(?:to|address)"
    r"|Customer\s+(?:no|number|code|account|id|reference|ref\.?)"
    r"|Customer\s+account\s+(?:no|number|code)"
    r"|Account\s+(?:no|number|code|holder|reference)"
    r"|Client\s+(?:no|number|code|id|reference)"
    r"|Acct\.?\s*no"
    r"|Your\s+(?:customer\s+)?(?:no|number|code|account|reference)"
    r"|Recipient\s+(?:no|number|code)"
    r"|Buyer\s+(?:no|number|code)"
    # DE (enrichi v6 - symetrie multilingue)
    r"|Kundennummer|Kunden-Nr\.?|Kunden\s+Nr\.?"
    r"|Konto-?Nr\.?|Kontonummer"
    r"|Kundenkonto"
    r"|Rechnungsempf[äa]nger"
    r"|Rechnungsadresse"
    r"|Lieferadresse|Lieferanschrift"
    r"|Liefer[uü]ng\s+an"
    r"|Versand\s+an"
    r"|Ihre\s+Kunden(?:nummer|-Nr\.?)"
    # ES (enrichi v6 - symetrie multilingue)
    r"|N[°ºo]\.?\s*(?:de\s+)?cliente"
    r"|N[°ºo]\.?cliente"
    r"|C[óo]digo\s+(?:de\s+)?cliente"
    r"|Direcci[óo]n\s+(?:de\s+)?(?:entrega|env[íi]o|facturaci[óo]n)"
    r"|Entrega\s+a"
    r"|Facturaci[óo]n\s+a"
    r"|Facturar\s+a"
    r"|Cuenta\s+(?:de\s+)?cliente"
    # IT (enrichi v6 - symetrie multilingue)
    r"|N[°o]\.?\s*(?:di\s+)?cliente"
    r"|Codice\s+(?:di\s+)?cliente"
    r"|Indirizzo\s+(?:di\s+)?(?:consegna|spedizione|fatturazione)"
    r"|Consegna\s+a"
    r"|Fatturazione\s+a"
    r"|Fatturare\s+a"
    r"|Conto\s+cliente"
    # PT (enrichi v6 - symetrie multilingue)
    r"|N[°ºo]\.?\s*(?:de\s+)?cliente"
    r"|C[óo]digo\s+(?:do\s+)?cliente"
    r"|Endere[çc]o\s+(?:de\s+)?(?:entrega|envio|factura[çc][ãa]o|faturamento)"
    r"|Entrega\s+a"
    r"|Faturar\s+a"
    r"|Conta\s+(?:do\s+)?cliente"
    # NL (Pays-Bas, AR de fournisseurs neerlandais frequents en Europe)
    r"|Klantnummer|Klant-?Nr\.?"
    r"|Klantcode"
    r"|Leveringsadres|Verzendadres"
    r"|Factuuradres"
    r"|Afleveren\s+aan"
    r")"
)

# Valeur : code alphanum 3-15 chars contenant au moins 3 chiffres.
# Audit v5-bis : le lookahead enforce le min 3 chiffres directement dans
# la regex, sinon un mot alphabetique adjacent (autre label) est consume
# comme valeur et empeche `finditer` de trouver le bon match suivant.
_VALUE = r"(?P<value>(?=[A-Z0-9\-/]*\d[A-Z0-9\-/]*\d[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{2,14})"

# Separateur : accepte 0 a 3 caracteres de ponctuation (`: :`, `: -`, etc.)
# entoure d'espaces. Audit v5-bis : layout PDF avec separateurs doublons.
# Tolere aussi UNE ligne intermediaire de "label PO" entre le libelle
# client et la valeur (cluster vertical avec ordre inverse), cas 990cfb17.
#
# AUDIT v8 (mai 2026) : la ligne intermediaire NE DOIT PAS etre un libelle
# de document fournisseur (Accuse de reception, Confirmation de commande,
# Auftragsbestaetigung, Order confirmation, Numero du document...). Si on
# l'absorbe comme separateur, on capture le NUMERO AR comme code client
# (faux positif observe sur Sick : "Sold to / Accuse de reception / 2842074").
_AR_DOC_LABELS_NEG = (
    r"(?!\s*(?:"
    r"Accus[ée]\s+de\s+r[ée]ception"
    r"|Confirmation\s+de\s+commande"
    r"|Confirmation\s+Commande"
    r"|Auftragsbest[äa]tigung"
    r"|Bestellbest[äa]tigung"
    r"|Order\s+confirmation"
    r"|Acknowledgment\s+of\s+order"
    r"|Sales\s+confirmation"
    r"|Num[ée]ro\s+du\s+document"
    r"|Notre\s+AR"
    r"|Doc\.?\s*Vente"
    r"|Conferma\s+d['']?ordine"
    r"|Confirmaci[óo]n\s+de\s+pedido"
    r"|Confirma[çc][ãa]o\s+de\s+encomenda"
    r"))"
)

_PATTERN = re.compile(
    rf"(?i){_CLIENT_LABEL}"
    r"[\s:#.\-/]*"
    # Skip optionnel d'1 ligne intermediaire (max 50 chars, finissant par
    # : ou \n, sans chiffres en fin) MAIS PAS si cette ligne est un
    # libelle de document AR/Confirmation (cf. negative lookahead).
    rf"(?:{_AR_DOC_LABELS_NEG}[A-Za-zéèà][^\n0-9]{{0,50}}[:\n])?"
    r"[\s:#.\-/]*"
    rf"{_VALUE}\b"
)


def _has_min_digits(value: str, minimum: int = 3) -> bool:
    return sum(1 for c in value if c.isdigit()) >= minimum


def recognize_client_code(text: str, score: float = 0.88) -> list[Span]:
    """Detecte les codes clients dans le systeme ERP du fournisseur.

    Args:
        text: texte source.
        score: confiance.

    Returns:
        Liste de Span de type CLIENT_CODE.
    """
    spans: list[Span] = []
    for m in _PATTERN.finditer(text):
        value = m.group("value")
        if not _has_min_digits(value, 3):
            continue
        # Eviter de matcher les libelles fiscaux confondus
        if value.upper() in {"TVA", "VAT", "SIRET", "SIREN", "EUR", "USD"}:
            continue
        start, end = m.span("value")
        spans.append(
            Span(
                start=start, end=end,
                entity_type="CLIENT_CODE",
                text=value,
                score=score,
                recognizer="ClientCodeRegex",
            )
        )
    return spans
