# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""CLI carnaval : anonymise un fichier .txt vers les formats standards.

Usage :
    carnaval-anonymize inbox/doc.txt
    carnaval-anonymize doc.txt --profile acknowledge
    carnaval-anonymize doc.txt --profile acknowledge --private mon_profil
    carnaval-anonymize doc.txt --no-gliner

La variable d'environnement CARNAVAL_VAULT_PASSWORD doit etre definie.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from carnaval.core.logger import configure_logging
from carnaval.pipeline import run_anonymization

DEMO_PASSWORD = "demo_password_change_me_in_prod"


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="carnaval-anonymize",
        description=(
            "Anonymise un fichier texte. Produit simultanement les sorties "
            "TXT, JSON, JSONL, XML, CoNLL et HTML dans outbox/."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Chemin du fichier .txt a anonymiser",
    )
    parser.add_argument(
        "--outbox",
        type=Path,
        default=Path("outbox"),
        help="Dossier de sortie (defaut : ./outbox)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profil metier (acknowledge, invoice, email, ...)",
    )
    parser.add_argument(
        "--private",
        type=str,
        default=None,
        help="Profil prive sous profiles_private/",
    )
    parser.add_argument(
        "--no-gliner",
        action="store_true",
        help="Desactive GLiNER (plus rapide, mais detecte moins de PERSON/LOCATION libres)",
    )
    parser.add_argument(
        "--gliner-threshold",
        type=float,
        default=0.4,
        help="Seuil de confiance GLiNER (defaut : 0.4)",
    )
    parser.add_argument(
        "--cleanup-pipes",
        action="store_true",
        help="Retire les `|` parasites entre les mots (utile pour textes extracteur PDF defaillants)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=("fr", "en", "de", "ja"),
        help="Force la langue. Auto-detection si non specifie.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Niveau de log (defaut : INFO)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Logs en mode console lisible plutot que JSON",
    )
    args = parser.parse_args()

    configure_logging(level=args.log_level, json_format=not args.console)

    password = os.environ.get("CARNAVAL_VAULT_PASSWORD") or DEMO_PASSWORD
    if password == DEMO_PASSWORD:
        print(
            "[AVERTISSEMENT] CARNAVAL_VAULT_PASSWORD non defini : password de demo utilise.",
            file=sys.stderr,
        )

    if not args.input.exists():
        print(f"[ERREUR] Fichier introuvable : {args.input}", file=sys.stderr)
        return 2

    try:
        masked, written, cfg = run_anonymization(
            input_path=args.input,
            outbox_dir=args.outbox,
            vault_password=password,
            profile=args.profile,
            private_profile=args.private,
            use_gliner=not args.no_gliner,
            gliner_threshold=args.gliner_threshold,
            cleanup_pipes=args.cleanup_pipes,
            language=args.language,
        )
    except Exception as e:
        print(f"[ERREUR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    # Resume console pour l'humain
    print()
    print("=" * 60)
    print(f"  carnaval - {args.input.name}")
    print("=" * 60)
    print(f"  Langue          : {masked.language}")
    print(f"  Spans masques   : {len(masked.spans)}")
    print(f"  Par categorie   :")
    for cat, n in sorted(masked.by_category.items()):
        print(f"    {cat:18s} : {n}")
    print()
    print(f"  Fichiers produits :")
    print(f"    TXT             : {written.txt_path}")
    print(f"    JSON            : {written.json_path}")
    print(f"    JSONL           : {written.jsonl_path}")
    print(f"    XML             : {written.xml_path}")
    print(f"    CoNLL           : {written.conll_path}")
    print(f"    HTML            : {written.html_path}")
    print(f"    Vault chiffre   : {written.vault_path}")
    print(f"    Metadata        : {written.meta_path}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
