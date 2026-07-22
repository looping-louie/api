"""Fake provider secret service."""

from src.app.services.providers.secret_service import (
    SecretDecryptionError,
)


class FakeSecretService:
    """Provides deterministic reversible encryption for tests."""

    PREFIX = "encrypted::"

    def __init__(self) -> None:
        self.encrypted_values: list[str] = []
        self.decrypted_values: list[str] = []

    def encrypt_secret(self, plaintext: str) -> str:
        """Return deterministic ciphertext."""

        if not plaintext:
            raise ValueError("Cannot encrypt an empty secret.")

        self.encrypted_values.append(plaintext)
        return f"{self.PREFIX}{plaintext}"

    def decrypt_secret(self, ciphertext: str) -> str:
        """Recover plaintext from deterministic ciphertext."""

        self.decrypted_values.append(ciphertext)

        if not ciphertext.startswith(self.PREFIX):
            raise SecretDecryptionError(
                "Stored provider credential cannot be decrypted."
            )

        return ciphertext.removeprefix(self.PREFIX)

    @staticmethod
    def trim_secret(plaintext: str) -> str:
        """Return the production-compatible masked representation."""

        return f"{plaintext[:5]}{'*' * 15}"
