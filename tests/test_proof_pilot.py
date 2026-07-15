import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from proof.canonical import canonical_bytes, sha256_bytes
from proof.evaluate import build_blind_pair, reveal_verdict, validate_review
from proof.fixtures import (
    load_fixture_lock,
    reset_fixture,
    seal_fixture,
    tree_hash,
    verify_fixture,
)
from proof.manifest import build_manifest, build_pairs, build_system_freeze
from proof.pilot import build_pilot_package, build_pilot_plan, load_pilot_registry
from proof.privacy import scan_public_tree
from proof.publish import build_publication, publication_approval_digest, render_index
from proof.runner import prepare_cell
from proof.store import EvidenceStore


ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = ROOT / "proof" / "fixtures" / "pilot"


def _init_fixture_repo(path, files):
    path.mkdir()
    for name, content in files.items():
        destination = path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "proof@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Proof Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "core.autocrlf", "false"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "synthetic fixture"],
        check=True,
    )
    return path


class PilotFixtureTest(unittest.TestCase):
    def test_committed_pilot_bytes_force_lf_across_checkouts(self):
        target = PILOT_ROOT / "design" / "contract.json"
        result = subprocess.run(
            ["git", "check-attr", "eol", "--", str(target)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("eol: lf", result.stdout)

    def test_pilot_has_three_non_scored_families(self):
        registry = load_pilot_registry(PILOT_ROOT / "registry.json")
        self.assertEqual(
            {"work", "design", "write"},
            {item["family"] for item in registry["tasks"]},
        )
        self.assertTrue(all(item["scored"] is False for item in registry["tasks"]))
        self.assertTrue(
            all(item["task_id"].startswith("pilot-") for item in registry["tasks"])
        )

    def test_fixture_contracts_are_machine_readable_and_fictional(self):
        registry = load_pilot_registry(PILOT_ROOT / "registry.json")
        for task in registry["tasks"]:
            fixture = PILOT_ROOT / task["path"]
            self.assertEqual(task["fixture_sha256"], tree_hash(fixture))
            contract = json.loads(
                (fixture / task["contract"]).read_text(encoding="utf-8")
            )
            self.assertEqual(task["family"], contract["family"])
            self.assertTrue(contract["required_outputs"])
            text = json.dumps(contract).casefold()
            self.assertNotIn("ohad", text)
            self.assertNotIn("ditto", text)

    def test_six_cells_are_isolated_opaque_and_non_scored(self):
        registry = load_pilot_registry(PILOT_ROOT / "registry.json")
        cells = build_pilot_plan(registry, seed="pilot-seed")
        self.assertEqual(6, len(cells))
        self.assertEqual(6, len({item["cell_id"] for item in cells}))
        self.assertEqual(6, len({item["review_id"] for item in cells}))
        self.assertEqual({"cold", "ditto"}, {item["condition"] for item in cells})
        self.assertTrue(all(item["scored"] is False for item in cells))
        self.assertTrue(
            all(
                "cold" not in item["review_id"]
                and "ditto" not in item["review_id"]
                for item in cells
            )
        )

    def test_resets_are_deterministic_and_cell_roots_differ(self):
        registry = load_pilot_registry(PILOT_ROOT / "registry.json")
        work = next(item for item in registry["tasks"] if item["family"] == "work")
        source = PILOT_ROOT / work["path"]
        with tempfile.TemporaryDirectory() as root:
            first = reset_fixture(source, Path(root) / "cold", work["fixture_sha256"])
            second = reset_fixture(source, Path(root) / "ditto", work["fixture_sha256"])
            self.assertNotEqual(first, second)
            self.assertEqual(tree_hash(first), tree_hash(second))

    def test_simulated_capture_is_sanitized_and_non_comparable(self):
        registry = load_pilot_registry(PILOT_ROOT / "registry.json")
        cells = build_pilot_plan(registry, seed="pilot-seed")
        records = []
        for index, cell in enumerate(cells):
            records.append(
                {
                    **cell,
                    "objective_checks": {"contract_captured": True},
                    "blind_review": {"captured": True, "verdict": "tie"},
                    "artifact_sha256": f"{index + 1:064x}",
                    "redaction_state": "passed",
                    "public_note": "synthetic pilot record",
                }
            )
        package = build_pilot_package(records, canaries={"private": "CANARY-PRIVATE"})
        self.assertEqual("pilot", package["label"])
        self.assertFalse(package["scored"])
        self.assertFalse(package["comparable"])
        self.assertEqual(6, package["execution_count"])
        self.assertTrue(
            all(item["objective_checks"] for item in package["records"])
        )
        self.assertTrue(all(item["blind_review"] for item in package["records"]))

        records[0]["public_note"] = "CANARY-PRIVATE"
        with self.assertRaisesRegex(ValueError, "privacy scan failed"):
            build_pilot_package(records, canaries={"private": "CANARY-PRIVATE"})

    def test_full_v1_synthetic_dry_run_without_provider_execution(self):
        task_ids = [
            f"{family}-{variant}"
            for family in ("work", "design", "write")
            for variant in ("primary", "held-out")
        ]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            run_root = base / "private-run"
            fixture_hashes = {}
            instruction_hashes = {}
            for index, task_id in enumerate(task_ids):
                source = _init_fixture_repo(
                    base / f"source-{task_id}",
                    {
                        "brief.md": f"Synthetic bounded task {index}.\n",
                        "policy.json": json.dumps(
                            {"task_id": task_id, "synthetic": True}, sort_keys=True
                        )
                        + "\n",
                        "checks.json": json.dumps(
                            {"required_outputs": ["result.txt"]}, sort_keys=True
                        )
                        + "\n",
                        "start.txt": "fictional input\n",
                    },
                )
                sealed = seal_fixture(source, run_root, task_id)
                lock = load_fixture_lock(run_root, task_id)
                self.assertEqual(lock["fixture_sha256"], verify_fixture(sealed))
                fixture_hashes[task_id] = lock["fixture_sha256"]
                instruction_hashes[task_id] = sha256_bytes(
                    (source / "brief.md").read_bytes()
                )

            systems = []
            for host, marker in (("codex", "a"), ("claude", "d")):
                systems.append(
                    build_system_freeze(
                        host=host,
                        menu_label=f"Synthetic {host.title()} Full",
                        model_id=f"synthetic-{host}",
                        host_version="test-only",
                        run_argv=[sys.executable, "-c", "print('not executed')"],
                        ditto_install_argv=[
                            sys.executable,
                            "-c",
                            "print('not executed')",
                        ],
                        screenshot_sha256=marker * 64,
                        tool_policy_sha256="b" * 64,
                        permission_policy_sha256="c" * 64,
                        quota_snapshot="synthetic; no provider quota",
                        expected_cost="zero; command is never executed",
                    )
                )
            pairs = build_pairs(
                systems,
                fixture_hashes,
                instruction_hashes,
                profile_manifest_sha256="9" * 64,
                budgets={
                    "work": {"time_seconds": 30, "max_turns": 2},
                    "design": {"time_seconds": 30, "max_turns": 2},
                    "write": {"time_seconds": 30, "max_turns": 2},
                },
                seed="8" * 64,
            )
            manifest = build_manifest(
                systems,
                pairs,
                profile_manifest_sha256="9" * 64,
                private_rubric_sha256="7" * 64,
                public_rubric_sha256="6" * 64,
                limitations=["synthetic dry run; no provider execution"],
                created_at="2026-07-15T00:00:00Z",
            )

            prepared = [
                prepare_cell(manifest, cell, run_root)
                for pair in manifest["pairs"]
                for cell in pair["cells"]
            ]
            self.assertEqual(48, len({item.workspace for item in prepared}))
            self.assertEqual(48, len({item.home for item in prepared}))

            store = EvidenceStore(
                run_root,
                {
                    cell["cell_id"]: cell
                    for pair in manifest["pairs"]
                    for cell in pair["cells"]
                },
            )
            records = []
            for pair in manifest["pairs"]:
                outputs = {}
                pair_records = []
                for cell in pair["cells"]:
                    attempt = {
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
                    }
                    attempt_receipt = store.record_attempt(cell["cell_id"], attempt)
                    artifact_sha256 = sha256_bytes(
                        canonical_bytes({"synthetic_cell": cell["cell_id"]})
                    )
                    evaluation_sha256 = store.record_evaluation(
                        cell["cell_id"],
                        {
                            "schema": "ditto-proof-evaluation/1",
                            "cell_id": cell["cell_id"],
                            "checks": {"synthetic_contract": True},
                            "hard_failures": [],
                            "artifact_hashes": [artifact_sha256],
                            "redaction_state": "passed",
                        },
                    )
                    outputs[cell["review_id"]] = {
                        "artifact_sha256": artifact_sha256,
                        "sanitized_output": "fictional synthetic output",
                    }
                    pair_records.append(
                        {
                            "cell_id": cell["cell_id"],
                            "pair_id": cell["pair_id"],
                            "condition": cell["condition"],
                            "family": cell["family"],
                            "publication_status": "eligible",
                            "hard_failures": [],
                            "objective_result_sha256": evaluation_sha256,
                            "artifact_hashes": [artifact_sha256],
                            "retry_history": [],
                            "review_status": "valid",
                            "preference": None,
                            "invalidation_reason": "",
                            "attempt_sha256": attempt_receipt["sha256"],
                            "evaluation_sha256": evaluation_sha256,
                            "review_sha256": None,
                            "redaction_state": "passed",
                        }
                    )
                packet = build_blind_pair(pair, outputs)
                self.assertEqual("paired-review/1", packet["schema"])
                ordered = sorted(pair["cells"], key=lambda item: item["order"])
                review_record = {
                    "schema": "ditto-proof-review/1",
                    "review_id": f"decision-{pair['pair_id']}",
                    "pair_id": pair["pair_id"],
                    "family": pair["family"],
                    "reviewer_role": "independent",
                    "consent_reference": "synthetic-consent",
                    "eligibility_attestation": "synthetic independent reviewer",
                    "unfamiliar_with_operator_voice": True,
                    "blinding_confirmed": True,
                    "verdict": "tie",
                    "left_review_id": ordered[0]["review_id"],
                    "right_review_id": ordered[1]["review_id"],
                    "invalidation_reason": "",
                    "created_at": "2026-07-15T00:00:00Z",
                }
                checked_review = validate_review(review_record, pair["family"])
                pair_records[0]["review_sha256"] = store.record_review(
                    pair_records[0]["cell_id"], review_record
                )
                pair_records[0]["preference"] = reveal_verdict(checked_review, pair)
                records.extend(pair_records)

            approval = publication_approval_digest(manifest, records)
            publication = build_publication(
                manifest, records, approval, evidence_store=store
            )
            expected_hashes = {
                item["cell_id"]: sha256_bytes(canonical_bytes(item)) for item in records
            }
            self.assertEqual(
                expected_hashes,
                {
                    item["cell_id"]: item["sha256"]
                    for item in publication["record_hashes"]
                },
            )

            leaked = dict(records[0])
            leaked["cell_id"] = "excluded-synthetic-leak"
            leaked["publication_status"] = "superseded"
            leaked["retry_history"] = [{"reason": "SEEDED-PRIVATE-CANARY"}]
            leaked_publication = build_publication(
                manifest,
                records + [leaked],
                publication_approval_digest(manifest, records + [leaked]),
                evidence_store=store,
            )
            with self.assertRaisesRegex(ValueError, "privacy scan failed"):
                render_index(
                    leaked_publication,
                    base / "rejected-publication",
                    canaries={"seeded": "SEEDED-PRIVATE-CANARY"},
                )

            first = base / "public-a"
            second = base / "public-b"
            render_index(publication, first, canaries={})
            render_index(publication, second, canaries={})
            self.assertEqual(
                (first / "results.json").read_bytes(),
                (second / "results.json").read_bytes(),
            )
            scanned = scan_public_tree(first, canaries={}, manual_review_approved=True)
            self.assertTrue(scanned["passed"])
            self.assertEqual(48, publication["cell_count"])


if __name__ == "__main__":
    unittest.main()
