# 04 - Configuration

## Configuration layers

carnaval applies 3 successive layers on load:

```
+-----------------------+
| 1. config/            |  (technical defaults - universal regex)
+-----------------------+
            |
            v
+-----------------------+
| 2. profiles/<type>/   |  (document type - acknowledge, invoice, email...)
+-----------------------+
            |
            v
+-----------------------+
| 3. profiles_private/  |  (real client data - GIT IGNORE)
+-----------------------+
            |
            v
       Resolved Config
```

Merge strategy:
- `dict + dict`: recursion (key by key)
- `list + list`: concatenation (deny lists are enriched)
- `scalar + scalar`: the upper layer wins

## Profile layout

```
profiles/<name>/
|-- profile.yaml           # description (name, language, expected entities)
|-- deny_lists/            # lists to MASK
|   |-- organizations.yaml
|   |-- organization_singleton.yaml
|   `-- people.yaml
|-- allow_lists/           # lists to PRESERVE (anti false positives)
|   `-- product_refs.yaml
|-- patterns/              # type-specific regex (rare)
|-- policies/              # arbitration rules (rare)
`-- fixtures/              # fictional examples for tests
    `-- sample.txt
```

## `config/pipeline.yaml` file

```yaml
pipeline:
  default_language: fr
  use_gliner: true
  gliner_threshold: 0.4
  cleanup_pipes: false
  score_threshold: 0.4

placeholder:
  format: "[{prefix}_{index}]"
  singleton_format: "[{prefix}]"

ai:
  gliner_model: "urchade/gliner_multi_pii-v1"
  gliner_labels:
    - person
    - email
    - phone number
    - address
    - organization
```

## Deny lists

Simple format - a key at the YAML root:

```yaml
# config/deny_lists/organizations.yaml or profiles/<type>/deny_lists/organizations.yaml
organizations:
  - "Globex Inc."
  - "Initech"
  - "Vandelay"
```

For email/web domains:

```yaml
supplier_domains:
  - "globex.example"
  - "initech.example"
```

## Singleton organization

The client's single parent company (appearing in all its documents) receives
**a single placeholder** without index:

```yaml
# profiles/<type>/deny_lists/organization_singleton.yaml
organization_singleton:
  - "Acme Corp"
  - "Acme Corporation"
  - "ACME CORP"
  - "ACMECORP"
```

All variants above will produce `[ORG]` (unique).

## People

```yaml
# profiles/<type>/deny_lists/people.yaml
people:
  - "Alice Anderson"
  - "Bob Brown"
```

## Allow lists (informative)

Allow lists are **documentary**. The pipeline does not use them
explicitly - their respect is guaranteed by:
- Specific regex that only match the correct forms
- The GLiNER score threshold
- Dedup that prioritizes deterministic recognizers

```yaml
# profiles/<type>/allow_lists/product_refs.yaml
product_ref_patterns:
  - "[A-Z]{2,4}-[A-Z0-9]{2,8}-\\d{2,4}"
```

## Run with a profile

```bash
python anonymize.py doc.txt --profile acknowledge
python anonymize.py doc.txt --profile invoice --no-gliner
python anonymize.py doc.txt --profile acknowledge --private my_client
```

## Inspect the resolved config

```python
from carnaval.core.config_loader import load_config

cfg = load_config(profile="acknowledge", private_profile="my_client")
print(cfg.layers)            # ['base:...', 'profile:acknowledge', 'private:my_client']
print(cfg.deny_lists)         # resolved dict
print(cfg.get("pipeline.use_gliner"))   # dotted-path access
```
