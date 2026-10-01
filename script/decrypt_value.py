"""Decrypt a token using the key in .env, to verify it decrypts correctly.

Usage:
    python script\\decrypt_value.py "<token>"
    python script\\decrypt_value.py          # prompts for the token

Requires ENCRYPTION_KEY (and optional ENCRYPTION_ALGORITHM) in .env.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from EnvManager import EnvManager
from EncryptionManager import EncryptionManagerFactory


def main():
    if len(sys.argv) > 1:
        token = " ".join(sys.argv[1:]).strip()
    else:
        token = input("Token to decrypt: ").strip()

    if not token:
        print("No token provided.")
        return 1

    try:
        env = EnvManager(PROJECT_ROOT / ".env")
        manager = EncryptionManagerFactory.from_env(env)
    except Exception as error:  # noqa: BLE001
        print(f"Could not load encryption key: {error}")
        print("Run script\\create_key.py first and add the key to .env.")
        return 1

    try:
        value = manager.decrypt_text(token)
    except Exception as error:  # noqa: BLE001
        print(f"Decryption failed: {type(error).__name__}: {error}")
        print("The token may be corrupted, or encrypted with a different key.")
        return 1

    print("\nDecrypted value:\n")
    print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
