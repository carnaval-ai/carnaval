# 06 - Extend recognizers (code a new detector)

When deny lists are not enough (entity by pattern), you need to code
a recognizer.

## Contract

A carnaval recognizer is **a pure function**:

```python
def my_recognizer(text: str) -> list[Span]:
    ...
```

That's it. No inheritance, no framework, no hook to implement.

## Example: recognize a French social security number

```python
# src/carnaval/recognizers/regex/social_security_fr.py
"""Recognizer for French social security numbers (NIR)."""

import re
from carnaval.core.span import Span
from carnaval.recognizers.base import regex_to_spans


# NIR: 1 digit (gender) + 2 digits (year) + 2 digits (month) + 5 digits
# (birth commune) + 3 digits (order number) + 2 digits (key)
NIR_PATTERN = re.compile(
    r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2,5}\s?\d{3}\s?\d{2}\b"
)


def recognize_nir_fr(text: str, score: float = 0.85) -> list[Span]:
    return regex_to_spans(
        NIR_PATTERN, text,
        entity_type="NIR",
        recognizer="NirFrRegex",
        score=score,
    )
```

## Wire the new recognizer

Edit `src/carnaval/stages/s3_detect.py`, add the import and the function
in the appropriate tuple:

```python
from carnaval.recognizers.regex.social_security_fr import recognize_nir_fr

_FR_REGEX_RECOGNIZERS = (
    recognize_phone_fr,
    recognize_all_fiscal_fr,
    recognize_address_fr,
    recognize_name_patterns,
    recognize_nir_fr,      # <-- addition
)
```

## Add the placeholder

In `src/carnaval/stages/s5_mask.py`, add the mapping:

```python
DEFAULT_PLACEHOLDER_PREFIX = {
    ...,
    "NIR": "NIR",
}
```

Without this entry, the default prefix will be the entity_type itself, which
may also be suitable.

## Add priority in dedup

In `src/carnaval/stages/s4_resolve.py`:

```python
DEFAULT_RECOGNIZER_PRIORITY = {
    ...,
    "NirFrRegex": 85,
}
```

## Add to the reinjection pattern

In `src/carnaval/stages/s7_reinject.py`, the pattern is generic:

```python
PLACEHOLDER_PATTERN = re.compile(
    r"\[([A-Z]+(?:_\d+)?)\]"
)
```

It already matches `[NIR_1]`, `[NIR_2]`, etc. **No modification necessary**.

## Mandatory tests

Create `tests/recognizers/test_nir.py`:

```python
import pytest
from carnaval.recognizers.regex.social_security_fr import recognize_nir_fr

class TestNirRecognizer:
    @pytest.mark.parametrize("text,expected", [
        ("NIR 1 85 04 75 116 089 25", True),
        ("Numero 1850475116089 25", True),
        ("No NIR here", False),
        ("Reference 12345", False),
    ])
    def test_match(self, text, expected):
        assert (len(recognize_nir_fr(text)) > 0) == expected
```

And at least one integration test:

```python
# tests/integration/test_nir_pipeline.py
def test_nir_masked_end_to_end(tmp_path):
    ...
```

## Run all tests

```bash
pytest -m "not slow"
```

Target: everything remains green after adding the recognizer.

## AI recognizer (GLiNER zero-shot)

GLiNER already detects `person`, `email`, `address`, etc. To add a
new label:

```yaml
# config/pipeline.yaml
ai:
  gliner_labels:
    - person
    - email
    - ...
    - social security number    # <-- new label
```

And in `src/carnaval/recognizers/ai/gliner_engine.py`, add the
mapping:

```python
LABEL_TO_ENTITY_TYPE = {
    ...,
    "social security number": "NIR",
}
```

GLiNER will try to detect the pattern in zero-shot mode, without
retraining.

## Dictionary-based recognizer from external source

For a very long list (>1000 entries) that changes often (e.g. employee
list synchronized with an Active Directory), you can:

1. Store the list in an external file `data/employees.txt`
2. Load lazily:

```python
@functools.lru_cache(maxsize=1)
def _load_employees() -> list[str]:
    path = Path(__file__).parent.parent.parent / "data" / "employees.txt"
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def recognize_employees(text: str) -> list[Span]:
    return recognize_people(text, _load_employees())
```

## Best practices

- **One responsibility per recognizer**: one file = one entity type.
- **Positive AND negative tests**: 5 True cases + 5 False cases minimum.
- **No side effects**: the function receives `text`, returns `list[Span]`,
  nothing else.
- **Pattern compiled at module level**: avoids recompilation on each
  call.
- **Realistic score**: 0.95+ for very specific regex with checksum, 0.5-0.7
  for generic regex prone to false positives.
