"""Generate a base64 encryption key to paste into .env.

Usage:
    python script\\create_key.py            # 32-byte key (AES-256)
    python script\\create_key.py 16         # 16-byte key (AES-128)
    python script\\create_key.py 24         # 24-byte key (AES-192)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from EncryptionManager import EncryptionManager


def main():
    key_size = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    try:
        key_b64 = EncryptionManager.generate_key_b64(key_size)
    except ValueError as error:
        print(f"Error: {error}")
        return 1

    print("Add this to your .env:\n")
    print(f"ENCRYPTION_ALGORITHM = {EncryptionManager.ALGORITHM_AES_GCM}")
    print(f"ENCRYPTION_KEY = {key_b64}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
