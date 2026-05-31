# 07 - Security

## The encrypted vault

### Algorithm

| Element | Value |
|---|---|
| Symmetric encryption | AES-256-GCM |
| Key derivation | PBKDF2-HMAC-SHA256, 600,000 iterations |
| Salt | 16 random bytes per file |
| GCM nonce | 16 random bytes per file |
| Authentication tag | 16 bytes (integrity verification) |
| Binary format | `[salt 16][nonce 16][tag 16][ciphertext N]` |

### Strength

- AES-256-GCM mode: authenticated encryption. Any alteration of the file
  is detected on read (VaultError).
- PBKDF2 600k iterations: slows down dictionary/brute force attacks
  (non-trivial delay even with GPU).
- Random nonce per file: no reuse, no leakage by comparison
  of figures.

### Limitation

- The password must be strong. Minimum 16 characters, ideally >32, randomly
  generated.
- The password in RAM during execution. If the machine is compromised at
  the OS level, the clear text values are accessible. **This is not an HSM**.

## The password

### Generate a strong password

Linux/macOS:
```bash
openssl rand -base64 48
```

Windows PowerShell:
```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
```

### Storage

**DO NOT**:
- Commit to the repo (`.env` is git-ignored by default, keep it).
- Log even partially.
- Pass as command line argument (visible in `ps`, history).
- Hardcode in the code.

**DO**:
- Environment variable `CARNAVAL_VAULT_PASSWORD`, injected by:
  - Systemd: `EnvironmentFile=/etc/secrets/carnaval` (mode 600)
  - Windows: system variable of the service / scheduled task
  - Cloud: secret manager (Vault, AWS SM, Azure KV) read at startup

### Rotation

See [03_deploiement_production.md](03_deploiement_production.md#rotation).

## Anti-leak in logs

The structured logger (`carnaval/core/logger.py`) includes a processor
`_redact_sensitive` that prohibits any value under the following keys:

```python
SENSITIVE_KEYS = frozenset({
    "original", "raw_text", "raw", "text",
    "mapping", "vault", "vault_contents",
    "password", "secret",
    "forward", "backward",
})
```

If a caller attempts `log.info("event", original="Alice")`, the emitted log will be:
`{"event":"event","original":"<REDACTED>"}`.

This is a **default safeguard**. If you add keys in the code,
remember to enrich this frozenset.

## No network leakage

carnaval opens **no network ports** and makes **no outgoing calls**
after the initial GLiNER model download. You can:
- Test with `tcpdump` / wireshark
- Deploy in a container without network interface
- Block all outbound firewall for the user running carnaval

## Attack surface

### Compromised vault.enc file

Without the password, the content is unreadable (AES-256-GCM). With the password,
all original values are accessible.

**Mitigation**:
- Store `outbox/vault/` in an encrypted partition at rest
- Purge vaults after processing (cron: `find ... -mtime +30 -delete`)
- Password rotation (cf. deployment doc)

### Input file inbox/

The input file contains sensitive data **in clear text**. You must:
- Restrict POSIX rights (chmod 600)
- Delete it after anonymization
- Store on an encrypted partition

### Metadata meta.json

The file `outbox/meta/<stem>_meta.json` contains:
- Number of entities per category (statistical, non-sensitive)
- Source path (may be sensitive if the filename reflects the client)

No **original values** are in the meta.

## Audit

For SOC traces:

```bash
python anonymize.py inbox/doc.txt --profile acknowledge \
    --log-level INFO 2>> /var/log/carnaval/audit.jsonl
```

Format of each line:
```json
{"event":"s5_mask_done","by_category":{"PERSON":2,"EMAIL":1},"timestamp":"..."}
```

Traceability: we know how many entities of each type were masked,
but we never know WHICH ONES (zero leakage).

## RGPD compliance

carnaval allows implementing **pseudonymization** within the meaning of
RGPD (art. 4.5):
- Personal data replaced by identifiers that no longer allow
  identification without additional data
- Additional data (vault) is kept separately
  and technically protected

**Note**: carnaval is not an RGPD certificate. It is a technical
tool that helps with compliance. Overall compliance depends on the
usage context, retention periods, DPA contracts with external
LLMs, etc.
