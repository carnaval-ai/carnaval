# Profil `acknowledge`

Anonymisation d'**accuses de reception fournisseur** (AR).

## Cas d'usage

Un client envoie une commande a un fournisseur. Le fournisseur retourne un
PDF de confirmation (AR). Le client extrait le texte et veut le faire
traiter par un LLM cloud pour extraire les donnees structurees, sans envoyer
en clair :
- Le nom du fournisseur
- Les contacts commerciaux
- Les coordonnees bancaires
- Les adresses

Il faut en revanche **preserver** :
- Le numero de commande (pour le rattachement metier)
- Les references produit
- Les montants
- Les delais

## Entites masquees

| Type | Detecteur principal |
|---|---|
| PERSON | GLiNER + NameCommaRegex + Civilites |
| ORGANIZATION | DenyList `deny_lists/organizations.yaml` + GLiNER fallback |
| EMAIL | Regex |
| PHONE | Regex FR |
| LOCATION | GLiNER + PostalCity + Zone |
| IBAN/BIC | Regex + checksum |
| VAT/SIRET/SIREN | Regex |

## Donnees fictives livrees

Le profil contient des donnees **fictives** (Apache 2.0) pour tests :
- Fournisseurs : Globex Inc., Initech, Vandelay Industries
- Personnes : Alice Anderson, Bob Brown, Carol Carter
- Adresses : zones d'activite genericiques en France

## Surcharger pour vos donnees reelles

Voir `profiles_private/README.md` pour cloner ce profil avec vos vrais
fournisseurs / contacts sans les exposer dans un repo public.

## Fixtures de test

`fixtures/sample_ack_globex.txt` : AR fictif representatif.
