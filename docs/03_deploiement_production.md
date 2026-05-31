# 03 - Production deployment

## Principles

carnaval is a **command-line tool**, not a service. To put it into production:
1. Install in a dedicated folder (cf. [02_install.md](02_install.md))
2. Store the vault password in an enterprise vault (HashiCorp Vault,
   AWS Secrets Manager, Azure Key Vault...)
3. Connect upstream/downstream of an existing pipeline (cron, NiFi, Airflow,
   PowerShell scheduler...)

## Typical deployment architecture

```
+-----------+
| PDF       |   (PDF -> TXT)
| Extractor |
+-----+-----+
      |
      v
   inbox/<doc>.txt
      |
      v
+-----------+
| anonymize.py (carnaval)
+-----+-----+
      |
      v
   outbox/txt/<doc>_anonymise.txt
      |
      v
+-----------+
| LLM call  | (Sonnet via Bedrock, etc.)
+-----+-----+
      |
      v
   response.json
      |
      v
+-----------+
| reinject.py (carnaval)
+-----+-----+
      |
      v
   final.json --> business consumer
```

## Environment variables

| Variable | Role | Critical |
|---|---|---|
| `CARNAVAL_VAULT_PASSWORD` | Vault password | YES |
| `CARNAVAL_LOG_LEVEL` | Log level (DEBUG/INFO/WARNING/ERROR) | No |

## Password management in production

**Bad**: `.env` file on the server in clear text.

**Good**:
- Linux: environment variable injected by systemd (`EnvironmentFile=/etc/secrets/carnaval`)
- Windows: system variable injected by the service or scheduled task
- Cloud: secret manager (Vault, AWS SM, Azure KV) retrieved on each run

PowerShell example:

```powershell
$env:CARNAVAL_VAULT_PASSWORD = (Get-VaultSecret -Path 'carnaval/vault-pwd').Value
python anonymize.py inbox\doc.txt --profile acknowledge
```

## Audit and logs

Structured JSON logs (`--log-level INFO`) emit per stage:

```json
{"event":"s5_mask_done","by_category":{"PERSON":2,"EMAIL":1},"timestamp":"..."}
```

**No clear text values** in the logs ( `_redact_sensitive` filter active).

For SIEM integration:
```bash
python anonymize.py inbox/doc.txt --profile acknowledge \
    --log-level INFO 2>> /var/log/carnaval/audit.jsonl
```

## Expected performance

| Configuration | Latency per document |
|---|---|
| GLiNER off (regex + denylist) | **<2 seconds** |
| GLiNER on, CPU x86 16 GB RAM | **15-20 seconds** |
| GLiNER on, GPU CUDA | **<5 seconds** (not tested) |

The first call includes downloading the HuggingFace model
(~80-120s with a decent connection).

## Vault lifecycle strategy

### Rotation

The vault password can be changed: all active vaults must then be re-encrypted. Procedure:

```python
import os
from pathlib import Path
from carnaval.core.vault import Vault

old_pwd = os.environ["OLD_PASSWORD"]
new_pwd = os.environ["NEW_PASSWORD"]

for vault_file in Path("outbox/vault").glob("*.enc"):
    v = Vault(password=old_pwd, path=vault_file)
    v.load()
    v_new = Vault(password=new_pwd, path=vault_file)
    v_new.forward = v.forward
    v_new.backward = v.backward
    v_new.save()
```

### Purge

Vaults can be purged after N days (after the downstream LLM
has finished processing and reinjection is done).

```bash
find outbox/vault -name "*.enc" -mtime +30 -delete
```

## Network security

carnaval opens **no network ports**. It reads a file, writes to
`outbox/`. No service, no bind. Easier to audit.

## Monitoring

Recommended metrics to report:
- Number of documents anonymized per hour
- Average latency per stage
- Failures (Spans=0, language=unknown, vault save failure)
- Size of the outbox/vault folder (alert if > X GB)
