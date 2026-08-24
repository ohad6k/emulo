import json
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

from emulo_autopilot import contracts
from emulo_autopilot.continuity import (
    complete_pairing,
    package_generation,
    pull_remote_head,
    push_active,
    retry_pending,
    unpack_generation,
)
from emulo_autopilot.continuity_crypto import (
    generate_device_key_pair,
    generate_master_key,
    wrap_master_key_for_device,
)
from emulo_autopilot.store import AutopilotStore
from tests.autopilot_helpers import candidate_fixture, decision_fixture


DEVICE_A = "dev_0123456789abcdef0123456789abcdef"
DEVICE_B = "dev_ffffffffffffffffffffffffffffffff"
DEVICE_TOKEN = "A" * 43
PAIRING_CODE = "B" * 43


class JsonHeaders:
    def get_content_type(self):
        return "application/json"


class JsonResponse:
    def __init__(self, value, status=201):
        self.value = json.dumps(value).encode("utf-8")
        self.status = status
        self.headers = JsonHeaders()

    def read(self, _limit):
        return self.value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class CapturingOpener:
    def __init__(self, response):
        self.response = response
        self.request = None
        self.timeout = None

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return self.response


class MemoryTransport:
    def __init__(self):
        self.generations = {}
        self.head_id = None
        self.fail_upload = False
        self.upload_calls = 0

    def upload(self, envelope):
        self.upload_calls += 1
        if self.fail_upload:
            raise OSError("synthetic cloud outage")
        generation_id = envelope["generation_id"]
        existing = self.generations.get(generation_id)
        if existing is not None and existing != envelope:
            raise ValueError("generation-id-reused")
        self.generations[generation_id] = envelope
        if existing is not None:
            return {"status": "stored", "idempotent": True, "head": self.head_id}
        if envelope["parent_generation_id"] == self.head_id:
            self.head_id = generation_id
            return {"status": "stored", "idempotent": False, "head": self.head_id}
        return {
            "status": "conflict",
            "currentHead": self.head_id,
            "storedGeneration": generation_id,
        }

    def head(self):
        return {"generationId": self.head_id}

    def download(self, generation_id):
        return self.generations[generation_id]


def approved_generation(store, statement, created_at="2026-07-17T12:00:00Z"):
    candidate = candidate_fixture(statement=statement)
    store.put_candidate(candidate)
    store.append_decision(decision_fixture(candidate["candidate_id"]))
    return store.activate([candidate["candidate_id"]], created_at)


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = AutopilotStore(Path(self.temporary.name) / "device-a")
        self.key = generate_master_key()

    def test_package_contains_only_manifest_and_verified_domain_artifacts(self):
        generation = approved_generation(
            self.store,
            "Keep Unicode exact: שלום 🧠 and a private-looking C:/Users/ohad path.",
        )
        bundle = package_generation(self.store, generation["generation_id"])
        decoded = json.loads(bundle)

        self.assertEqual(
            {"schema_version", "generation", "artifacts"}, set(decoded)
        )
        self.assertEqual(generation, decoded["generation"])
        self.assertEqual({"work.md"}, set(decoded["artifacts"]))
        serialized = bundle.decode("utf-8")
        self.assertNotIn("receipts", serialized)
        self.assertNotIn("source_packet_hash", serialized)
        self.assertNotIn("evidence", serialized)
        manifest, artifacts = unpack_generation(bundle)
        self.assertEqual(generation, manifest)
        self.assertEqual(
            self.store.read_domain(generation["generation_id"], "work").encode(),
            artifacts["work.md"],
        )

    def test_push_encrypts_before_transport_and_retries_pending_idempotently(self):
        statement = "This raw approved statement must never reach the server."
        generation = approved_generation(self.store, statement)
        transport = MemoryTransport()
        transport.fail_upload = True

        with self.assertRaisesRegex(OSError, "outage"):
            push_active(self.store, self.key, DEVICE_A, transport)
        pending = self.store.list_continuity_pending()
        self.assertEqual([generation["generation_id"]], pending)
        pending_text = json.dumps(self.store.get_continuity_pending(pending[0]))
        self.assertNotIn(statement, pending_text)

        transport.fail_upload = False
        result = retry_pending(self.store, transport)
        self.assertEqual(1, result["uploaded"])
        self.assertEqual([], self.store.list_continuity_pending())
        self.assertNotIn(statement, json.dumps(transport.generations))
        self.assertEqual(generation["generation_id"], transport.head_id)

        replay = push_active(self.store, self.key, DEVICE_A, transport)
        self.assertTrue(replay["idempotent"])

    def test_second_device_imports_exact_unicode_bytes_and_preserves_local_rollback(self):
        first = approved_generation(
            self.store,
            "First rule with Hebrew שלום and emoji 🧠.",
            "2026-07-17T12:00:00Z",
        )
        second = approved_generation(
            self.store,
            "Second rule keeps CRLF text literal: A\\r\\nB.",
            "2026-07-17T12:01:00Z",
        )
        transport = MemoryTransport()
        push_active(self.store, self.key, DEVICE_A, transport, generation_id=first["generation_id"])
        push_active(self.store, self.key, DEVICE_A, transport, generation_id=second["generation_id"])

        other = AutopilotStore(Path(self.temporary.name) / "device-b")
        result = pull_remote_head(other, self.key, transport)
        self.assertEqual("activated", result["status"])
        self.assertEqual(second["generation_id"], other.get_head()["generation_id"])
        self.assertEqual(
            self.store.read_domain(second["generation_id"], "work").encode("utf-8"),
            other.read_domain(second["generation_id"], "work").encode("utf-8"),
        )

        rolled_back = other.rollback(first["generation_id"], "2026-07-17T12:02:00Z")
        self.assertEqual("rollback", rolled_back["operation"])
        self.assertIn("First rule", other.read_active_domain("work"))

    def test_divergent_local_head_is_preserved_for_explicit_resolution(self):
        shared = approved_generation(self.store, "Shared rule.")
        transport = MemoryTransport()
        push_active(self.store, self.key, DEVICE_A, transport)
        remote = approved_generation(
            self.store, "Remote branch.", "2026-07-17T12:01:00Z"
        )
        push_active(self.store, self.key, DEVICE_A, transport)

        other = AutopilotStore(Path(self.temporary.name) / "device-b")
        first_bundle = unpack_generation(package_generation(self.store, shared["generation_id"]))
        other.install_generation(*first_bundle)
        other.activate_imported_generation(shared["generation_id"], None)
        local = approved_generation(
            other, "Local branch.", "2026-07-17T12:01:30Z"
        )

        result = pull_remote_head(other, self.key, transport)
        self.assertEqual("conflict", result["status"])
        self.assertEqual(local["generation_id"], other.get_head()["generation_id"])
        self.assertEqual(remote, other.get_generation(remote["generation_id"]))

    def test_tampered_bundle_fails_before_store_mutation(self):
        generation = approved_generation(self.store, "Verified only.")
        transport = MemoryTransport()
        push_active(self.store, self.key, DEVICE_A, transport)
        envelope = dict(transport.generations[generation["generation_id"]])
        envelope["ciphertext"] = "A" + envelope["ciphertext"][1:]
        transport.generations[generation["generation_id"]] = envelope
        other = AutopilotStore(Path(self.temporary.name) / "device-b")

        with self.assertRaises((ValueError, InvalidTag)):
            pull_remote_head(other, self.key, transport)
        self.assertIsNone(other.get_head())
        self.assertEqual([], other.list_generations())

    def test_pairing_posts_bounded_json_without_credentials_in_url_or_headers(self):
        _private_key, public_key = generate_device_key_pair()
        wrapped = wrap_master_key_for_device(self.key, public_key)
        opener = CapturingOpener(
            JsonResponse({"deviceId": DEVICE_A, "deviceToken": DEVICE_TOKEN})
        )

        result = complete_pairing(
            "https://emulo.example",
            {
                "pairingCode": PAIRING_CODE,
                "label": "Work laptop",
                "keyAgreementPublicKey": wrapped["device_public_key"],
                "wrappedMasterKey": wrapped,
                "clientVersion": "0.3.8",
            },
            opener=opener,
        )

        self.assertEqual(
            {"deviceId": DEVICE_A, "deviceToken": DEVICE_TOKEN},
            result,
        )
        self.assertEqual(
            "https://emulo.example/v1/devices/pair/complete",
            opener.request.full_url,
        )
        self.assertEqual("POST", opener.request.method)
        self.assertNotIn("Authorization", opener.request.headers)
        self.assertNotIn(PAIRING_CODE, opener.request.full_url)
        self.assertLessEqual(len(opener.request.data), 8192)

    def test_pairing_rejects_unsafe_origins_and_malformed_responses(self):
        body = {
            "pairingCode": PAIRING_CODE,
            "label": "Laptop",
            "keyAgreementPublicKey": "C" * 43,
            "wrappedMasterKey": {},
            "clientVersion": "0.3.8",
        }
        for origin in (
            "http://emulo.example",
            "https://user:pass@emulo.example",
            "https://emulo.example/path",
            "https://emulo.example?query=1",
        ):
            with self.subTest(origin=origin):
                with self.assertRaisesRegex(ValueError, "HTTPS origin"):
                    complete_pairing(origin, body)

        malformed = CapturingOpener(JsonResponse({"deviceId": DEVICE_A}))
        with self.assertRaisesRegex(ValueError, "pairing response"):
            complete_pairing("https://emulo.example", body, opener=malformed)

        redirected = CapturingOpener(JsonResponse({}, status=302))
        with self.assertRaisesRegex(ValueError, "pairing response"):
            complete_pairing("https://emulo.example", body, opener=redirected)


if __name__ == "__main__":
    unittest.main()
