# 02 - Installation

## Prerequisites

- **Python**: 3.11 or higher (tested on 3.13)
- **OS**: Windows, Linux, macOS
- **RAM**: 2 GB minimum (GLiNER loads a ~500 MB model)
- **Disk**: ~1 GB (for the venv + HuggingFace model caches)
- **Network**: required on first launch (GLiNER download).
  After that, everything works offline.

## Installation

### Method A: Standard Installation (from PyPI)

If you only want to use `carnaval` as a dependency in your project, install it directly from PyPI:

```bash
pip install carnaval
```

### Method B: Local Source & Development Installation

If you want to run tests, contribute, or build/test packaging distributions locally:

#### 1. Clone or retrieve the code

```bash
git clone <url>
cd carnaval
```

#### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS / Git Bash
source .venv/bin/activate
```

#### 3. Install in editable development mode

```bash
pip install --upgrade pip
pip install -e .
```

#### 4. Building and Testing the Distributable Wheels (Optional)

To verify the packaging build structure locally (ensuring all static data directories and compiled modules are correctly bundled):

```bash
# Install the build tool
pip install build

# Build the source distribution (tar.gz) and wheel (.whl)
python -m build

# Create a clean temporary environment to test the wheel
python -m venv test_env
.\test_env\Scripts\Activate.ps1   # Windows
# or: source test_env/bin/activate # Linux/macOS

# Install the locally built wheel
pip install dist/carnaval-*.whl

# Copy the quickstart example script into the test environment folder
# Windows:
copy examples\quickstart_api.py test_env\
# Linux/macOS:
cp examples/quickstart_api.py test_env/

# Change directory to the test environment
cd test_env

# Run the script to verify the installed wheel works perfectly
python quickstart_api.py
```

Installed dependencies:
- `pycryptodome`: AES-256-GCM encryption
- `PyYAML`, `python-dotenv`: config
- `structlog`: logs
- `lingua-language-detector`: language detection
- `gliner`: PII NER (via torch + transformers)
- `pytest`, `pytest-cov`: tests

### 4. Configure the vault password

```bash
cp .env.example .env
```

Edit `.env`:

```
CARNAVAL_VAULT_PASSWORD=your_strong_secret_of_at_least_32_characters
```

**Important**: never commit `.env`. The `.gitignore` already excludes it.

### 5. Verify the installation

```bash
pytest -m "not slow"
```

Expected result: `179 passed, 5 deselected` (for a total of 184 tests in the test suite; the 5 deselected tests are slow AI recognizer tests that require downloading neural network models like GLiNER ~500 MB).

### 6. Run a live test

```bash
python anonymize.py profiles/acknowledge/fixtures/sample_ack_globex.txt \
    --profile acknowledge --no-gliner
```

Verify that `outbox/txt/sample_ack_globex_anonymise.txt` is created.

## Activate GLiNER (first call)

The model is automatically downloaded from HuggingFace on the first
call. This takes **~2-5 minutes** depending on your connection (~500 MB).

```bash
python anonymize.py profiles/acknowledge/fixtures/sample_ack_globex.txt \
    --profile acknowledge
```

Subsequent calls use the local cache (~/.cache/huggingface).

## Offline installation (no network)

To deploy in an environment without internet:

1. On a connected machine:
   ```bash
   pip download -r requirements.txt -d wheels/
   python -c "from gliner import GLiNER; GLiNER.from_pretrained('urchade/gliner_multi_pii-v1')"
   ```
2. Copy `wheels/` and `~/.cache/huggingface/` to the target machine.
3. On the target machine:
   ```bash
   pip install --no-index --find-links=wheels/ -r requirements.txt
   ```

## Final verification

```bash
python -c "from carnaval.pipeline import run_anonymization; print('OK')"
```

If OK is displayed, the installation is complete.


## The Validation Corpus & Hard Cases

carnaval is validated against a dedicated test corpus of several hundreds of fake documents representing the worst real-world B2B data quality and privacy cases encountered in production. The suite covers the following challenging scenarios:

- **Case & Accent Variations**: Handling of accents and uppercase/lowercase variants (e.g., `Stephanie`, `Stéphanie`, `STEPHANIE`).
- **Valid & Invalid Identifiers**: Real-world validation checks, including mod-97 verification for IBAN and BIC formats.
- **Country-Specific Identifiers**: French regulatory IDs like `NIR` (social security number), `VAT` (TVA), and company registration numbers (`SIREN` and `SIRET`).
- **Entity Overlaps**: Resolving overlapping boundaries in Stage 4 (e.g., an email address containing a subdomain or a product reference overlapping with a business name).
- **Punctuation & Layout Layouts**: Parsing names directly attached to punctuation, and layouts such as `"LASTNAME Firstname"` or `"Mr. LASTNAME"`.
- **Dirty PDF Extractions**: Cleaning up noisy PDF texts with parasite characters like pipes (e.g., `"Chi | mieBERTAUX"`).
- **Multi-Occurrence Consistency**: Ensuring the same real entity across multiple places in a document maps to the exact same placeholder index.
- **Tricky False Positives**: Filtering out common business terms mistaken as BICs (e.g. `"PARC"`).
- **Multilingual Documents**: Supporting long-form documents containing content mixed across multiple active languages.
