import base64
import copy
import os
import stat
import tempfile
from pathlib import Path
import unittest

try:
    from cryptography.exceptions import InvalidTag
except ImportError:  # pragma: no cover - exercised only in a core-only install
    # The [pro] extra is optional and needs Python >=3.9 (cryptography's floor). A user who
    # installed the dependency-free core must still be able to run the suite; without this
    # guard, discovery errors on import and every OTHER test dies with it.
    raise unittest.SkipTest("cryptography not installed; continuity is the [pro] extra")

from emulo_autopilot.continuity_crypto import (
    decrypt_generation,
    generate_device_key_pair,
    generate_master_key,
    generate_recovery_secret,
    unwrap_master_key_for_device,
    unwrap_master_key_from_recovery,
    wrap_master_key_for_device,
    wrap_master_key_for_recovery,
    encrypt_generation,
    read_private_material,
    write_private_material,
)


GENERATION_ID = "gen_0123456789abcdef0123"
DEVICE_ID = "dev_0123456789abcdef0123456789abcdef"
CREATED_AT = "2026-07-17T12:00:00Z"


class ContinuityCryptoTests(unittest.TestCase):
    def test_generation_encryption_round_trips_unicode_and_crlf(self):
        key = generate_master_key()
        plaintext = "# Work\r\n\r\n- Hebrew: שלום\r\n- emoji: 🧠\r\n".encode("utf-8")
        envelope = encrypt_generation(
            key,
            generation_id=GENERATION_ID,
            parent_generation_id=None,
            author_device_id=DEVICE_ID,
            created_at=CREATED_AT,
            plaintext=plaintext,
        )

        self.assertEqual("emulo.continuity-envelope/v1", envelope["schema_version"])
        self.assertNotIn(plaintext.decode("utf-8"), str(envelope))
        self.assertEqual(plaintext, decrypt_generation(key, envelope))

    def test_fresh_nonce_makes_identical_plaintext_distinct(self):
        key = generate_master_key()
        arguments = dict(
            generation_id=GENERATION_ID,
            parent_generation_id=None,
            author_device_id=DEVICE_ID,
            created_at=CREATED_AT,
            plaintext=b"same approved artifact",
        )
        first = encrypt_generation(key, **arguments)
        second = encrypt_generation(key, **arguments)
        self.assertNotEqual(first["nonce"], second["nonce"])
        self.assertNotEqual(first["ciphertext"], second["ciphertext"])

    def test_tamper_wrong_key_and_metadata_changes_are_rejected(self):
        key = generate_master_key()
        envelope = encrypt_generation(
            key,
            generation_id=GENERATION_ID,
            parent_generation_id=None,
            author_device_id=DEVICE_ID,
            created_at=CREATED_AT,
            plaintext=b"approved artifact",
        )
        with self.assertRaises((InvalidTag, ValueError)):
            decrypt_generation(generate_master_key(), envelope)

        tampered = copy.deepcopy(envelope)
        raw = bytearray(base64.urlsafe_b64decode(tampered["ciphertext"] + "=="))
        raw[0] ^= 1
        tampered["ciphertext"] = base64.urlsafe_b64encode(bytes(raw)).decode().rstrip("=")
        with self.assertRaises(ValueError):
            decrypt_generation(key, tampered)

        metadata = copy.deepcopy(envelope)
        metadata["author_device_id"] = "dev_ffffffffffffffffffffffffffffffff"
        with self.assertRaises((InvalidTag, ValueError)):
            decrypt_generation(key, metadata)

    def test_plaintext_and_envelope_limits_fail_closed(self):
        key = generate_master_key()
        with self.assertRaisesRegex(ValueError, "plaintext is too large"):
            encrypt_generation(
                key,
                generation_id=GENERATION_ID,
                parent_generation_id=None,
                author_device_id=DEVICE_ID,
                created_at=CREATED_AT,
                plaintext=b"x" * (192 * 1024 + 1),
            )
        with self.assertRaisesRegex(ValueError, "generation_id"):
            encrypt_generation(
                key,
                generation_id="../escape",
                parent_generation_id=None,
                author_device_id=DEVICE_ID,
                created_at=CREATED_AT,
                plaintext=b"x",
            )

    def test_master_key_is_wrapped_for_only_the_intended_device(self):
        master_key = generate_master_key()
        private_a, public_a = generate_device_key_pair()
        private_b, _public_b = generate_device_key_pair()
        wrapped = wrap_master_key_for_device(master_key, public_a)

        self.assertNotIn(base64.urlsafe_b64encode(master_key).decode(), str(wrapped))
        self.assertEqual(master_key, unwrap_master_key_for_device(wrapped, private_a))
        with self.assertRaises((InvalidTag, ValueError)):
            unwrap_master_key_for_device(wrapped, private_b)

    def test_recovery_secret_is_random_confirmable_and_required(self):
        master_key = generate_master_key()
        secret = generate_recovery_secret()
        other_secret = generate_recovery_secret()
        self.assertNotEqual(secret, other_secret)
        self.assertRegex(secret, r"^[A-Za-z0-9_-]{43}$")
        wrapped = wrap_master_key_for_recovery(master_key, secret)

        self.assertNotIn(secret, str(wrapped))
        self.assertEqual(master_key, unwrap_master_key_from_recovery(wrapped, secret))
        with self.assertRaises((InvalidTag, ValueError)):
            unwrap_master_key_from_recovery(wrapped, other_secret)

    def test_keys_have_exact_modern_lengths(self):
        self.assertEqual(32, len(generate_master_key()))
        private_key, public_key = generate_device_key_pair()
        self.assertEqual(32, len(private_key))
        self.assertEqual(32, len(public_key))

    def test_private_material_round_trips_without_storing_recovery_secret(self):
        private_key, _public_key = generate_device_key_pair()
        master_key = generate_master_key()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "continuity-keys.json"
            write_private_material(path, private_key, master_key)
            self.assertEqual((private_key, master_key), read_private_material(path))
            payload = path.read_text(encoding="utf-8")
            self.assertNotIn("recovery_secret", payload)
            if os.name != "nt":
                self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))

    def test_private_material_refuses_a_symbolic_link(self):
        if os.name == "nt":
            self.skipTest("Windows symlink creation requires optional privileges")
        private_key, _public_key = generate_device_key_pair()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "target.json"
            target.write_text("untouched", encoding="utf-8")
            link = Path(folder) / "continuity-keys.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "private material path"):
                write_private_material(link, private_key, generate_master_key())
            self.assertEqual("untouched", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
