# carnaval business profiles

A profile represents a **document type**: its typical entities, the business
fields to preserve, and its arbitration rules.

## Bundled profiles

| Profile | Document type | Use case |
|---|---|---|
| `acknowledge/` | Supplier order acknowledgement (OA) | Order confirmation, delivery |
| `invoice/` | Invoice / fee note | Accounting, payment |
| `email/` | Professional email | B2B communication |

## Usage

```bash
python anonymize.py inbox/doc.txt --profile acknowledge
```

The profile applies:
- its `deny_lists/` (organizations, people typical of the domain)
- its `allow_lists/` (specific business fields, false-positive guards)
- its `patterns/` (regex specific to the type)
- its `policies/` (arbitration rules)

## Creating a new profile

1. Copy an existing profile: `cp -r profiles/acknowledge profiles/my_profile`
2. Edit `profiles/my_profile/profile.yaml` (description, language, etc.)
3. Adapt the YAML files in `deny_lists/`, `allow_lists/`, etc.
4. Add fictional fixtures in `fixtures/` for testing
5. Run: `python anonymize.py my_doc.txt --profile my_profile`

## Private profiles (end customers)

The real suppliers / people / data of an end customer must **never** appear
in the public profiles. Use `profiles_private/`, which is git-ignored by
default:

```
profiles_private/
`-- my_client/
    |-- profile.yaml            # extends: acknowledge
    |-- deny_lists/
    |   `-- organizations.yaml  # the client's real suppliers
    `-- ...
```

Run: `python anonymize.py doc.txt --profile acknowledge --private my_client`

---
Author: Patrice Aubert