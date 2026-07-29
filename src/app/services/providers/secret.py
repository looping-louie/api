"""Encryption service for provider API keys."""

from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken


class SecretService(Protocol):
    """Encrypts, decrypts and masks provider secrets."""

    def encrypt_secret(self, plaintext: str) -> str:
        """Encrypt one plaintext value."""

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decrypt one encrypted value."""

    def trim_secret(self, plaintext: str) -> str:
        """Return a safe display representation."""


class SecretDecryptionError(RuntimeError):
    """Raised when encrypted provider data cannot be decrypted."""


class FernetSecretService:
    """Fernet-backed authenticated encryption service."""

    def __init__(self, encryption_key: str) -> None:
        """Validate and store the Looping Louie master key."""

        try:
            self._fernet = Fernet(encryption_key.encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "LOUIE_ENCRYPTION_KEY is not a valid Fernet key."
            ) from exc

    def encrypt_secret(self, plaintext: str) -> str:
        """Encrypt one plaintext value."""

        if not plaintext:
            raise ValueError("Cannot encrypt an empty secret.")

        return self._fernet.encrypt(
            plaintext.encode("utf-8")
        ).decode("utf-8")

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decrypt one encrypted value."""

        try:
            return self._fernet.decrypt(
                ciphertext.encode("utf-8")
            ).decode("utf-8")
        except InvalidToken as exc:
            raise SecretDecryptionError(
                "Stored provider credential cannot be decrypted."
            ) from exc

    def trim_secret(self, plaintext: str) -> str:
        """Keep the first five characters and mask the remainder."""

        return f"{plaintext[:5]}{'*' * 15}"
