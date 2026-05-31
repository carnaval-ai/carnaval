# 01 - Architecture by stages

The carnaval pipeline is split into **7 autonomous stages**.

```
+---------+    +----------+    +--------+    +---------+    +------+    +--------+
| S1      |--->| S2       |--->| S3     |--->| S4      |--->| S5   |--->| S6     |
| Intake  |    | Preproc. |    | Detect |    | Resolve |    | Mask |    | Output |
+---------+    +----------+    +--------+    +---------+    +------+    +--------+

(inverse stage) S7 Reinject : JSON/XML with tags -> JSON/XML restored
```

## S1 - Intake: read the file

**Input**: `Path` to a `.txt` file
**Output**: `RawDocument` (raw text + metadata)

**Responsibilities**:
- Check existence and accessibility
- Read in UTF-8 (fallback to latin-1 on failure)
- Reject empty or too large files (`max_size_bytes`)
- Capture metadata: size, mtime, encoding

**Code**: `src/carnaval/stages/s1_intake.py`

**Tests**: `tests/unit/test_s1_intake.py`

---

## S2 - Preprocess: normalization + language

**Input**: `RawDocument`
**Output**: `NormalizedDocument` (normalized text + detected language)

**Responsibilities**:
- Detect language (lingua: FR/EN/DE/JA)
- Remove BOM
- Normalize multiple spaces (option `normalize_spaces`)
- Clean `|` parasites in the middle of words (option `cleanup_pipes`,
  disabled by default due to business risk)

**Code**: `src/carnaval/stages/s2_preprocess.py`

---

## S3 - Detect: execute recognizers

**Input**: `NormalizedDocument` + `Config`
**Output**: `DetectedDocument` (list of raw `Span`, not deduplicated)

**Responsibilities**:
- Load deny lists from config
- Execute each recognizer:
  - **Universal**: email, URL, IBAN, BIC, header_source
  - **FR** (if French language): phone, fiscal, address, name_patterns
  - **Deny lists**: organization_singleton, organizations, people
  - **AI**: GLiNER (zero-shot multilingual)
- Collect all Spans without arbitration (S4 will sort)

**Code**: `src/carnaval/stages/s3_detect.py`

---

## S4 - Resolve: deduplication of overlaps

**Input**: `DetectedDocument`
**Output**: `ResolvedDocument` (non-overlapping, ordered Spans)

**Responsibilities**:
- For each group of overlapping Spans, keep only one.
- Selection criteria (descending):
  1. **Length**: the longest span wins (encompassing)
  2. **Score**: higher wins
  3. **Recognizer priority**: `OrgSingleton` > `OrganizationsDenyList` > ... > `GLiNER`

**Why not "score first?"** Because an EMAIL (score 0.95) that contains a
subdomain (URL score 0.7) must prevail: the encompassing span wins even
if its score is slightly lower, otherwise the integrity of the
email is lost.

**Code**: `src/carnaval/stages/s4_resolve.py`

---

## S5 - Mask: placeholders + vault feeding

**Input**: `ResolvedDocument` + `Vault`
**Output**: `MaskedDocument` (anonymized text + Spans enriched with placeholder)

**Responsibilities**:
- For each Span, allocate a placeholder:
  - Singleton (`ORG_SINGLETON`) -> `[ORG]` (no index)
  - Other -> `[TYPE_n]` with n incremental per type
- Guarantee **consistency**: if a value already has a placeholder in the
  vault, reuse it (all occurrences -> same tag).
- Build the anonymized text (substitution **from right to left** to
  avoid breaking offsets).
- Record each mapping in the vault.

**Code**: `src/carnaval/stages/s5_mask.py`

---

## S6 - Output: multi-format writing

**Input**: `MaskedDocument` + `Vault` + outbox path
**Output**: `WrittenOutput` (paths of 8 files written)

**Responsibilities**: write to `outbox/`:
- `txt/<stem>_anonymise.txt`
- `json/<stem>_anonymise.json` (text + entities + meta)
- `jsonl/<stem>_entities.jsonl` (1 entity per line)
- `xml/<stem>_anonymise.xml`
- `conll/<stem>_anonymise.conll` (BIO)
- `html/<stem>_anonymise.html` (visualization)
- `vault/<stem>_vault.enc` (AES-256-GCM)
- `meta/<stem>_meta.json` (audit, **without sensitive data**)

**Code**: `src/carnaval/stages/s6_output.py`
**Serializers**: `src/carnaval/core/serializers.py`

---

## S7 - Reinject: restoration (inverse stage)

**Input**: JSON or XML with placeholders + Vault
**Output**: JSON or XML with original values restored

**Auto-detection** of format by the first character:
- `{` or `[` -> JSON
- `<` -> XML
- other -> fallback to raw text

**Code**: `src/carnaval/stages/s7_reinject.py`

---

## Orchestration: pipeline.py

The `src/carnaval/pipeline.py` module chains S1->S6:

```python
masked, written, config = run_anonymization(
    input_path=...,
    outbox_dir=...,
    vault_password=...,
    profile="acknowledge",
)
```

Each stage emits a structured log (without sensitive data, thanks to the
`_redact_sensitive` filter of the logger).
