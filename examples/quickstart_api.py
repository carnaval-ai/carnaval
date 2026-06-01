# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Quickstart example showing how to use Carnaval programmatically as a Python library."""

import json
from pathlib import Path
from carnaval.pipeline import run_anonymization_from_text
from carnaval.core.vault import Vault
from carnaval.stages.s7_reinject import reinject_json_data


def main():
    # 1. Sample text containing mock PII data
    sample_text = (
        "Dear Alice Anderson,\n\n"
        "We have received your order acknowledgment from Acme Corp.\n"
        "Please confirm the bank details for payment: IBAN FR76 3000 6000 0112 3456 7890 123.\n"
        "If you have questions, contact us at contact@acmecorp.com or +33 1 23 45 67 89.\n\n"
        "Best regards,\n"
        "Bob Smith"
    )

    print("--- 1. Original Text ---")
    print(sample_text)
    print("\n------------------------")

    # 2. Define output directory and password
    # In production, use a strong password (minimum 16 characters) from an environment variable.
    vault_password = "very-strong-secret-password-for-encryption-1234"
    outbox_dir = Path("outbox_quickstart")

    print("\nRunning anonymization pipeline...")
    
    # 3. Run the anonymization pipeline
    # We use the 'acknowledge' profile and disable GLiNER for a fast, rule-based initial run.
    masked, written, config = run_anonymization_from_text(
        text=sample_text,
        outbox_dir=outbox_dir,
        vault_password=vault_password,
        profile="acknowledge",
        use_gliner=False,  # Set to True to enable AI-based NER detection
    )

    print("\n--- 2. Anonymized Text ---")
    print(masked.anonymized_text)
    print("\n--------------------------")

    # 4. Show detected entities (spans)
    print("\n--- 3. Detected Spans ---")
    for span in masked.spans:
        print(f"[{span.entity_type}] '{span.text}' (index: {span.start}..{span.end})")
    print("------------------------")

    # 5. Simulate an LLM processing the anonymized text and returning structured JSON data
    # The LLM's response will contain the placeholder tags instead of the original sensitive data.
    mock_llm_response = {
        "client_name": "[CONTACT_2]",
        "company": "[CLIENT_NAME]",
        "contact_email": "[EMAIL_1]",
        "detected_phone": "[PHONE_1]",
        "summary": "Order received from [CLIENT_NAME] via [CONTACT_2]."
    }

    print("\n--- 4. Simulated LLM Response (with placeholders) ---")
    print(json.dumps(mock_llm_response, indent=2))
    print("-----------------------------------------------------")

    # 6. Re-inject the original values back into the LLM's structured output
    # We load the vault mappings from the encrypted file written during step 3.
    print("\nLoading encrypted vault to restore original values...")
    vault = Vault(password=vault_password, path=written.vault_path)
    vault.load()

    restored_response = reinject_json_data(mock_llm_response, vault)

    print("\n--- 5. Restored/Re-injected Response ---")
    print(json.dumps(restored_response, indent=2))
    print("-----------------------------------------")


if __name__ == "__main__":
    main()
