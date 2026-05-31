# 08 - Input and output formats

## Input

### Raw .txt file

- Encoding: UTF-8 (automatic latin-1 fallback)
- Max size: 50 MB by default (configurable)
- No imposed structure: raw text

Example:
```
Hello Alice Anderson,
Your order from Globex Inc. is confirmed.
Contact: alice@globex.example
```

## Simultaneous outputs

A single anonymization pass produces **6 formats** in `outbox/`:

### 1. TXT - `outbox/txt/<stem>_anonymise.txt`

Text with tags, ready to pipe to an LLM.

```
Hello [PERSON_1],
Your order from [ORG_1] is confirmed.
Contact: [EMAIL_1]
```

### 2. JSON - `outbox/json/<stem>_anonymise.json`

Exploitable structure for APIs.

```json
{
  "anonymized_text": "Hello [PERSON_1]...",
  "language": "fr",
  "entities": [
    {
      "start": 8,
      "end": 22,
      "type": "PERSON",
      "placeholder": "[PERSON_1]",
      "score": 0.95,
      "recognizer": "GLiNER"
    }
  ],
  "by_category": {"PERSON": 1, "ORGANIZATION": 1, "EMAIL": 1},
  "source": "/path/inbox/doc.txt"
}
```

### 3. JSONL - `outbox/jsonl/<stem>_entities.jsonl`

One entity per line, streaming-friendly.

```jsonl
{"start": 8, "end": 22, "type": "PERSON", "placeholder": "[PERSON_1]", "score": 0.95, "recognizer": "GLiNER"}
{"start": 40, "end": 51, "type": "ORGANIZATION", "placeholder": "[ORG_1]", "score": 1.0, "recognizer": "OrganizationsDenyList"}
```

### 4. XML - `outbox/xml/<stem>_anonymise.xml`

Legacy / EDI integration.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<anomarkResult>
  <anonymizedText>Hello [PERSON_1]...</anonymizedText>
  <language>fr</language>
  <source>/path/inbox/doc.txt</source>
  <byCategory>
    <category name="PERSON">1</category>
    <category name="ORGANIZATION">1</category>
  </byCategory>
  <entities>
    <entity start="8" end="22" type="PERSON" placeholder="[PERSON_1]" .../>
  </entities>
</anomarkResult>
```

### 5. CoNLL - `outbox/conll/<stem>_anonymise.conll`

CoNLL-2003 BIO format for NER model training.

```
Hello O

Alice B-PERSON
Anderson I-PERSON

Your O
order O
from O
Globex B-ORGANIZATION
Inc. I-ORGANIZATION
```

### 6. HTML - `outbox/html/<stem>_anonymise.html`

Interactive visualization with colorized spans. Useful for debug and
functional reviews.

## Vault and metadata

### Vault - `outbox/vault/<stem>_vault.enc`

AES-256-GCM encrypted binary file. Essential for reinjection.

### Meta - `outbox/meta/<stem>_meta.json`

Non-sensitive audit.

```json
{
  "source": "/path/inbox/doc.txt",
  "language": "fr",
  "num_spans": 3,
  "by_category": {"PERSON": 1, "ORGANIZATION": 1, "EMAIL": 1},
  "outputs": {
    "txt": "...",
    "json": "...",
    "...": "..."
  },
  "timestamp": 1715680000.0,
  "duration_seconds": 12.5
}
```

## Re-injection: supported input formats

S7 accepts JSON and XML. Auto-detection by the first character:

| First char | Detected format |
|---|---|
| `{` or `[` | JSON |
| `<` | XML |
| Other | Raw text |

### JSON example

```bash
# Sonnet response
cat > response.json <<EOF
{
  "supplier": "[ORG_1]",
  "contact": "[PERSON_1]",
  "amount": 1200
}
EOF

python reinject.py response.json --vault outbox/vault/doc_vault.enc
```

Produces `response_final.json`:
```json
{
  "supplier": "Globex Inc.",
  "contact": "Alice Anderson",
  "amount": 1200
}
```

### XML example

```bash
cat > response.xml <<EOF
<order>
  <supplier>[ORG_1]</supplier>
  <contact email="[EMAIL_1]">[PERSON_1]</contact>
</order>
EOF

python reinject.py response.xml --vault outbox/vault/doc_vault.enc
```

Produces `response_final.xml`:
```xml
<order>
  <supplier>Globex Inc.</supplier>
  <contact email="alice@globex.example">Alice Anderson</contact>
</order>
```

XML attributes, element text and tails are all processed.

## Add a custom output format

Edit `src/carnaval/core/serializers.py`, add a function
`to_<format>(doc: MaskedDocument) -> str`. Wire it in
`stages/s6_output.py`.

Ideas for additional formats:
- **Markdown** with annotations
- **YAML** for configuration
- **CSV** for spreadsheet (1 row = 1 entity)
- **OWL/RDF** for knowledge graph
