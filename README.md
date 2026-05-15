<p align="center">
  <img src="assets/carnaval-mask.svg" width="240" alt="Carnaval mask">
</p>

<h1 align="center">Carnaval</h1>

<p align="center"><em>The art of the mask - hide the identity, keep the meaning.</em></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/status-functional%20POC-orange.svg" alt="Status">
</p>

**Carnaval** is an open-source Python framework for **reversible PII anonymization**.
It masks sensitive entities in text documents *before* they are sent to a cloud
LLM, then restores the original values in the structured response the LLM returns.

---

## The problem

You want to use a cloud LLM (Claude, GPT, Mistral, Gemini...) to process text
documents - order acknowledgements, invoices, business emails, contracts - but
those documents contain personal or confidential data that must never leave
your infrastructure in clear text.

## The solution

```
RAW DOCUMENT  ──▶  [ Carnaval ]  ──▶  MASKED DOCUMENT  ──▶  Cloud LLM
                                                                │
FINAL DOCUMENT  ◀──  [ Carnaval ]  ◀──  JSON / XML response  ◀──┘
```

1. **Before sending** - sensitive entities are replaced with placeholders such
   as `[PERSON_1]`, `[EMAIL_2]`, `[ORG]`. The placeholder ↔ real-value mapping
   is stored in an **encrypted local vault**.
2. **After the response** - the original values are re-injected into the JSON
   or XML structure returned by the LLM.

No data ever leaves your machine in clear text, and the LLM still receives a
coherent, structured document it can reason about.

---

## Key features

- **Reversible** - every masked entity maps to a unique placeholder; the mapping
  lives in an AES-256-GCM encrypted vault.
- **Coherent** - the same value always receives the same placeholder within a
  run, so the LLM can reason about cross-references.
- **Local-first** - no network calls to anonymize. The optional neural model
  runs on your own machine.
- **9 entity types** - `PERSON`, `ORGANIZATION`, `LOCATION`, `EMAIL`, `PHONE`,
  `IBAN`, `BIC`, `VAT`, `SIREN`/`SIRET`, `URL`.
- **Layered detection** - regex recognizers, deny lists, bundled dictionaries
  (GeoNames cities, first names), and an optional zero-shot neural recognizer
  (GLiNER).
- **Multilingual** - 6 languages: French, English, German, Spanish, Italian,
  Portuguese.
- **Business profiles** - `acknowledge`, `invoice`, `email`, plus private
  per-client profiles kept out of version control.
- **8 output formats** - TXT, JSON, JSONL, XML, CoNLL, HTML, encrypted vault,
  audit metadata - all produced in a single pass.
- **CLI and library** - use the `anonymize.py` / `reinject.py` scripts, or
  import `carnaval` directly into your Python code.

---

## Pipeline

Carnaval is built as **7 self-contained stages**, each with a clear
input → output contract:

```
TXT ──▶ S1 Intake ──▶ S2 Preprocess ──▶ S3 Detect ──▶ S4 Resolve ──▶ S5 Mask ──▶ S6 Output
        (read)        (language,         (recognizers)  (dedup,        (placeholders  (8 formats)
                       normalize)                        arbitration)   + vault)

JSON / XML ──▶ S7 Reinject ──▶ JSON / XML with original values restored
```

See [Architecture](wiki/Architecture.md) for details on each stage.

---

## Installation

Requires **Python 3.11+** (tested on 3.13).

```bash
git clone <repository-url>
cd carnaval

python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

The neural recognizer (GLiNER) is included in `requirements.txt`. The model
(~500 MB) is downloaded automatically on first use; afterwards Carnaval works
fully offline. See the [Installation guide](wiki/Installation.md) for an
offline / air-gapped setup.

### Configure the vault password

```bash
cp .env.example .env
```

Then edit `.env` and set a strong secret (16 characters minimum, 32+ recommended):

```
CARNAVAL_VAULT_PASSWORD=a-strong-randomly-generated-secret
```

---

## Quickstart - CLI

```bash
# 1. Anonymize a document
python anonymize.py inbox/order.txt --profile acknowledge

# 2. Send outbox/txt/order_anonymise.txt to your LLM, collect a JSON response

# 3. Re-inject the real values into the LLM response
python reinject.py response.json --vault outbox/vault/order_vault.enc
```

`anonymize.py` produces, in one pass, all 8 output files under `outbox/`
(`txt/`, `json/`, `jsonl/`, `xml/`, `conll/`, `html/`, `vault/`, `meta/`).

Useful flags: `--no-gliner` (regex + deny lists only, faster),
`--gliner-threshold 0.6`, `--profile invoice`, `--private my_client`,
`--console` (human-readable logs).

---

## Quickstart - Python API

```python
from pathlib import Path
from carnaval.pipeline import run_anonymization

masked, written, config = run_anonymization(
    input_path=Path("inbox/order.txt"),
    outbox_dir=Path("outbox"),
    vault_password="a-strong-randomly-generated-secret",
    profile="acknowledge",
    use_gliner=True,
)

print(masked.anonymized_text)      # text with placeholders
print(masked.by_category)          # {'PERSON': 2, 'ORGANIZATION': 1, ...}
print(written.json_path)           # path to the JSON output
```

Re-injecting an LLM response:

```python
from carnaval.core.vault import Vault
from carnaval.stages.s7_reinject import reinject_json_data

vault = Vault(password="a-strong-randomly-generated-secret",
              path="outbox/vault/order_vault.enc")
vault.load()

llm_response = {"supplier": "[ORG_1]", "contact": "[PERSON_1]"}
restored = reinject_json_data(llm_response, vault)
# {"supplier": "Globex Inc.", "contact": "Jane Doe"}
```

See the [Quickstart](wiki/Quickstart.md) and [Reinjection](wiki/Reinjection.md)
wiki pages for more.

---

## Security

The placeholder ↔ value mapping is stored in an encrypted vault:

| Property | Value |
|---|---|
| Symmetric cipher | AES-256-GCM (authenticated encryption) |
| Key derivation | PBKDF2-HMAC-SHA256, 600,000 iterations |
| Salt | 16 random bytes per file |
| Nonce | 16 random bytes per file |
| Integrity tag | 16 bytes - any tampering is detected on read |

Without the password, the vault is unreadable. Carnaval makes **no outbound
network calls** once the GLiNER model has been downloaded, and its structured
logger redacts sensitive keys by default. It supports GDPR-style
**pseudonymization** (Article 4.5). See [Vault and Security](wiki/Vault-and-Security.md).

---

## Supported languages

French (FR), English (EN), German (DE), Spanish (ES), Italian (IT) and
Portuguese (PT). The language is auto-detected; mixed-language documents are
handled via in-text linguistic markers. See [Multilingual](wiki/Multilingual.md).

---

## Project status

Carnaval is a **functional proof of concept**. Core anonymization,
re-injection, the encrypted vault and the 8 output formats are implemented and
covered by an extensive automated test suite.

## Testing

```bash
pytest                       # full suite (skips slow neural tests)
pytest -m slow               # real GLiNER tests (downloads the model)
pytest --cov=src/carnaval    # with coverage
```

---

## Documentation

The complete reference lives in the **[project wiki](wiki/Home.md)**:

- [Home](wiki/Home.md) - overview and table of contents
- [Installation](wiki/Installation.md)
- [Quickstart](wiki/Quickstart.md)
- [Architecture](wiki/Architecture.md)
- [Vault and Security](wiki/Vault-and-Security.md)
- [Profiles](wiki/Profiles.md)
- [Recognizers](wiki/Recognizers.md)
- [Multilingual](wiki/Multilingual.md)
- [Output Formats](wiki/Output-Formats.md)
- [Reinjection](wiki/Reinjection.md)
- [Troubleshooting](wiki/Troubleshooting.md)
- [Contributing](wiki/Contributing.md)

The original design notes are kept under [`docs/`](docs/).

---

## Contributing

Contributions are welcome - see [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md). Please use only fictitious entities
(Acme Corp, Globex, Jane Doe, Springfield...) in public fixtures and examples.

## Contact & Security

- General questions, conduct reports: **carnaval.oss@gmail.com**
- Bug reports and feature requests: GitHub issues
- Security vulnerabilities: please **do not** open a public issue - see
  [SECURITY.md](SECURITY.md) for responsible disclosure.

## License

Carnaval is released under the **Apache License 2.0**. See [LICENSE](LICENSE).
