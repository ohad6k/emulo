import hashlib
import tempfile
from pathlib import Path
import unittest

from cryptography.exceptions import InvalidTag

from emulo_autopilot import contracts
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


if __name__ == "__main__":
    unittest.main()
