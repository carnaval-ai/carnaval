# Profils metier carnaval

Un profil represente un **type de document** : ses entites typiques, ses
champs metier a preserver, ses regles d'arbitrage.

## Profils livres

| Profil | Type de document | Cas d'usage |
|---|---|---|
| `acknowledge/` | Accuse de reception (AR) fournisseur | Confirmation de commande, livraison |
| `invoice/` | Facture / note d'honoraires | Comptabilite, paiement |
| `email/` | Email professionnel | Communication B2B |

## Utilisation

```bash
python anonymize.py inbox/doc.txt --profile acknowledge
```

Le profil applique :
- ses `deny_lists/` (organisations, personnes typiques du domaine)
- ses `allow_lists/` (champs metier specifiques, anti faux positifs)
- ses `patterns/` (regex propres au type)
- ses `policies/` (regles d'arbitrage)

## Creer un nouveau profil

1. Copier un profil existant : `cp -r profiles/acknowledge profiles/mon_profil`
2. Editer `profiles/mon_profil/profile.yaml` (description, langue, etc.)
3. Adapter les YAML dans `deny_lists/`, `allow_lists/`, etc.
4. Ajouter des fixtures fictives dans `fixtures/` pour test
5. Lancer : `python anonymize.py mon_doc.txt --profile mon_profil`

## Profils prives (clients finaux)

Les fournisseurs/personnes/donnees reelles d'un client final ne doivent
**jamais** apparaitre dans les profils publics. Utiliser `profiles_private/`
qui est git-ignore par defaut :

```
profiles_private/
|-- mon_client/
|   |-- profile.yaml          # extends: acknowledge
|   |-- deny_lists/
|   |   `-- organizations.yaml  # vrais fournisseurs du client
|   `-- ...
```

Lancement : `python anonymize.py doc.txt --profile acknowledge --private mon_client`
