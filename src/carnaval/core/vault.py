# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""AES-256-GCM encrypted vault for placeholder <-> original value mappings.

Binary file format:
    [16 bytes salt][16 bytes nonce][16 bytes tag][N bytes ciphertext]

Key is derived from the password using PBKDF2-HMAC-SHA256 (600,000 iterations).
"""

from __future__ import annotations

import json
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes


class VaultError(Exception):
    """Generic vault error (invalid password, corrupted file, etc.)."""


class Vault:
    """In-memory encrypted vault with optional on-disk persistence."""

    SALT_SIZE = 16
    NONCE_SIZE = 16
    TAG_SIZE = 16
    KEY_SIZE = 32  # AES-256
    PBKDF2_ITERATIONS = 600_000
    MIN_PASSWORD_LEN = 16

    def __init__(self, password: str, path: Path | str | None = None):
        if not password or len(password) < self.MIN_PASSWORD_LEN:
            raise VaultError(
                f"Password trop court (min {self.MIN_PASSWORD_LEN} caracteres)"
            )
        self._password = password.encode("utf-8")
        self.path: Path | None = Path(path) if path else None
        self.forward: dict[str, str] = {}  # original -> placeholder
        self.backward: dict[str, str] = {}  # placeholder -> original

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def store(self, placeholder: str, original: str) -> None:
        """Store a bidirectional mapping (original <-> placeholder)."""
        self.forward[original] = placeholder
        self.backward[placeholder] = original

    def get_original(self, placeholder: str) -> str | None:
        """Return the original value for a given placeholder, or None."""
        return self.backward.get(placeholder)

    def get_placeholder(self, original: str) -> str | None:
        """Return the existing placeholder for a given original value, or None."""
        return self.forward.get(original)

    def export_mapping(self) -> dict[str, dict[str, str]]:
        """Export mappings for debugging only. Do not log in production."""
        return {"forward": dict(self.forward), "backward": dict(self.backward)}

    def __len__(self) -> int:
        return len(self.forward)

    # ------------------------------------------------------------------
    # Persistance
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Write the encrypted vault to disk."""
        if not self.path:
            raise VaultError("Aucun chemin configure pour la persistance")
        payload = json.dumps(
            {"forward": self.forward, "backward": self.backward},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        salt = get_random_bytes(self.SALT_SIZE)
        key = self._derive_key(salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=get_random_bytes(self.NONCE_SIZE))
        ciphertext, tag = cipher.encrypt_and_digest(payload)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as f:
            f.write(salt + cipher.nonce + tag + ciphertext)

    def load(self) -> None:
        """Load the vault from disk. No-op if the file does not exist."""
        if not self.path or not self.path.exists():
            return
        with open(self.path, "rb") as f:
            blob = f.read()

        if len(blob) < self.SALT_SIZE + self.NONCE_SIZE + self.TAG_SIZE:
            raise VaultError("Fichier vault corrompu (trop court)")

        salt = blob[: self.SALT_SIZE]
        nonce = blob[self.SALT_SIZE : self.SALT_SIZE + self.NONCE_SIZE]
        tag = blob[
            self.SALT_SIZE
            + self.NONCE_SIZE : self.SALT_SIZE
            + self.NONCE_SIZE
            + self.TAG_SIZE
        ]
        ciphertext = blob[self.SALT_SIZE + self.NONCE_SIZE + self.TAG_SIZE :]

        key = self._derive_key(salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        try:
            payload = cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError as e:
            raise VaultError("Mauvais password ou vault corrompu") from e

        data = json.loads(payload.decode("utf-8"))
        self.forward = dict(data.get("forward", {}))
        self.backward = dict(data.get("backward", {}))

    # ------------------------------------------------------------------
    # Interne
    # ------------------------------------------------------------------

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive a 256-bit key from the password using PBKDF2-HMAC-SHA256."""
        return PBKDF2(
            self._password,  # type: ignore[arg-type]
            salt,
            dkLen=self.KEY_SIZE,
            count=self.PBKDF2_ITERATIONS,
            hmac_hash_module=SHA256,
        )
