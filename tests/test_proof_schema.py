import json
import unittest
from pathlib import Path

from proof.schema import (
    CELL_RECORD_KEYS,
    MANIFEST_KEYS,
    PUBLICATION_KEYS,
    REVIEW_KEYS,
    require_sha256,
    validate_cell,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def minimal_manifest():
    return {
        "schema": "ditto-proof/1",
        "benchmark": "Ditto Proof v1",
        "benchmark_version": "1.0.0",
        "ditto_ref": "v0.3.7",
        "ditto_commit": "5f4008b0c0df40dcadb92c8fd1ba4dcf3aee40d0",
        "profile_manifest_sha256": "a" * 64,
        "private_rubric_sha256": "b" * 64,
        "public_rubric_sha256": "c" * 64,
        "uncertainty_policy": (
            "small-n, directional only; Wilson 95%; no significance claims"
        ),
        "host_persistent_context": "absent",
        "systems": [],
        "pairs": [],
        "limitations": ["synthetic test manifest"],
        "created_at": "2026-07-15T00:00:00Z",
    }


class ProofSchemaTest(unittest.TestCase):
    def test_manifest_rejects_unknown_version_before_cardinality(self):
        value = minimal_manifest()
        value["schema"] = "ditto-proof/2"

        with self.assertRaisesRegex(ValueError, "unsupported schema"):
            validate_manifest(value)

    def test_manifest_rejects_unknown_key(self):
        value = minimal_manifest()
        value["surprise"] = True

        with self.assertRaisesRegex(ValueError, "unexpected keys: surprise"):
            validate_manifest(value)

    def test_manifest_rejects_mixed_ditto_version(self):
        value = minimal_manifest()
        value["ditto_ref"] = "v0.3.8"

        with self.assertRaisesRegex(ValueError, "mixed Ditto version"):
            validate_manifest(value)

    def test_manifest_requires_two_systems_and_24_pairs(self):
        with self.assertRaisesRegex(ValueError, "exactly 2 systems"):
            validate_manifest(minimal_manifest())

    def test_manifest_rejects_structurally_empty_systems_pairs_and_bad_time(self):
        value = minimal_manifest()
        value["systems"] = [{}, {}]
        value["pairs"] = [{"cells": []} for _ in range(24)]
        value["created_at"] = "garbage"

        with self.assertRaisesRegex(ValueError, "system|created_at"):
            validate_manifest(value)

    def test_cell_requires_clean_host_state(self):
        with self.assertRaisesRegex(ValueError, "persistent context"):
            validate_cell(
                {
                    "schema": "ditto-proof-cell/1",
                    "host_persistent_context": "present",
                }
            )

    def test_sha256_rejects_uppercase_and_wrong_length(self):
        with self.assertRaisesRegex(ValueError, "lowercase hex"):
            require_sha256("A" * 64, "digest")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            require_sha256("a" * 63, "digest")

    def test_json_contracts_match_python_required_keys(self):
        expectations = {
            "benchmark-manifest-v1.json": MANIFEST_KEYS,
            "cell-record-v1.json": CELL_RECORD_KEYS,
            "review-record-v1.json": REVIEW_KEYS,
            "publication-v1.json": PUBLICATION_KEYS,
        }
        for filename, required in expectations.items():
            with self.subTest(filename=filename):
                schema = json.loads(
                    (ROOT / "proof" / "schemas" / filename).read_text("utf-8")
                )
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(sorted(required), sorted(schema["required"]))

        manifest_schema = json.loads(
            (ROOT / "proof/schemas/benchmark-manifest-v1.json").read_text("utf-8")
        )
        self.assertEqual(2, manifest_schema["properties"]["systems"]["minItems"])
        self.assertEqual(2, manifest_schema["properties"]["systems"]["maxItems"])
        self.assertEqual(24, manifest_schema["properties"]["pairs"]["minItems"])
        self.assertEqual(24, manifest_schema["properties"]["pairs"]["maxItems"])
        self.assertFalse(
            manifest_schema["properties"]["systems"]["items"][
                "additionalProperties"
            ]
        )
        self.assertFalse(
            manifest_schema["properties"]["pairs"]["items"][
                "additionalProperties"
            ]
        )


if __name__ == "__main__":
    unittest.main()
