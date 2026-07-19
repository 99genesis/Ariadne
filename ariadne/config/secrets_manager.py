"""OS Credentials Vault / Secrets Manager layer for Ariadne.

Stores API keys and sensitive tokens securely using the operating system's native credential
store (Windows Credential Manager or Linux Secret Service via 'keyring').
If keyring is unavailable or headless, falls back to a locally encrypted Fernet vault file.
"""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Optional
import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ariadne.core.exceptions import SecurityException
from ariadne.core.interfaces import ISecretsManager


class OSSecretsManager(ISecretsManager):
    """Cross-platform secrets manager using OS keyring with encrypted fallback."""

    SERVICE_NAME = "ariadne-osint-framework"

    def __init__(self, fallback_dir: Optional[Path] = None) -> None:
        """Initialize secrets manager.

        Args:
            fallback_dir: Directory where encrypted fallback vault is saved if keyring is unavailable.
        """
        self.fallback_dir = Path(fallback_dir) if fallback_dir is not None else Path.home() / ".ariadne_secrets"
        self.fallback_file = self.fallback_dir / "vault.enc"
        self._keyring_available = self._check_keyring_availability()

    def _check_keyring_availability(self) -> bool:
        """Test if OS keyring is functioning properly."""
        try:
            # Check backend type without setting arbitrary values
            backend = keyring.get_keyring()
            if "fail" in str(backend).lower() or "null" in str(backend).lower():
                return False
            return True
        except Exception:
            return False

    def _get_fernet(self) -> Fernet:
        """Derive an encryption key tied to the current OS user and machine identifier."""
        try:
            self.fallback_dir.mkdir(parents=True, exist_ok=True)
            salt_file = self.fallback_dir / "salt.bin"
            if not salt_file.exists():
                salt = os.urandom(16)
                salt_file.write_bytes(salt)
            else:
                salt = salt_file.read_bytes()

            # Derive key from OS user string + fixed app string
            user_id = os.environ.get("USERNAME") or os.environ.get("USER") or "ariadne_local_user"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(user_id.encode("utf-8")))
            return Fernet(key)
        except Exception as exc:
            raise SecurityException(message="Failed to initialize encrypted secrets fallback.", details={"error": str(exc)})

    def _load_fallback_dict(self) -> Dict[str, str]:
        if not self.fallback_file.exists():
            return {}
        try:
            fernet = self._get_fernet()
            encrypted_data = self.fallback_file.read_bytes()
            decrypted_data = fernet.decrypt(encrypted_data)
            data: Dict[str, str] = json.loads(decrypted_data.decode("utf-8"))
            return data
        except Exception as exc:
            raise SecurityException(
                message="Failed to decrypt local secrets vault file.", details={"error": str(exc)}
            )

    def _save_fallback_dict(self, data: Dict[str, str]) -> None:
        try:
            fernet = self._get_fernet()
            payload = json.dumps(data).encode("utf-8")
            encrypted_data = fernet.encrypt(payload)
            self.fallback_file.write_bytes(encrypted_data)
        except Exception as exc:
            raise SecurityException(
                message="Failed to write to encrypted secrets vault file.", details={"error": str(exc)}
            )

    async def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret by key name."""
        if self._keyring_available:
            try:
                secret = keyring.get_password(self.SERVICE_NAME, key)
                if secret is not None:
                    return str(secret)
            except Exception:
                # Fall through to local fallback on keyring errors
                pass

        fallback_data = self._load_fallback_dict()
        return fallback_data.get(key)

    async def set_secret(self, key: str, value: str) -> None:
        """Store secret securely."""
        if self._keyring_available:
            try:
                keyring.set_password(self.SERVICE_NAME, key, value)
                return
            except Exception:
                pass

        fallback_data = self._load_fallback_dict()
        fallback_data[key] = value
        self._save_fallback_dict(fallback_data)

    async def delete_secret(self, key: str) -> bool:
        """Delete secret by key name."""
        deleted = False
        if self._keyring_available:
            try:
                keyring.delete_password(self.SERVICE_NAME, key)
                deleted = True
            except Exception:
                pass

        fallback_data = self._load_fallback_dict()
        if key in fallback_data:
            del fallback_data[key]
            self._save_fallback_dict(fallback_data)
            deleted = True

        return deleted
