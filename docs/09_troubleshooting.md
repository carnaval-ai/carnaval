# 09 - Troubleshooting

## VaultError: Wrong password or corrupted vault

**Cause**: the `CARNAVAL_VAULT_PASSWORD` used for `reinject.py` does
not match the one used for `anonymize.py`.

**Fix**:
- Check the environment variable
- If the password was changed between the two runs, the vault can no longer
  be decrypted. Either regenerate the vault (re-anonymize the text),
  or recover the old password.

## VaultError: Password too short

**Cause**: less than 16 characters.

**Fix**: use a password >= 16 chars, ideally >= 32.

```bash
openssl rand -base64 48
```

## IntakeError: File not found / empty / too large

- **Not found**: check the path (relative vs absolute)
- **Empty**: carnaval rejects 0-byte files. Check the upstream
  PDF extraction.
- **Too large**: default max size 50 MB. Increase via:
  ```python
  intake(path, max_size_bytes=100 * 1024 * 1024)
  ```

## GLiNER: download stuck

**Symptom**: on first call, hangs on "Fetching files...".

**Cause**: firewall/proxy blocks huggingface.co.

**Fix**:
- Check access to `huggingface.co` / `cdn-lfs.huggingface.co`
- Configure HTTPS proxy: `HTTPS_PROXY=...`
- Download on another machine and copy `~/.cache/huggingface/` to
  the target machine

Alternative: disable GLiNER (`--no-gliner`) - the pipeline falls back to
regex + denylist only.

## Slow performance

| Symptom | Probable cause | Fix |
|---|---|---|
| First call >60s | HF model download | Normal, wait |
| Each call >15s | GLiNER on CPU | Acceptable, or GPU if available |
| With `--no-gliner` still slow | Very long text | Check size (large document = many Spans) |

## Too many false positives

**Symptom**: non-sensitive words are masked (e.g. "PARC" becomes `[BIC_1]`).

**Possible causes**:
- GLiNER threshold too low: increase via `--gliner-threshold 0.6`
- Mis-calibrated custom recognizer

**Fix**:
- Inspect the JSON output: see which `recognizer` produces the false positive
- Adjust the regex in question, or increase the score threshold

## Not enough detection (leak)

**Symptom**: an obvious name is not masked.

**Causes**:
- GLiNER disabled (`--no-gliner`): missing contextual PERSON detection
- The name is not in the deny lists and is not matchable by regex
- The GLiNER threshold is too high

**Fix**:
- Enable GLiNER, lower the threshold to 0.3
- Add the name to `deny_lists/people.yaml`

## Parasitic text ( `|` characters in the middle of words)

**Symptom**: PDF extraction failure, text like `Chi | mieBERTAUX`.

**Fix**: enable `--cleanup-pipes`:

```bash
python anonymize.py inbox/doc.txt --profile acknowledge --cleanup-pipes
```

Warning: risk of modifying business content (rare but possible).

## latin-1 encoding in output

**Cause**: the source file was in latin-1 (the fallback was activated).

**Fix**: none. The content is preserved. If you want to force UTF-8
upstream, convert the file before: `iconv -f latin1 -t utf8 in.txt > out.txt`.

## ImportError: No module named 'carnaval'

**Cause**: execution without the venv activated, or outside the project folder.

**Fix**:
- Activate the venv: `.\.venv\Scripts\activate`
- Run from the project root: `python anonymize.py ...`

## IBAN checksum error

**Symptom**: a valid IBAN is not detected.

**Cause**: the validator requires mod 97 = 1. Verify on
[iban.com/iban-checker](https://www.iban.com/iban-checker) that the IBAN is
formally valid.

If the IBAN is valid but not detected, open an issue with an
anonymized example (without the real value, mask it yourself first!).

## Tests fail after a change

**Fix**: isolate by stage.

```bash
pytest tests/unit/test_s3_detect.py -v       # single file
pytest tests/unit/test_s3_detect.py::TestDetect::test_email_only -v   # single test
pytest --lf                                    # only the tests that failed
```

Read the error trace, the assertion message often gives the expected
value vs received.

## Logs invisible / empty

**Cause**: high log level.

**Fix**:
```bash
python anonymize.py inbox/doc.txt --profile acknowledge \
    --log-level DEBUG --console
```

`--console` makes logs readable (JSON mode by default for
machine-readability).

## Rarer symptoms

If nothing in this list matches your case:
1. Reproduce with a minimal text
2. Run with `--log-level DEBUG --console`
3. Capture the complete trace
4. Open an issue with:
   - Python version
   - OS
   - Input text (anonymized!)
   - Exact command
   - Complete output
   - Error trace
