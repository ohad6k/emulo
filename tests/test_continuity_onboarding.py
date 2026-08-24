import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

try:
    from cryptography.exceptions import InvalidTag
except ImportError:  # pragma: no cover - exercised only in a core-only install
    # The [pro] extra is optional and needs Python >=3.9 (cryptography's floor). A user who
    # installed the dependency-free core must still be able to run the suite; without this
    # guard, discovery errors on import and every OTHER test dies with it.
    raise unittest.SkipTest("cryptography not installed; continuity is the [pro] extra")

from emulo_autopilot.continuity_crypto import read_private_material
from emulo_autopilot.continuity_onboarding import (
    connect_continuity,
    initialize_continuity,
    read_device_credential,
    recover_continuity,
)


class ContinuityOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_initialize_writes_private_keys_and_portable_kit_without_secret(self):
        home = self.root / "first"

        result = initialize_continuity(home)

        self.assertEqual("emulo.continuity-setup/v1", result["schema_version"])
        self.assertRegex(result["recovery_secret"], r"^[A-Za-z0-9_-]{43}$")
        private_path = Path(result["private_material_path"])
        kit_path = Path(result["recovery_kit_path"])
        self.assertTrue(private_path.is_file())
        self.assertTrue(kit_path.is_file())
        self.assertEqual(
            "emulo.continuity-recovery-kit/v1",
            json.loads(kit_path.read_text(encoding="utf-8"))["schema_version"],
        )
        serialized = "\n".join(
            (
                private_path.read_text(encoding="utf-8"),
                kit_path.read_text(encoding="utf-8"),
            )
        )
        self.assertNotIn(result["recovery_secret"], serialized)
        self.assertNotIn("recovery_secret", serialized)
        self.assertFalse((home / "autopilot" / "continuity" / "device.json").exists())
        if os.name != "nt":
            self.assertEqual(0o600, stat.S_IMODE(private_path.stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE(kit_path.stat().st_mode))

    def test_recover_restores_master_key_with_a_fresh_device_key(self):
        first_home = self.root / "first"
        second_home = self.root / "second"
        first = initialize_continuity(first_home)

        recovered = recover_continuity(
            second_home,
            first["recovery_kit_path"],
            first["recovery_secret"],
        )

        first_private, first_master = read_private_material(
            first["private_material_path"]
        )
        second_private, second_master = read_private_material(
            recovered["private_material_path"]
        )
        self.assertEqual(first_master, second_master)
        self.assertNotEqual(first_private, second_private)
        self.assertNotEqual(first["device_public_key"], recovered["device_public_key"])
        self.assertNotIn("recovery_secret", recovered)

    def test_wrong_recovery_secret_does_not_create_private_material(self):
        first = initialize_continuity(self.root / "first")
        second_home = self.root / "second"

        with self.assertRaises((InvalidTag, ValueError)):
            recover_continuity(
                second_home,
                first["recovery_kit_path"],
                "A" * 43,
            )

        self.assertFalse(
            (second_home / "autopilot" / "continuity" / "private-material.json").exists()
        )

    def test_initialize_and_recover_refuse_to_overwrite_existing_keys(self):
        first = initialize_continuity(self.root / "first")
        with self.assertRaisesRegex(ValueError, "already initialized"):
            initialize_continuity(self.root / "first")

        second_home = self.root / "second"
        recover_continuity(
            second_home,
            first["recovery_kit_path"],
            first["recovery_secret"],
        )
        before = (
            second_home / "autopilot" / "continuity" / "private-material.json"
        ).read_bytes()
        with self.assertRaisesRegex(ValueError, "already initialized"):
            recover_continuity(
                second_home,
                first["recovery_kit_path"],
                first["recovery_secret"],
            )
        self.assertEqual(
            before,
            (
                second_home
                / "autopilot"
                / "continuity"
                / "private-material.json"
            ).read_bytes(),
        )

    def test_recover_rejects_malformed_or_linked_recovery_kit(self):
        malformed = self.root / "malformed.json"
        malformed.write_text('{"schema_version":"wrong"}\n', encoding="utf-8")
        malformed.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "recovery kit is invalid"):
            recover_continuity(self.root / "malformed-home", malformed, "A" * 43)

        if os.name == "nt":
            return
        first = initialize_continuity(self.root / "first")
        linked = self.root / "linked.json"
        linked.symlink_to(Path(first["recovery_kit_path"]))
        with self.assertRaisesRegex(ValueError, "recovery kit path is invalid"):
            recover_continuity(
                self.root / "linked-home",
                linked,
                first["recovery_secret"],
            )

    def test_connect_wraps_the_key_and_stores_token_only_in_private_file(self):
        home = self.root / "first"
        setup = initialize_continuity(home)
        pairing_code = "P" * 43
        device_token = "T" * 43
        captured = {}

        def pairer(server, payload):
            captured["server"] = server
            captured["payload"] = payload
            return {
                "deviceId": "dev_0123456789abcdef0123456789abcdef",
                "deviceToken": device_token,
            }

        result = connect_continuity(
            home,
            "https://emulo.example",
            pairing_code,
            "Work laptop",
            "0.3.8",
            pairer=pairer,
        )

        self.assertEqual("emulo.continuity-connect/v1", result["schema_version"])
        self.assertEqual("https://emulo.example", captured["server"])
        self.assertEqual(pairing_code, captured["payload"]["pairingCode"])
        self.assertEqual(setup["device_public_key"], captured["payload"]["keyAgreementPublicKey"])
        self.assertEqual(
            setup["device_public_key"],
            captured["payload"]["wrappedMasterKey"]["device_public_key"],
        )
        self.assertNotIn("deviceToken", result)
        self.assertNotIn(device_token, json.dumps(result))
        credential = read_device_credential(home)
        self.assertEqual(device_token, credential["device_token"])
        credential_path = home / "autopilot" / "continuity" / "device.json"
        self.assertTrue(credential_path.is_file())
        if os.name != "nt":
            self.assertEqual(0o600, stat.S_IMODE(credential_path.stat().st_mode))

    def test_connect_refuses_to_replace_an_existing_device_credential(self):
        home = self.root / "first"
        initialize_continuity(home)

        def pairer(_server, _payload):
            return {
                "deviceId": "dev_0123456789abcdef0123456789abcdef",
                "deviceToken": "T" * 43,
            }

        connect_continuity(
            home,
            "https://emulo.example",
            "P" * 43,
            "Laptop",
            "0.3.8",
            pairer=pairer,
        )
        with self.assertRaisesRegex(ValueError, "already connected"):
            connect_continuity(
                home,
                "https://emulo.example",
                "Q" * 43,
                "Laptop",
                "0.3.8",
                pairer=pairer,
            )

    def test_connect_rejects_an_unsafe_server_before_calling_the_pairer(self):
        home = self.root / "first"
        initialize_continuity(home)
        called = []

        def pairer(_server, _payload):
            called.append(True)
            return {
                "deviceId": "dev_0123456789abcdef0123456789abcdef",
                "deviceToken": "T" * 43,
            }

        with self.assertRaisesRegex(ValueError, "HTTPS origin"):
            connect_continuity(
                home,
                "http://emulo.example",
                "P" * 43,
                "Laptop",
                "0.3.8",
                pairer=pairer,
            )
        self.assertEqual([], called)


if __name__ == "__main__":
    unittest.main()
