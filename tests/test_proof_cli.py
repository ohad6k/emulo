import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from proof.cli import main
from proof.manifest import build_manifest, build_pairs, build_system_freeze
from proof.publish import publication_approval_digest
from proof.store import EvidenceStore


TASK_IDS = (
    "work-primary", "work-held-out", "design-primary", "design-held-out",
    "write-primary", "write-held-out",
)


def frozen_manifest():
    systems = []
    for index, host in enumerate(("codex", "claude"), start=1):
        systems.append(
            build_system_freeze(
                host, f"{host.title()} Stable", f"model-{index}", "1.0",
                ["provider", host], ["installer", host], f"{index:064x}",
                f"{index + 2:064x}", f"{index + 4:064x}", "quota", "cost"
            )
        )
    fixtures = {task_id: f"{i + 10:064x}" for i, task_id in enumerate(TASK_IDS)}
    instructions = {task_id: f"{i + 20:064x}" for i, task_id in enumerate(TASK_IDS)}
    pairs = build_pairs(
        systems, fixtures, instructions, "9" * 64,
        {family: {"time_seconds": 60, "max_turns": 2} for family in ("work", "design", "write")},
        "8" * 64,
    )
    return build_manifest(
        systems, pairs, "9" * 64, "7" * 64, "6" * 64,
        ["synthetic CLI test"], "2026-07-15T00:00:00Z"
    )


def publication_records(manifest, evidence_root):
    records = []
    store = EvidenceStore(
        evidence_root,
        {
            cell["cell_id"]: cell
            for pair in manifest["pairs"]
            for cell in pair["cells"]
        },
    )
    for index, pair in enumerate(manifest["pairs"]):
        ordered = sorted(pair["cells"], key=lambda item: item["order"])
        review = {
            "schema": "ditto-proof-review/1",
            "review_id": f"decision-{index}",
            "pair_id": pair["pair_id"],
            "family": pair["family"],
            "reviewer_role": "independent",
            "consent_reference": f"consent-{index}",
            "eligibility_attestation": "independent synthetic reviewer",
            "unfamiliar_with_operator_voice": True,
            "blinding_confirmed": True,
            "verdict": "tie",
            "left_review_id": ordered[0]["review_id"],
            "right_review_id": ordered[1]["review_id"],
            "invalidation_reason": "",
            "created_at": "2026-07-15T00:00:00Z",
        }
        for cell in pair["cells"]:
            artifacts = [f"{index + 201:064x}"]
            attempt_receipt = store.record_attempt(
                cell["cell_id"],
                {
                    "schema": "ditto-proof-attempt/1",
                    **{
                        field: cell[field]
                        for field in (
                            "cell_id", "pair_id", "system_id", "fixture_sha256",
                            "instruction_sha256", "profile_manifest_sha256",
                            "tool_policy_sha256", "permission_policy_sha256", "budget",
                        )
                    },
                    "meaningful_output": True,
                    "exit_status": "synthetic",
                },
            )
            evaluation_sha256 = store.record_evaluation(
                cell["cell_id"],
                {
                    "schema": "ditto-proof-evaluation/1",
                    "cell_id": cell["cell_id"],
                    "hard_failures": [],
                    "artifact_hashes": artifacts,
                    "redaction_state": "passed",
                },
            )
            review_sha256 = None
            if cell["order"] == 1:
                review_sha256 = store.record_review(cell["cell_id"], review)
            records.append(
                {
                    "cell_id": cell["cell_id"],
                    "pair_id": cell["pair_id"],
                    "condition": cell["condition"],
                    "family": cell["family"],
                    "publication_status": "eligible",
                    "hard_failures": [],
                    "objective_result_sha256": evaluation_sha256,
                    "artifact_hashes": artifacts,
                    "retry_history": [],
                    "review_status": "valid",
                    "preference": "tie" if cell["order"] == 1 else None,
                    "invalidation_reason": "",
                    "attempt_sha256": attempt_receipt["sha256"],
                    "evaluation_sha256": evaluation_sha256,
                    "review_sha256": review_sha256,
                    "redaction_state": "passed",
                }
            )
    return records


class ProofCliTest(unittest.TestCase):
    def write_manifest(self, root):
        path = root / "manifest.json"
        path.write_text(json.dumps(frozen_manifest()), encoding="utf-8")
        return path

    def test_validate_prints_json_and_manifest_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_manifest(Path(tmp))
            stdout = io.StringIO()
            stderr = io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["validate", "--manifest", str(path)])

            self.assertEqual(0, code)
            value = json.loads(stdout.getvalue())
            self.assertTrue(value["valid"])
            self.assertRegex(value["manifest_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual("", stderr.getvalue())

    @mock.patch("proof.cli.execute_cell")
    def test_execute_cell_without_execute_flag_fails_before_runner(self, execute):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write_manifest(root)
            target_cell = frozen_manifest()["pairs"][0]["cells"][0]["cell_id"]
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "execute-cell", "--manifest", str(path), "--cell-id", target_cell,
                        "--run-root", str(root / "run"), "--approval", "0" * 64,
                    ]
                )

            self.assertEqual(2, code)
            self.assertIn("--execute", stderr.getvalue())
            execute.assert_not_called()

    def test_package_requires_real_privacy_inputs_and_blocks_seeded_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = frozen_manifest()
            manifest["limitations"] = ["PROFILE-CANARY-do-not-publish"]
            evidence_root = root / "evidence"
            records = publication_records(manifest, evidence_root)
            manifest_path = root / "manifest.json"
            records_path = root / "records.json"
            privacy_path = root / "privacy.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            records_path.write_text(json.dumps(records), encoding="utf-8")
            privacy_path.write_text(
                json.dumps(
                    {
                        "canaries": {"profile": "PROFILE-CANARY-do-not-publish"},
                        "private_roots": [str(evidence_root)],
                    }
                ),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "package",
                        "--manifest",
                        str(manifest_path),
                        "--records",
                        str(records_path),
                        "--destination",
                        str(root / "public"),
                        "--ship-approval",
                        publication_approval_digest(manifest, records),
                        "--evidence-root",
                        str(evidence_root),
                        "--privacy-inputs",
                        str(privacy_path),
                        "--manual-review-approved",
                    ]
                )
            self.assertEqual(2, code)
            self.assertIn("privacy scan failed", stderr.getvalue())
            self.assertFalse((root / "public").exists())


if __name__ == "__main__":
    unittest.main()
