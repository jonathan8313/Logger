"""
Signing abstraction and implementations.
HMAC (builtin) + RSA (cryptography when available).
"""

from __future__ import annotations
import base64
import os
from abc import ABC, abstractmethod
from typing import Optional

# Try to import cryptography for asymmetric support
try:
    from cryptography.hazmat.primitives import hashes, hmac as _crypto_hmac, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    CRYPTO_AVAILABLE = True
except Exception:
    CRYPTO_AVAILABLE = False

# --- Abstraction ---
class Signer(ABC):
    @abstractmethod
    def sign(self, data: bytes) -> str:
        """Return base64-encoded signature."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, data: bytes, signature_b64: str) -> bool:
        """Verify signature; return True if valid."""
        raise NotImplementedError

# --- HMAC Signer (works without cryptography) ---
import hmac as _hmac_builtin
import hashlib

class HMACSigner(Signer):
    def __init__(self, key: bytes, algorithm: str = "sha256"):
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("key must be bytes")
        self.key = key
        self.algorithm = algorithm.lower()
        # Use builtin for portability and no native deps

    def sign(self, data: bytes) -> str:
        digest_mod = getattr(hashlib, self.algorithm)
        sig = _hmac_builtin.new(self.key, data, digest_mod).digest()
        return base64.b64encode(sig).decode("ascii")

    def verify(self, data: bytes, signature_b64: str) -> bool:
        try:
            expected = self.sign(data)
            # constant-time compare
            return hmac_compare(expected.encode("ascii"), signature_b64.encode("ascii"))
        except Exception:
            return False

    @staticmethod
    def generate_key(nbytes: int = 32) -> bytes:
        return os.urandom(nbytes)

# --- RSA Signer (requires cryptography) ---
if CRYPTO_AVAILABLE:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    class RSASigner(Signer):
        def __init__(self, private_key_pem: bytes, password: Optional[bytes] = None):
            if not CRYPTO_AVAILABLE:
                raise RuntimeError("cryptography required for RSASigner")
            self._priv = load_pem_private_key(private_key_pem, password=password)
            self._pub = self._priv.public_key()

        def sign(self, data: bytes) -> str:
            sig = self._priv.sign(data, padding.PKCS1v15(), hashes.SHA256())
            return base64.b64encode(sig).decode("ascii")

        def verify(self, data: bytes, signature_b64: str) -> bool:
            try:
                sig = base64.b64decode(signature_b64.encode("ascii"))
                self._pub.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
                return True
            except Exception:
                return False

        @staticmethod
        def generate_rsa_keypair(key_size: int = 2048, password: Optional[bytes] = None) -> tuple[bytes, bytes]:
            priv = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
            enc = serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
            priv_pem = priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=enc
            )
            pub_pem = priv.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return priv_pem, pub_pem
else:
    # Provide a placeholder RSASigner raising clear error at use-time
    class RSASigner(Signer):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("cryptography library required for RSASigner")

        def sign(self, data: bytes) -> str:
            raise RuntimeError("cryptography library required for RSASigner")

        def verify(self, data: bytes, signature_b64: str) -> bool:
            raise RuntimeError("cryptography library required for RSASigner")

# --- Utilities ---
def hmac_compare(a: bytes, b: bytes) -> bool:
    """Constant-time comparison for signatures."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0
