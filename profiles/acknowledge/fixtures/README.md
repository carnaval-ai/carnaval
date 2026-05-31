# Multilingual Test Fixtures — Acknowledgment Profile

This directory contains fictional Acknowledgment of Order documents in
8 languages, designed to test Carnaval's recognizers without using any
real customer or supplier data.

## Licence

All fixtures are released under **Apache License 2.0** (same as Carnaval).
You may freely copy, modify, and redistribute them.

## Fictional companies used

All organization names are 100% fictional, borrowed from well-known TV
series and films. They are guaranteed not to refer to any real entity :

| Name | Origin |
|------|--------|
| Globex Inc. | "The Simpsons" |
| Initech | "Office Space" |
| Vandelay Industries | "Seinfeld" |
| Soylent Corp | "Soylent Green" |
| Cyberdyne Systems | "Terminator" |
| InGen | "Jurassic Park" |
| Tyrell Corporation | "Blade Runner" |
| Acme Corp | "Looney Tunes" |

## Fictional people

All personal names are alliterative fictional pairs :

`Alice Anderson`, `Bob Brown`, `Carol Carter`, `David Davis`,
`Emma Evans`, `Frank Fischer`, `Grace Garcia`, `Henry Hudson`,
`Isabel Ibarra`, `Jose Jimenez`, `Katia Kelly`, `Lech Lewandowski`,
`Magda Malinowska`, `Naoto Nakamura`, `Oishi Yumi`, `Patrick Park`,
`Selma Sahin`.

## Fixtures available

| File | Language | Currency | VAT rate | Special features |
|------|----------|----------|----------|------------------|
| `sample_ack_globex.txt` | FR | EUR | 20% | French addresses, SIRET, RCS |
| `sample_ack_globex_en.txt` | EN | USD | 8.25% | US addresses, EIN, Net 30 |
| `sample_ack_initech_de.txt` | DE | EUR | 19% | German HRB, USt-IdNr., DAP |
| `sample_ack_vandelay_it.txt` | IT | EUR | 22% | Italian P.IVA, REA |
| `sample_ack_soylent_es.txt` | ES | EUR | 21% | Spanish CIF, Tomo |
| `sample_ack_cyberdyne_pt.txt` | PT | EUR | 23% | Portuguese NIPC |
| `sample_ack_ingen_pl.txt` | PL | PLN | 23% | Polish NIP/REGON/KRS |
| `sample_ack_tyrell_jp.txt` | JP | JPY | 10% | Japanese Reiwa era, CJK chars |
| `sample_ack_initech_tr.txt` | TR | TRY | 20% | Turkish MERSIS, Vergi No |

## Common structure

All fixtures follow the same logical structure (in the local language) :

```
- Supplier header (legal name, fiscal IDs, contact info)
- Bill-to address
- Ship-to address
- Customer purchase order reference
- Acknowledgment number
- Customer account number
- Account manager (PII)
- Order lines table (position / qty / ref / description / unit price / delivery / total)
- Subtotal, shipping, VAT, grand total
- Payment terms
- Incoterm
- Carrier
- Notes (retention of title clause)
```

This consistency allows testing the same family of recognizers across
all languages and verifying that translation does not break detection
(e.g. dates in French dd/mm/yyyy vs German dd.mm.yyyy vs ISO yyyy-mm-dd).

## How to use

```python
from carnaval.cli.anonymize import anonymize_text

with open("sample_ack_initech_de.txt", encoding="utf-8") as f:
    text = f.read()

result = anonymize_text(
    text=text,
    profile="acknowledge",
    vault_password="any_password",
    primary_language="de",
)

print(result.anonymized_text)
print(f"Detected {result.num_spans} entities across {len(result.by_category)} types")
```

Expected output (approximate, depending on recognizer threshold) :
- ~15-25 entities masked per fixture
- 6-10 distinct entity types : `FOURNISSEUR`, `CLIENT_NAME`, `ADRESSE`,
  `EMAIL`, `PHONE`, `VAT`, `SIREN/SIRET/HRB/NIP`, `CONTACT`, `REF_COMMANDE_CLIENT`

## Adding a new language

1. Pick a fictional company name from the list (or add one to the
   `deny_lists/organizations.yaml`).
2. Translate the common structure above into the target language.
3. Use plausible local fiscal identifiers in the correct format :
   - FR : SIRET 14 digits, TVA `FR\d{11}`
   - DE : USt-IdNr. `DE\d{9}`
   - PL : NIP 10 digits, REGON 9 digits, KRS 10 digits
   - JP : 法人番号 `\d{13}`, vary period reference (Reiwa, Heisei, Gregorian)
   - ...
4. Add a row in this README's "Fixtures available" table.
5. Add a regression test in `carnaval/tests/test_recognizers_<lang>.py`.

## Validation

Each fixture has been hand-validated to ensure :
- no real-world entity is referenced ;
- fiscal IDs use valid format but are not actual registered numbers ;
- street addresses use generic placeholders ;
- phone numbers use reserved test ranges where possible
  (e.g. `+1 212 555 0199` is a reserved exchange in US).
