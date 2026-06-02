# Test Suite & Validation Corpus Guide

This directory contains the automated test suite for **carnaval**. The test suite is designed to ensure compliance, stability, and cryptographic reversibility without leaking any customer PII.

---

## 📂 Directory Structure

```text
tests/
├── conftest.py          # Global path helper and sharing configurations
├── test_template.py     # Boilerplate code for new unit/integration tests (copy-paste)
├── unit/                # Unit tests for core components and pipeline stages
│   ├── test_span.py     # Offsets and text span arithmetic
│   ├── test_vault.py    # AES-256-GCM vault key-derivation and load/save
│   └── test_s1_...py    # Step-by-step unit testing for Stage 1 to 7
├── recognizers/         # Neural (GLiNER) and regex-based entity recognizers
└── integration/         # End-to-end integration tests using business profiles
    └── test_profiles.py # Runs the pipeline on fictional sample documents
```

---

## ⚡ How to Run Tests

Before running tests, ensure you have active developer dependencies installed:
```bash
pip install -r requirements.txt
pip install pytest pytest-cov
```

### 1. Run Standard Tests (Fast)
To run the unit and integration tests *excluding* heavy AI models downloads:
```bash
pytest -v -k "not test_ai"
```
*Expected output: `179 passed, 5 deselected`.*

### 2. Run All Tests (Including GLiNER)
To run all tests, including zero-shot neural entity recognizers (downloads GLiNER model ~500 MB):
```bash
pytest -v
```
*Expected output: `184 passed`.*

### 3. Run Coverage Analysis
To check coverage percentage (the library maintains a strict **~95% coverage**):
```bash
pytest --cov=src/carnaval --cov-report=term-missing
```

---

## 📝 How to Write a New Test

We provide a pre-configured template [tests/test_template.py](test_template.py) containing boilerplate code for:
- Writing unit tests for new custom recognizers.
- Testing a custom pipeline stage.
- Executing an end-to-end integration test with mock file outputs.

### Steps to add a test:
1. Copy the relevant code class block from [test_template.py](test_template.py).
2. Save it under `tests/unit/test_your_feature.py` or `tests/integration/test_your_feature.py`.
3. Add your custom test assertions.
4. Execute `pytest tests/unit/test_your_feature.py` to verify it passes.

---

## 🧪 The Validation Corpus

`carnaval` is validated against a dedicated test corpus of several hundreds of fake documents representing the worst real-world B2B data quality and privacy cases encountered in production. The suite covers:
1. **Case & Accent Variations**: Handling of accents and casing (e.g. `Stephanie` / `Stéphanie` / `STEPHANIE`).
2. **Valid & Invalid Identifiers**: Validation algorithms, including mod-97 verification for IBAN and BIC formats.
3. **Country-Specific Identifiers**: French regulatory IDs like `NIR` (social security number), `VAT` (TVA), and company registration numbers (`SIREN` and `SIRET`).
4. **Entity Overlaps**: Resolving overlapping boundaries in Stage 4 (e.g. email containing subdomains).
5. **Punctuation & Layout Layouts**: Handling names attached to punctuation (e.g. `"LASTNAME Firstname"`, `"Mr. LASTNAME"`).
6. **Dirty PDF Extractions**: Sanitizing noisy PDF texts with parasite characters like pipes (e.g. `"Chi | mieBERTAUX"`).
7. **Multi-Occurrence Consistency**: Guaranteeing that the same real entity in multiple places maps to the exact same placeholder index.
8. **Tricky False Positives**: Filtering out common business terms mistaken as BICs (e.g. `"PARC"`).
9. **Multilingual Documents**: Processing long-form documents containing content mixed across multiple active languages.
