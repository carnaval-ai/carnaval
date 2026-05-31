# carnaval

[![CI](https://github.com/carnaval-ai/carnaval/actions/workflows/ci.yml/badge.svg)](https://github.com/carnaval-ai/carnaval/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/carnaval-ai/carnaval/branch/master/graph/badge.svg)](https://codecov.io/gh/carnaval-ai/carnaval)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> *The art of masking: concealing identity, preserving the essentials.*

**carnaval** is a **reversible** Python framework for text-document anonymization. It masks sensitive entities (people, organizations, emails, phone numbers, bank identifiers, etc.) before sending them to a cloud LLM, and restores the original values in the structured response (JSON or XML) on the way back.

## Status: Stable (Beta) — v0.2.0

- License: **Apache 2.0**
- Stack: Python 3.11 / 3.12 / 3.13, GLiNER (zero-shot NER), regex, AES-256-GCM
- **No external PII framework** (no Presidio, no spaCy NER)
- 184 tests passing, ~95% coverage, mypy-checked, CI on every push
- Used internally in production at one enterprise (anonymization of supplier acknowledgments before LLM extraction). Public API may evolve until v1.0.

## Quick Start

```bash
# 1. Installation
git clone <repo>
cd carnaval
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# or: .\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Edit .env and set CARNAVAL_VAULT_PASSWORD=<32+ characters>

# 3. Anonymization
python anonymize.py inbox/my_document.txt --profile acknowledge

# 4. Reinjection (after LLM processing)
python reinject.py response_llm.json --vault outbox/vault/my_document_vault.enc
```

## 7-Stage Architecture

```
Raw TXT --> S1 Intake
        --> S2 Preprocess (language, normalization)
        --> S3 Detect (regex + denylist + GLiNER)
        --> S4 Resolve (dedup, arbitration)
        --> S5 Mask (placeholders + encrypted vault)
        --> S6 Output (6 formats: txt/json/jsonl/xml/conll/html)

JSON/XML --> S7 Reinject --> JSON/XML with original values
```

## Out-of-the-box Business Profiles

| Profile | Document Type |
|---|---|
| `acknowledge` | Supplier order acknowledgment |
| `invoice` | Invoice / professional fee note |
| `email` | B2B professional email |

Private profiles (real client data) in `profiles_private/` (git-ignored).

## Documentation

| Doc | Topic |
|---|---|
| [docs/00_overview.md](docs/00_overview.md) | Overview, principles |
| [docs/01_architecture_etages.md](docs/01_architecture_etages.md) | The 7 stages in detail |
| [docs/02_install.md](docs/02_install.md) | Installation |
| [docs/03_deploiement_production.md](docs/03_deploiement_production.md) | Production |
| [docs/04_configuration.md](docs/04_configuration.md) | YAML config + profiles |
| [docs/05_extension_listes.md](docs/05_extension_listes.md) | Adding entities to mask |
| [docs/06_extension_recognizers.md](docs/06_extension_recognizers.md) | Coding a new recognizer |
| [docs/07_securite.md](docs/07_securite.md) | Vault, password, audit |
| [docs/08_format_entree_sortie.md](docs/08_format_entree_sortie.md) | Supported formats |
| [docs/09_troubleshooting.md](docs/09_troubleshooting.md) | Common errors |
| [docs/10_api_reference.md](docs/10_api_reference.md) | Python API |

## Tests

```bash
pytest                          # all (except slow)
pytest -m slow                  # real AI tests (downloads GLiNER ~500 MB)
pytest --cov=src/carnaval       # coverage
```

## Contributing

Apache 2.0. Issues and PRs welcome. No personal or client data in public fixtures: use only fictitious entities (Acme Corp, Globex, Initech, etc.).
