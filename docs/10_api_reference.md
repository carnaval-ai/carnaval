# 10 - Python API

## Programmatic usage

carnaval can also be used as a Python library.

### Simple anonymization

```python
from pathlib import Path
from carnaval.pipeline import run_anonymization

masked, written, config = run_anonymization(
    input_path=Path("inbox/doc.txt"),
    outbox_dir=Path("outbox"),
    vault_password="my_long_secret_of_at_least_32_chars",
    profile="acknowledge",
    private_profile=None,
    use_gliner=True,
    gliner_threshold=0.4,
    cleanup_pipes=False,
    language=None,             # auto-detection if None
)

print(f"Anonymized: {masked.anonymized_text}")
print(f"Spans: {len(masked.spans)}")
print(f"Files written: {written.txt_path}, ...")
```

### Anonymization without disk writes

```python
from carnaval.core.vault import Vault
from carnaval.stages.s1_intake import intake
from carnaval.stages.s2_preprocess import preprocess
from carnaval.stages.s3_detect import detect
from carnaval.stages.s4_resolve import resolve
from carnaval.stages.s5_mask import mask
from carnaval.core.config_loader import load_config

cfg = load_config(profile="acknowledge")
raw = intake("inbox/doc.txt")
norm = preprocess(raw, cleanup_pipes=False)
det = detect(norm, cfg, use_gliner=True)
res = resolve(det)

vault = Vault(password="my_long_secret_of_at_least_32_chars")
masked = mask(res, vault)

# `masked.anonymized_text` contains the text with tags.
# `vault` contains the mappings in memory (not persisted).
```

### JSON reinjection

```python
import json
from carnaval.core.vault import Vault
from carnaval.stages.s7_reinject import reinject_json_data, reinject_json_string

vault = Vault(password="my_secret", path="outbox/vault/doc_vault.enc")
vault.load()

# From a dict
sonnet_response = {"supplier": "[ORG_1]", "contact": "[PERSON_1]"}
restored = reinject_json_data(sonnet_response, vault)
# {"supplier": "Globex Inc.", "contact": "Alice Anderson"}

# From a JSON string
json_str = '{"x": "[PERSON_1]"}'
restored_str = reinject_json_string(json_str, vault)
```

### XML reinjection

```python
from carnaval.stages.s7_reinject import reinject_xml_string

xml_str = '<order supplier="[ORG_1]">[PERSON_1]</order>'
restored = reinject_xml_string(xml_str, vault)
```

### Auto-detection

```python
from carnaval.stages.s7_reinject import reinject_string

# Accepts JSON, XML, or raw text. Auto-detects.
restored = reinject_string(content, vault)
```

## Key modules

### `carnaval.core.span.Span`

```python
@dataclass(frozen=True)
class Span:
    start: int
    end: int
    entity_type: str
    text: str
    score: float = 1.0
    recognizer: str = ""
    metadata: dict[str, Any] = ...

    @property
    def length(self) -> int: ...
    def overlaps(self, other: Span) -> bool: ...
    def contains(self, other: Span) -> bool: ...
    def shift(self, delta: int) -> Span: ...
    def to_dict(self) -> dict: ...
    def to_dict_safe(self) -> dict: ...   # without the original value
```

### `carnaval.core.vault.Vault`

```python
class Vault:
    def __init__(self, password: str, path: Path | None = None): ...
    def store(self, placeholder: str, original: str) -> None: ...
    def get_original(self, placeholder: str) -> str | None: ...
    def get_placeholder(self, original: str) -> str | None: ...
    def save(self) -> None: ...
    def load(self) -> None: ...
    def export_mapping(self) -> dict: ...
    def __len__(self) -> int: ...
```

Errors: `VaultError` (password too short, corrupted vault, file
missing...).

### `carnaval.core.config_loader.load_config`

```python
def load_config(
    base_dir: Path | str | None = None,
    profile: str | None = None,
    private_profile: str | None = None,
    repo_root: Path | str | None = None,
) -> Config: ...

@dataclass
class Config:
    raw: dict
    layers: list[str]

    @property
    def pipeline(self) -> dict: ...
    @property
    def deny_lists(self) -> dict: ...
    @property
    def allow_lists(self) -> dict: ...
    @property
    def policies(self) -> dict: ...
    @property
    def ai_models(self) -> dict: ...

    def get(self, dotted_key: str, default=None): ...
```

### `carnaval.core.logger`

```python
from carnaval.core.logger import configure_logging, get_logger

configure_logging(level="INFO", json_format=True)
log = get_logger("my_module")
log.info("event", duration=1.23)
```

The `_redact_sensitive` processor automatically filters sensitive keys
(`password`, `original`, `vault`, ...) -> `<REDACTED>`.

### `carnaval.recognizers.*`

Recognizers as pure functions:

```python
from carnaval.recognizers.regex.email import recognize_email
from carnaval.recognizers.regex.phone_fr import recognize_phone_fr
from carnaval.recognizers.regex.fiscal_fr import recognize_all_fiscal_fr
from carnaval.recognizers.regex.iban_bic import recognize_iban, recognize_bic
from carnaval.recognizers.denylist.organizations import recognize_organizations
from carnaval.recognizers.ai.gliner_engine import recognize_with_gliner

spans = recognize_email("Contact alice@example.com")
spans2 = recognize_organizations(text, organizations=["Globex", "Initech"])
```

## Document models

```python
from carnaval.stages.documents import (
    RawDocument,           # S1 output
    NormalizedDocument,    # S2 output
    DetectedDocument,      # S3 output
    ResolvedDocument,      # S4 output
    MaskedDocument,        # S5 output
    WrittenOutput,         # S6 output
)
```

All are `dataclass(frozen=True)`. Access fields in read-only mode.

## Serializers

```python
from carnaval.core.serializers import (
    to_txt, to_json, to_jsonl, to_xml, to_conll, to_html,
)

masked: MaskedDocument = ...
txt = to_txt(masked)
json_str = to_json(masked)
html = to_html(masked)
```

## Complete example: custom pipeline

```python
"""Custom pipeline: anonymization without disk writes + LLM call."""

from pathlib import Path
from carnaval.core.config_loader import load_config
from carnaval.core.vault import Vault
from carnaval.stages.s1_intake import intake
from carnaval.stages.s2_preprocess import preprocess
from carnaval.stages.s3_detect import detect
from carnaval.stages.s4_resolve import resolve
from carnaval.stages.s5_mask import mask
from carnaval.stages.s7_reinject import reinject_json_data


def process_document(path: Path, password: str) -> dict:
    # 1. Anonymize
    cfg = load_config(profile="acknowledge")
    raw = intake(path)
    norm = preprocess(raw)
    det = detect(norm, cfg, use_gliner=True)
    res = resolve(det)
    vault = Vault(password=password)
    masked = mask(res, vault)

    # 2. Call the LLM (e.g. Bedrock Claude)
    response = call_bedrock_claude(masked.anonymized_text)
    # response = {"supplier": "[ORG_1]", "contact": "[PERSON_1]", ...}

    # 3. Restore
    return reinject_json_data(response, vault)


def call_bedrock_claude(text: str) -> dict:
    # Placeholder
    import boto3, json
    client = boto3.client("bedrock-runtime", region_name="eu-west-3")
    r = client.invoke_model(
        modelId="anthropic.claude-sonnet-4-7",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Extract structured data:\n" + text}
            ]}],
        }),
    )
    return json.loads(r["body"].read())
```
