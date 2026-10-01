import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionManager:
    """Symmetric encryption helper using authenticated AES-GCM.

    The key is passed in through the constructor (not read from the environment
    here); use EncryptionManagerFactory to build an instance from an EnvManager.

        manager = EncryptionManagerFactory.from_env(env)
        token = manager.encrypt_text("secret")
        plain = manager.decrypt_text(token)

    Encrypted output layout (then base64-encoded for text):
        [12-byte nonce][ciphertext + GCM auth tag]
    """

    #region CONSTANTS
    ALGORITHM_AES_GCM = "aes-gcm"
    SUPPORTED_ALGORITHMS = (ALGORITHM_AES_GCM,)
    NONCE_SIZE = 12  # 96 bits, the recommended nonce size for AES-GCM
    VALID_KEY_SIZES = (16, 24, 32)  # AES-128 / AES-192 / AES-256
    #endregion

    #region FIELDS
    __algorithm: str
    __key: bytes
    __aesgcm: AESGCM
    #endregion

    def __init__(self, key: bytes, algorithm: str = ALGORITHM_AES_GCM):
        """Create a manager from raw key bytes and an algorithm name."""
        algorithm = (algorithm or self.ALGORITHM_AES_GCM).lower()
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                f"Supported: {self.SUPPORTED_ALGORITHMS}"
            )
        if len(key) not in self.VALID_KEY_SIZES:
            raise ValueError(
                f"Key must be {self.VALID_KEY_SIZES} bytes (got {len(key)}). "
                "Use AES-128/192/256 sized keys."
            )

        self.__algorithm = algorithm
        self.__key = key
        self.__aesgcm = AESGCM(key)

    #region KEY HELPERS
    @staticmethod
    def generate_key(key_size: int = 32) -> bytes:
        """Generate a random key (default 32 bytes = AES-256)."""
        if key_size not in EncryptionManager.VALID_KEY_SIZES:
            raise ValueError(f"key_size must be one of {EncryptionManager.VALID_KEY_SIZES}.")
        return AESGCM.generate_key(bit_length=key_size * 8)

    @staticmethod
    def generate_key_b64(key_size: int = 32) -> str:
        """Generate a random key and return it base64-encoded (for .env)."""
        return base64.b64encode(EncryptionManager.generate_key(key_size)).decode("ascii")

    @staticmethod
    def key_from_b64(key_b64: str) -> bytes:
        """Decode a base64-encoded key string into raw bytes."""
        try:
            return base64.b64decode(key_b64, validate=True)
        except (ValueError, TypeError) as error:
            raise ValueError("ENCRYPTION_KEY is not valid base64.") from error
    #endregion

    #region PROPERTIES
    @property
    def algorithm(self) -> str:
        return self.__algorithm
    #endregion

    #region ENCRYPT / DECRYPT (bytes)
    def encrypt(self, plaintext: bytes, associated_data: bytes | None = None) -> bytes:
        """Encrypt raw bytes. Returns nonce + ciphertext (with auth tag)."""
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self.__aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext

    def decrypt(self, payload: bytes, associated_data: bytes | None = None) -> bytes:
        """Decrypt bytes produced by encrypt(). Raises if tampered or wrong key."""
        if len(payload) <= self.NONCE_SIZE:
            raise ValueError("Ciphertext is too short to contain a nonce.")
        nonce, ciphertext = payload[: self.NONCE_SIZE], payload[self.NONCE_SIZE :]
        return self.__aesgcm.decrypt(nonce, ciphertext, associated_data)
    #endregion

    #region ENCRYPT / DECRYPT (text)
    def encrypt_text(self, plaintext: str) -> str:
        """Encrypt a string and return a base64 token safe for storage/transport."""
        encrypted = self.encrypt(plaintext.encode("utf-8"))
        return base64.b64encode(encrypted).decode("ascii")

    def decrypt_text(self, token: str) -> str:
        """Decrypt a base64 token produced by encrypt_text() back into a string."""
        try:
            payload = base64.b64decode(token, validate=True)
        except (ValueError, TypeError) as error:
            raise ValueError("Token is not valid base64.") from error
        return self.decrypt(payload).decode("utf-8")
    #endregion

    #region ENCRYPT / DECRYPT (files)
    def encrypt_file(self, source_path, destination_path) -> None:
        """Encrypt a file's contents and write the result to destination_path."""
        from pathlib import Path

        data = Path(source_path).read_bytes()
        Path(destination_path).write_bytes(self.encrypt(data))

    def decrypt_file(self, source_path, destination_path) -> None:
        """Decrypt a file produced by encrypt_file() and write the plaintext."""
        from pathlib import Path

        data = Path(source_path).read_bytes()
        Path(destination_path).write_bytes(self.decrypt(data))
    #endregion


class EncryptionManagerFactory:
    """Logic layer: reads the key/algorithm from an EnvManager and builds an EncryptionManager."""

    @staticmethod
    def from_env(env) -> EncryptionManager:
        """Build an EncryptionManager from an EnvManager (or compatible object).

        Expects these .env keys:
            ENCRYPTION_KEY       base64-encoded 16/24/32-byte key
            ENCRYPTION_ALGORITHM optional, defaults to aes-gcm
        """
        key_b64 = env.require("ENCRYPTION_KEY")
        algorithm = env.get("ENCRYPTION_ALGORITHM", EncryptionManager.ALGORITHM_AES_GCM)
        key = EncryptionManager.key_from_b64(key_b64)
        return EncryptionManager(key, algorithm)
