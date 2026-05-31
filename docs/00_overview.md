# 00 - Overview

## What problem does carnaval solve

You want to use a cloud LLM (Sonnet, GPT, Mistral...) to process
text documents containing personal or confidential data:
- Supplier acknowledgments of receipt
- Invoices
- Professional emails
- Contracts, CVs, medical records, ...

**Problem**: these documents contain sensitive entities (names,
emails, IBANs, addresses) that must not be sent in clear to
an external service.

**Carnaval solution**:

```
RAW DOCUMENT --> [carnaval] --> TAGGED DOCUMENT --> cloud LLM
                                                          |
FINAL DOCUMENT <-- [carnaval] <-- JSON/XML response <------+
```

1. **Before sending**: replace sensitive entities with tags
   `[PERSON_1]`, `[EMAIL_2]`, `[ORG]`, etc. Store the mappings in a
   locally encrypted vault.
2. **After the response**: restore the original values in the
   returned JSON or XML structure.

## Principles

### 1. Reversibility

Each masked entity is associated with a unique placeholder. The mapping
is stored encrypted (AES-256-GCM) on the local disk. Without the password,
it is impossible to retrieve the original values.

### 2. Consistency

The same original value always receives the **same** placeholder in a
run. Example: "Alice Doe" appears 5 times in the text? -> 5 times
`[PERSON_1]`. The LLM can therefore reason about references.

### 3. Locality

No network call for anonymization. GLiNER runs locally (model
~500 MB downloaded once). Lingua for language detection. Everything runs on your
machine.

### 4. Multi-format

A single anonymization pass produces the result in 6 common formats:
- **TXT**: raw text with tags (for piping to LLM)
- **JSON**: exploitable structure (text + entities)
- **JSONL**: streaming (1 entity per line)
- **XML**: legacy SI / EDI integration
- **CoNLL**: NER model training
- **HTML**: colorized visualization for debug

### 5. Modular by stages

The pipeline consists of 7 autonomous stages. Each stage has a clear contract
(input -> output) and can be tested, replaced or debugged in
isolation.

### 6. Business profiles

A profile describes a **document type** (acknowledge, invoice, email...)
with its typical entities, deny lists, arbitration rules.
Profiles are editable YAML files without touching the code.

### 7. No magic

No opaque framework between the user and the pipeline. Each
recognizer is a **pure Python function** that takes text and returns
Spans. No inheritance, no class hierarchy, no implicit hook.

## What carnaval does not do

- **No OCR**: input = already extracted text. To extract from a PDF,
  use an upstream tool (pdfplumber, pypdf, tesseract...).
- **No LLM call**: carnaval prepares and restores, the network call
  is your responsibility.
- **No built-in batch**: one file at a time. To process in batch,
  write a shell or Python loop around `anonymize.py`.

## To go further

- [01_architecture_etages.md](01_architecture_etages.md) - the pipeline
  in detail
- [04_configuration.md](04_configuration.md) - configuration and profiles
- [07_securite.md](07_securite.md) - the vault and the password
