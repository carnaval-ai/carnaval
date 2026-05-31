# `acknowledge` Profile

Anonymization of **supplier order acknowledgements** (OAs).

## Use case

A customer sends an order to a supplier. The supplier returns a confirmation
PDF (the acknowledgement). The customer extracts the text and wants it
processed by a cloud LLM to extract structured data, without sending in
cleartext:
- The supplier name
- Sales contacts
- Bank details
- Addresses

The following, however, must be **preserved**:
- The order number (for business reconciliation)
- Product references
- Amounts
- Lead times

## Masked entities

| Type | Primary detector |
|---|---|
| PERSON | GLiNER + NameCommaRegex + Honorifics |
| ORGANIZATION | DenyList `deny_lists/organizations.yaml` + GLiNER fallback |
| EMAIL | Regex |
| PHONE | FR regex |
| LOCATION | GLiNER + PostalCity + Zone |
| IBAN/BIC | Regex + checksum |
| VAT/SIRET/SIREN | Regex |

## Bundled fictional data

The profile ships with **fictional** data (Apache 2.0) for testing:
- Suppliers: Globex Inc., Initech, Vandelay Industries
- People: Alice Anderson, Bob Brown, Carol Carter
- Addresses: generic business parks in France

## Overriding with your real data

See `profiles_private/README.md` to clone this profile with your actual
suppliers / contacts without exposing them in a public repo.

## Test fixtures

`fixtures/sample_ack_globex.txt`: representative fictional OA.

---
Author : Patrice Aubert