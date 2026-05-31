#!/usr/bin/env python3
"""CLI carnaval : restaure les valeurs originales dans un JSON ou XML.

Usage :
    python reinject.py response_sonnet.json --vault outbox/vault/doc_vault.enc
    python reinject.py response_sonnet.xml --vault outbox/vault/doc_vault.enc
    python reinject.py response_sonnet.json --vault ... --output final.json

Auto-detection JSON vs XML par le contenu du fichier (premier caractere).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

from carnaval.core.vault import Vault, VaultError  # noqa: E402
from carnaval.stages.s7_reinject import reinject_string  # noqa: E402


DEMO_PASSWORD = "demo_password_change_me_in_prod"


def main() -> int:
    load_dotenv(_REPO_ROOT / ".env")

    parser = argparse.ArgumentParser(
        prog="carnaval-reinject",
        description=(
            "Restaure les valeurs originales dans un JSON ou XML produit par "
            "un LLM downstream. Auto-detection du format."
        ),
    )
    parser.add_argument(
        "input", type=Path,
        help="Fichier JSON ou XML contenant des placeholders [TYPE_n]",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Chemin du vault chiffre produit par anonymize.py",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Fichier de sortie (defaut : <input>_final.<ext>)",
    )
    args = parser.parse_args()

    password = os.environ.get("CARNAVAL_VAULT_PASSWORD") or DEMO_PASSWORD
    if password == DEMO_PASSWORD:
        print(
            "[AVERTISSEMENT] CARNAVAL_VAULT_PASSWORD non defini : demo utilise.",
            file=sys.stderr,
        )

    if not args.input.exists():
        print(f"[ERREUR] Fichier introuvable : {args.input}", file=sys.stderr)
        return 2
    if not args.vault.exists():
        print(f"[ERREUR] Vault introuvable : {args.vault}", file=sys.stderr)
        return 2

    # Charger le vault
    vault = Vault(password=password, path=args.vault)
    try:
        vault.load()
    except VaultError as e:
        print(f"[ERREUR] Vault : {e}", file=sys.stderr)
        return 1

    # Restaurer
    content = args.input.read_text(encoding="utf-8")
    restored = reinject_string(content, vault)

    # Sortie
    if args.output is None:
        stem = args.input.stem
        ext = args.input.suffix
        args.output = args.input.parent / f"{stem}_final{ext}"

    args.output.write_text(restored, encoding="utf-8")
    print(f"[OK] Fichier restitue : {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
