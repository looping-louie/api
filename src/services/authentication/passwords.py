"""Argon2id password hashing for local accounts."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from os import urandom

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


_HASH_LENGTH = 32
_SALT_LENGTH = 16
_ITERATIONS = 3
_LANES = 4
_MEMORY_COST = 64 * 1024


class PasswordHasher:
    """Create and verify encoded Argon2id local-account password hashes."""

    def hash(self, password: str) -> str:
        """Return a self-contained Argon2id hash for one password."""

        salt = urandom(_SALT_LENGTH)
        digest = self._derive(password=password, salt=salt)
        return '.'.join((
            'argon2id',
            urlsafe_b64encode(salt).decode('ascii'),
            urlsafe_b64encode(digest).decode('ascii'),
        ))

    def verify(self, *, password: str, encoded_hash: str) -> bool:
        """Return whether a password matches an encoded Argon2id hash."""

        try:
            algorithm, encoded_salt, encoded_digest = encoded_hash.split('.', 2)
            if algorithm != 'argon2id':
                return False
            salt = urlsafe_b64decode(encoded_salt)
            expected_digest = urlsafe_b64decode(encoded_digest)
            self._derive(password=password, salt=salt, expected_digest=expected_digest)
        except (InvalidKey, ValueError):
            return False
        return True

    @staticmethod
    def _derive(
        *,
        password: str,
        salt: bytes,
        expected_digest: bytes | None = None,
    ) -> bytes:
        """Derive or verify one password hash using instance-wide parameters."""

        kdf = Argon2id(
            salt=salt,
            length=_HASH_LENGTH,
            iterations=_ITERATIONS,
            lanes=_LANES,
            memory_cost=_MEMORY_COST,
        )
        password_bytes = password.encode('utf-8')
        if expected_digest is not None:
            kdf.verify(password_bytes, expected_digest)
            return expected_digest
        return kdf.derive(password_bytes)
