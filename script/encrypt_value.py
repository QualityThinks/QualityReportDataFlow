"""Encrypt a value using the key in .env and print the token to paste back.

Usage:
    python script\\encrypt_value.py "my secret value"
    python script\\encrypt_value.py           # prompts for the value

The printed token can be stored in .env; decrypt_value.py reverses it.
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
        value = " ".join(sys.argv[1:])
    else:
        value = input("Value to encrypt: ")

    try:
        env = EnvManager(PROJECT_ROOT / ".env")
        manager = EncryptionManagerFactory.from_env(env)
    except Exception as error:  # noqa: BLE001
        print(f"Could not load encryption key: {error}")
        print("Run script\\create_key.py first and add the key to .env.")
        return 1

    token = manager.encrypt_text(value)
    print("\nEncrypted token (safe to paste into .env):\n")
    print(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
