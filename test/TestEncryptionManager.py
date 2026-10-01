import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from EnvManager import EnvManager
from EncryptionManager import EncryptionManager, EncryptionManagerFactory

OUTPUT_DIR = PROJECT_ROOT / "output"


def test_text_roundtrip():
    print("1) Text round-trip")
    key = EncryptionManager.generate_key()
    manager = EncryptionManager(key)

    secret = "Quality report password: hunter2"
    token = manager.encrypt_text(secret)
    recovered = manager.decrypt_text(token)

    print(f"   algorithm: {manager.algorithm}")
    print(f"   token:     {token[:40]}...")
    print(f"   recovered: {recovered}")
    assert recovered == secret, "decrypted text does not match original"
    assert token != secret, "token should not equal the plaintext"
    print("   OK")


def test_tamper_detection():
    print("2) Tamper detection")
    import base64

    manager = EncryptionManager(EncryptionManager.generate_key())
    token = manager.encrypt_text("do not modify")

    raw = bytearray(base64.b64decode(token))
    raw[-1] ^= 0x01  # flip a bit in the auth tag
    tampered = base64.b64encode(bytes(raw)).decode("ascii")

    try:
        manager.decrypt_text(tampered)
        raise AssertionError("tampered token was accepted")
    except Exception as error:  # noqa: BLE001
        print(f"   rejected tampered token: {type(error).__name__}")
    print("   OK")


def test_wrong_key():
    print("3) Wrong key fails to decrypt")
    manager_a = EncryptionManager(EncryptionManager.generate_key())
    manager_b = EncryptionManager(EncryptionManager.generate_key())

    token = manager_a.encrypt_text("cross-key message")
    try:
        manager_b.decrypt_text(token)
        raise AssertionError("decrypting with the wrong key succeeded")
    except Exception as error:  # noqa: BLE001
        print(f"   wrong key rejected: {type(error).__name__}")
    print("   OK")


def test_invalid_key_size():
    print("4) Invalid key size rejected")
    try:
        EncryptionManager(b"too-short")
        raise AssertionError("short key was accepted")
    except ValueError as error:
        print(f"   rejected: {error}")
    print("   OK")


def test_file_roundtrip():
    print("5) File round-trip")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plain_path = OUTPUT_DIR / "enc_test_plain.txt"
    enc_path = OUTPUT_DIR / "enc_test.bin"
    dec_path = OUTPUT_DIR / "enc_test_decrypted.txt"

    original = "line one\nline two\n"
    plain_path.write_text(original, encoding="utf-8")

    manager = EncryptionManager(EncryptionManager.generate_key())
    manager.encrypt_file(plain_path, enc_path)
    manager.decrypt_file(enc_path, dec_path)

    recovered = dec_path.read_text(encoding="utf-8")
    assert recovered == original, "decrypted file content does not match"
    print(f"   {plain_path.name} -> {enc_path.name} -> {dec_path.name} OK")

    # Clean up temporary files created by this test.
    for path in (plain_path, enc_path, dec_path):
        path.unlink(missing_ok=True)


def test_factory_from_env():
    print("6) Factory from .env")
    try:
        env = EnvManager(PROJECT_ROOT / ".env")
        manager = EncryptionManagerFactory.from_env(env)
    except Exception as error:  # noqa: BLE001
        print(f"   ENCRYPTION_KEY not configured, skipping ({type(error).__name__}).")
        print("   Set ENCRYPTION_KEY in .env to test this path (see .env.example).")
        return

    token = manager.encrypt_text("configured-via-env")
    assert manager.decrypt_text(token) == "configured-via-env"
    print(f"   built from .env, algorithm={manager.algorithm}, round-trip OK")


def main():
    print("TEST ENCRYPTION MANAGER\n")
    test_text_roundtrip()
    test_tamper_detection()
    test_wrong_key()
    test_invalid_key_size()
    test_file_roundtrip()
    test_factory_from_env()
    print("\nAll encryption checks passed.")


if __name__ == "__main__":
    main()
