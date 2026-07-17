import contextlib
import hashlib
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from cryptography.exceptions import InvalidTag

from emulo_autopilot import cli, contracts, continuity_onboarding
from emulo_autopilot.continuity import pull_remote_head, push_active
from emulo_autopilot.continuity_crypto import (
    generate_device_key_pair,
    generate_master_key,
    generate_recovery_secret,
    unwrap_master_key_for_device,
    unwrap_master_key_from_recovery,
    wrap_master_key_for_device,
    wrap_master_key_for_recovery,
)
from emulo_autopilot.store import AutopilotStore
from tests.test_continuity import MemoryTransport


DEVICE_A = "dev_11111111111111111111111111111111"
DEVICE_B = "dev_22222222222222222222222222222222"


def materialized(store, payload, parent, created_at, candidate_hex):
    domains = {
        "work": {
            "artifact": "work.md",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    }
    generation = {
        "schema_version": contracts.GENERATION_SCHEMA,
        "generation_id": "",
        "parent_generation_id": parent,
        "operation": "activate",
        "candidate_ids": ["cand_" + candidate_hex * 20],
        "domains": domains,
        "created_at": created_at,
    }
    generation["generation_id"] = contracts.generation_identity(generation)
    store.install_generation(generation, {"work.md": payload})
    store.activate_imported_generation(generation["generation_id"], parent)
    return generation


class TwoDeviceContinuityProof(unittest.TestCase):
    def test_encrypted_generation_follows_to_device_b_and_local_rollback_survives(self):
        master_key = generate_master_key()
        private_a, public_a = generate_device_key_pair()
        private_b, public_b = generate_device_key_pair()
        wrapped_a = wrap_master_key_for_device(master_key, public_a)
        wrapped_b = wrap_master_key_for_device(master_key, public_b)
        self.assertEqual(master_key, unwrap_master_key_for_device(wrapped_a, private_a))
        device_b_key = unwrap_master_key_for_device(wrapped_b, private_b)

        recovery_secret = generate_recovery_secret()
        recovery = wrap_master_key_for_recovery(master_key, recovery_secret)
        self.assertEqual(
            master_key,
            unwrap_master_key_from_recovery(recovery, recovery_secret),
        )
        with self.assertRaises((InvalidTag, ValueError)):
            unwrap_master_key_from_recovery(recovery, generate_recovery_secret())

        with tempfile.TemporaryDirectory() as folder:
            device_a = AutopilotStore(Path(folder) / "device-a")
            device_b = AutopilotStore(Path(folder) / "device-b")
            first_bytes = "# Work\r\n\r\n- Hebrew: שלום\r\n- emoji: 🧠\r\n".encode("utf-8")
            first = materialized(
                device_a,
                first_bytes,
                None,
                "2026-07-17T12:00:00Z",
                "1",
            )
            second_bytes = first_bytes + "- proof: exact bytes survive\r\n".encode("utf-8")
            second = materialized(
                device_a,
                second_bytes,
                first["generation_id"],
                "2026-07-17T12:01:00Z",
                "2",
            )
            transport = MemoryTransport()
            push_active(
                device_a,
                master_key,
                DEVICE_A,
                transport,
                generation_id=first["generation_id"],
            )
            push_active(
                device_a,
                master_key,
                DEVICE_A,
                transport,
                generation_id=second["generation_id"],
            )

            result = pull_remote_head(device_b, device_b_key, transport)
            self.assertEqual("activated", result["status"])
            self.assertEqual(
                second_bytes,
                device_b.read_domain(second["generation_id"], "work").encode(
                    "utf-8"
                ),
            )

            transport.fail_upload = True
            rolled_back = device_b.rollback(
                first["generation_id"], "2026-07-17T12:02:00Z"
            )
            self.assertEqual("rollback", rolled_back["operation"])
            self.assertEqual(first_bytes, device_b.read_active_domain("work").encode())

        with self.assertRaises((InvalidTag, ValueError)):
            unwrap_master_key_for_device(wrapped_b, private_a)

    def test_customer_cli_recovers_and_moves_exact_generation_to_a_second_device(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            device_a_home = root / "device-a"
            device_b_home = root / "device-b"
            output = []

            def invoke(home, arguments, secret=""):
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = 0
                try:
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        cli.main(
                            ["--emulo-home", str(home), *arguments],
                            secret_reader=lambda _prompt: secret,
                        )
                except SystemExit as exc:
                    code = exc.code
                output.append(stdout.getvalue() + stderr.getvalue())
                return code, json.loads(stdout.getvalue()) if stdout.getvalue() else None

            code, setup = invoke(device_a_home, ["continuity-init"])
            self.assertEqual(0, code)
            recovery_secret = setup["recovery_secret"]
            transport = MemoryTransport()
            paired_payloads = []

            def pair(_server, payload):
                paired_payloads.append(payload)
                position = len(paired_payloads)
                return {
                    "deviceId": DEVICE_A if position == 1 else DEVICE_B,
                    "deviceToken": ("A" if position == 1 else "B") * 43,
                }

            with mock.patch.object(
                continuity_onboarding,
                "complete_pairing",
                side_effect=pair,
            ):
                code, connected_a = invoke(
                    device_a_home,
                    [
                        "continuity-connect",
                        "--label",
                        "Desktop",
                        "--server",
                        "https://emulo.example",
                    ],
                    "P" * 43,
                )
            self.assertEqual(0, code)
            self.assertEqual(DEVICE_A, connected_a["device_id"])

            store_a = AutopilotStore(device_a_home)
            first_bytes = "# Work\r\n\r\n- Hebrew: שלום\r\n- emoji: 🧠\r\n".encode("utf-8")
            first = materialized(
                store_a,
                first_bytes,
                None,
                "2026-07-17T12:00:00Z",
                "3",
            )
            with mock.patch.object(
                continuity_onboarding,
                "HttpsContinuityTransport",
                return_value=transport,
            ):
                code, pushed = invoke(device_a_home, ["continuity-push"])
            self.assertEqual(0, code)
            self.assertEqual(first["generation_id"], pushed["head"])

            second_bytes = first_bytes + "- proof: exact bytes survive\r\n".encode("utf-8")
            second = materialized(
                store_a,
                second_bytes,
                first["generation_id"],
                "2026-07-17T12:01:00Z",
                "4",
            )
            with mock.patch.object(
                continuity_onboarding,
                "HttpsContinuityTransport",
                return_value=transport,
            ):
                code, pushed = invoke(device_a_home, ["continuity-push"])
            self.assertEqual(0, code)
            self.assertEqual(second["generation_id"], pushed["head"])

            code, recovered = invoke(
                device_b_home,
                ["continuity-recover", setup["recovery_kit_path"]],
                recovery_secret,
            )
            self.assertEqual(0, code)
            self.assertEqual("emulo.continuity-recovery/v1", recovered["schema_version"])

            with mock.patch.object(
                continuity_onboarding,
                "complete_pairing",
                side_effect=pair,
            ):
                code, connected_b = invoke(
                    device_b_home,
                    [
                        "continuity-connect",
                        "--label",
                        "Laptop",
                        "--server",
                        "https://emulo.example",
                    ],
                    "Q" * 43,
                )
            self.assertEqual(0, code)
            self.assertEqual(DEVICE_B, connected_b["device_id"])

            with mock.patch.object(
                continuity_onboarding,
                "HttpsContinuityTransport",
                return_value=transport,
            ):
                code, pulled = invoke(device_b_home, ["continuity-pull"])
            self.assertEqual(0, code)
            self.assertEqual("activated", pulled["status"])
            store_b = AutopilotStore(device_b_home)
            self.assertEqual(
                second_bytes,
                store_b.read_domain(second["generation_id"], "work").encode("utf-8"),
            )
            joined_output = "".join(output)
            self.assertEqual(1, joined_output.count(recovery_secret))
            self.assertNotIn("A" * 43, joined_output)
            self.assertNotIn("B" * 43, joined_output)
            self.assertEqual(2, len(paired_payloads))


if __name__ == "__main__":
    unittest.main()
