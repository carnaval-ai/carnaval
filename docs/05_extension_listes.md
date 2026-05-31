# 05 - Extend lists (deny / allow) without coding

This is the most frequent extension: add a supplier, a name, an
orthographic variant.

## Add a supplier

Edit `profiles/<type>/deny_lists/organizations.yaml`:

```yaml
organizations:
  - "Globex Inc."
  - "Initech"
  - "My New Supplier SAS"     # <-- addition
  - "MyNewSupplier"           # orthographic variant
```

Run an anonymization -> the new name is detected immediately.
No restart, no recompilation, no index rebuild.

## Add a singleton variant

The client's unique parent company:

```yaml
# profiles/<type>/deny_lists/organization_singleton.yaml
organization_singleton:
  - "Acme Corp"
  - "Acme Corporation"
  - "ACME CORP."         # variant with period
  - "Acme  Corp"         # variant with double space
  - "ACMECORP"           # without space
```

All variants -> same placeholder `[ORG]`.

## Add a recurring person name

```yaml
# profiles/<type>/deny_lists/people.yaml
people:
  - "Alice Anderson"
  - "Bob Brown"
  - "John Doe"           # <-- addition
  - "Jane Doe"
```

NB: these are **full names**. For names detected by context
(Mr. LAST First, LAST, First), no need to list them: the regex
`name_patterns` catches them.

## Add an email domain

```yaml
supplier_domains:
  - "globex.example"
  - "mydomain.com"     # <-- addition
```

Will be detected by UrlRecognizer / EmailRecognizer.

## Client-specific (private profile)

To **not** expose your real data in the public repo:

1. Create `profiles_private/my_client_acknowledge/`
2. Reproduce the minimal structure there:

```
profiles_private/my_client_acknowledge/
|-- profile.yaml
`-- deny_lists/
    `-- organizations.yaml
```

```yaml
# profiles_private/my_client_acknowledge/profile.yaml
profile:
  name: my_client_acknowledge
  extends: acknowledge       # informative
  description: "Private profile client X"
```

```yaml
# profiles_private/my_client_acknowledge/deny_lists/organizations.yaml
organizations:
  - "My Real Supplier 1"
  - "My Real Supplier 2"
```

The merge **adds** the private suppliers to those of the public profile.

Launch:

```bash
python anonymize.py doc.txt \
    --profile acknowledge \
    --private my_client_acknowledge
```

## Verify coverage of a list

To test that a new variant is properly detected, run on a
sample text:

```bash
echo "Test: My New Supplier SAS delivers tomorrow" > /tmp/test.txt
python anonymize.py /tmp/test.txt --profile acknowledge --no-gliner --console
cat outbox/txt/test_anonymise.txt
# Should display: "Test: [ORG_1] delivers tomorrow"
```

## Common pitfalls

- **Case sensitive?** No, by default deny lists match ignoring
  case. `acme corp` also matches.
- **Variants with accents?** Python IGNORECASE does not support
  unicode folding by default. For `Stephanie`, also add
  `Stéphanie` to the list.
- **Substring risk?** The pattern uses word boundaries, so
  `Acme` will not match inside `acmeic`. The "loose" variant
  without word boundary is available if needed (see
  `organizations.py:recognize_organizations_loose`).

## Validation: profile tests

If you extend a lot, add a test:

```python
# tests/integration/test_my_profile.py
def test_my_new_supplier_masked(outbox_dir, tmp_path):
    text = "Order from My New Supplier SAS"
    inbox = tmp_path / "in.txt"
    inbox.write_text(text, encoding="utf-8")

    masked, _, _ = run_anonymization(
        input_path=inbox,
        outbox_dir=outbox_dir,
        vault_password="test_password_long_enough",
        profile="acknowledge",
        use_gliner=False,
    )
    assert "My New Supplier" not in masked.anonymized_text
```
