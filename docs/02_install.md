# 02 - Installation

## Prerequisites

- **Python**: 3.11 or higher (tested on 3.13)
- **OS**: Windows, Linux, macOS
- **RAM**: 2 GB minimum (GLiNER loads a ~500 MB model)
- **Disk**: ~1 GB (for the venv + HuggingFace model caches)
- **Network**: required on first launch (GLiNER download).
  After that, everything works offline.

## Installation

### 1. Clone or retrieve the code

```bash
git clone <url>
cd carnaval
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS / Git Bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
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

Expected result: `179 passed, 2 deselected` (the 2 slow tests
require downloading the GLiNER model ~500 MB).

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
