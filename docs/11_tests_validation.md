# 11 - Testing & Validation

This section describes the automated test suite for **carnaval**, how to execute it, and how developers can add new tests.

---

## Directory Structure

The repository includes a dedicated test harness under `tests/`:

- **`tests/conftest.py`**: Global path helper and configurations.
- **`tests/test_template.py`**: Boilerplate code containing copy-pasteable test templates for unit and integration testing.
- **`tests/unit/`**: Unit tests for core components and pipeline stages (stages 1 to 7, vault, spans, config loader).
- **`tests/recognizers/`**: Tests for neural (GLiNER) and regex-based entity recognizers.
- **`tests/integration/`**: End-to-end integration tests using business profiles (running the pipeline on fictional sample documents).

---

## How to Run Tests

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

*Expected output: `182 passed, 5 deselected`.*

### 2. Run All Tests (Including GLiNER)

To run all tests, including zero-shot neural entity recognizers (downloads GLiNER model ~500 MB):

```bash
pytest -v
```

*Expected output: `187 passed`.*

### 3. Run Coverage Analysis

To check coverage percentage (the library maintains a strict **~95% coverage**):

```bash
pytest --cov=src/carnaval --cov-report=term-missing
```

---

## Writing a New Test (Boilerplate)

We provide a pre-configured template [tests/test_template.py](file:///C:/Temp/Claude/Carnaval-publishable-EN/tests/test_template.py) containing boilerplate code.

To write a new test:
1. Copy the relevant code class block from the template.
2. Save it under `tests/unit/test_your_feature.py` or `tests/integration/test_your_feature.py`.
3. Add your custom test assertions.
4. Execute `pytest` to verify it passes.

---

## The Validation Corpus

`carnaval` is validated against a dedicated test corpus of several hundreds of fake documents representing the worst B2B data quality and privacy cases encountered in production. The suite covers:

- **Case & Accent Variations**: Handling of accents and casing (e.g. `Stephanie` / `Stéphanie` / `STEPHANIE`).
- **Valid & Invalid Identifiers**: Validation algorithms, including mod-97 verification for IBAN and BIC formats.
- **Country-Specific Identifiers**: French regulatory IDs like `NIR` (social security number), `VAT` (TVA), and company registration numbers (`SIREN` and `SIRET`).
- **Entity Overlaps**: Resolving overlapping boundaries in Stage 4 (e.g. email containing subdomains).
- **Punctuation & Layout Layouts**: Handling names attached to punctuation (e.g. `"LASTNAME Firstname"`, `"Mr. LASTNAME"`).
- **Dirty PDF Extractions**: Sanitizing noisy PDF texts with parasite characters like pipes (e.g. `"Chi | mieBERTAUX"`).
- **Multi-Occurrence Consistency**: Guaranteeing that the same real entity in multiple places maps to the exact same placeholder index.
- **Tricky False Positives**: Filtering out common business terms mistaken as BICs (e.g. `"PARC"`).
- **Multilingual Documents**: Processing long-form B2B documents containing content mixed across multiple active languages.
