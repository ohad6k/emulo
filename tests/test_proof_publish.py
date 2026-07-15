import json
import tempfile
import unittest
from pathlib import Path

from proof.canonical import canonical_bytes, sha256_bytes
from proof.evaluate import wilson_interval
from proof.manifest import build_manifest, build_pairs, build_system_freeze
from proof.publish import (
    aggregate_preferences,
    build_publication,
    publication_approval_digest,
    render_index,
)
from proof.schema import validate_publication_record


TASK_IDS = (
    "work-primary",
    "work-held-out",
    "design-primary",
    "design-held-out",
    "write-primary",
    "write-held-out",
)


def _systems():
    values = []
    for host, marker in (("codex", "a"), ("claude", "d")):
        values.append(
            build_system_freeze(
                host=host,
                menu_label=f"Visible {host.title()} Label",
                model_id=f"model-{host}",
                host_version="1.0",
                run_argv=[host, "run"],
                ditto_install_argv=["python", "install.py"],
                screenshot_sha256=marker * 64,
                tool_policy_sha256="b" * 64,
                permission_policy_sha256="c" * 64,
                quota_snapshot="synthetic quota receipt",
                expected_cost="not executed",
            )
        )
    return values


def _manifest():
    systems = _systems()
    pairs = build_pairs(
        systems,
        {task_id: f"{index + 1:064x}" for index, task_id in enumerate(TASK_IDS)},
        {task_id: f"{index + 11:064x}" for index, task_id in enumerate(TASK_IDS)},
        "9" * 64,
        {
            "work": {"time_seconds": 900, "max_turns": 40},
            "design": {"time_seconds": 900, "max_turns": 40},
            "write": {"time_seconds": 600, "max_turns": 20},
        },
        "8" * 64,
    )
    return build_manifest(
        systems,
        pairs,
        profile_manifest_sha256="9" * 64,
        private_rubric_sha256="7" * 64,
        public_rubric_sha256="6" * 64,
        limitations=["synthetic fixture; no provider was executed"],
        created_at="2026-07-15T00:00:00Z",
    )


class MemoryEvidence:
    def __init__(self):
        self._events = {}
        self._values = {}

    def add(self, cell_id, kind, value):
        digest = sha256_bytes(canonical_bytes(value) + b"\n")
        event = {"sha256": digest, "value": value}
        self._events.setdefault((cell_id, kind), []).append(event)
        self._values[digest] = value
        return digest

    def events(self, cell_id, kind):
        return list(self._events.get((cell_id, kind), []))

    def load(self, digest):
        return self._values[digest]


class EvidenceRecords(list):
    pass


def _records(manifest, count=48):
    values = EvidenceRecords()
    values.evidence_store = MemoryEvidence()
    index = 0
    for pair_index, pair in enumerate(manifest["pairs"]):
        desired = ("ditto", "cold", "tie")[pair_index % 3]
        ordered = sorted(pair["cells"], key=lambda item: item["order"])
        if desired == "tie":
            blind_verdict = "tie"
        else:
            selected = next(cell for cell in ordered if cell["condition"] == desired)
            blind_verdict = "left" if selected["order"] == 1 else "right"
        review = {
            "schema": "ditto-proof-review/1",
            "review_id": f"decision-{pair_index:02d}",
            "pair_id": pair["pair_id"],
            "family": pair["family"],
            "reviewer_role": "independent",
            "consent_reference": f"consent-{pair_index:02d}",
            "eligibility_attestation": "independent synthetic reviewer",
            "unfamiliar_with_operator_voice": True,
            "blinding_confirmed": True,
            "verdict": blind_verdict,
            "left_review_id": ordered[0]["review_id"],
            "right_review_id": ordered[1]["review_id"],
            "invalidation_reason": "",
            "created_at": "2026-07-15T00:00:00Z",
        }
        for cell in pair["cells"]:
            failures = ["unsupported_claim"] if index == 3 else []
            artifacts = [f"{index + 201:064x}"]
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
            attempt_sha256 = values.evidence_store.add(
                cell["cell_id"], "attempts", attempt
            )
            evaluation = {
                "schema": "ditto-proof-evaluation/1",
                "cell_id": cell["cell_id"],
                "hard_failures": failures,
                "artifact_hashes": artifacts,
                "redaction_state": "passed",
            }
            evaluation_sha256 = values.evidence_store.add(
                cell["cell_id"], "evaluations", evaluation
            )
            review_sha256 = None
            preference = None
            if cell["order"] == 1:
                review_sha256 = values.evidence_store.add(
                    cell["cell_id"], "reviews", review
                )
                preference = desired
            values.append(
                {
                    "cell_id": cell["cell_id"],
                    "pair_id": cell["pair_id"],
                    "condition": cell["condition"],
                    "family": cell["family"],
                    "publication_status": "eligible",
                    "hard_failures": failures,
                    "objective_result_sha256": evaluation_sha256,
                    "artifact_hashes": artifacts,
                    "retry_history": [],
                    "review_status": "valid",
                    "preference": preference,
                    "invalidation_reason": "",
                    "attempt_sha256": attempt_sha256,
                    "evaluation_sha256": evaluation_sha256,
                    "review_sha256": review_sha256,
                    "redaction_state": "passed",
                }
            )
            index += 1
    del values[count:]
    return values


class PublishTest(unittest.TestCase):
    def test_publication_requires_hash_bound_evidence_store(self):
        manifest = _manifest()
        records = _records(manifest)
        with self.assertRaisesRegex(ValueError, "evidence store"):
            build_publication(
                manifest,
                list(records),
                publication_approval_digest(manifest, records),
            )

    def test_publication_rejects_unstored_retry_history(self):
        manifest = _manifest()
        records = _records(manifest)
        records[0]["retry_history"] = [{"reason": "invented retry"}]
        with self.assertRaisesRegex(ValueError, "retry history"):
            build_publication(
                manifest,
                records,
                publication_approval_digest(manifest, records),
            )

    def test_preference_excludes_ties_and_keeps_tie_count(self):
        result = aggregate_preferences(["ditto", "cold", "tie", "ditto"])
        self.assertEqual(
            {
                "ditto_wins": 2,
                "cold_wins": 1,
                "ties": 1,
                "binary_denominator": 3,
                "raw_denominator": 4,
            },
            result["counts"],
        )
        self.assertEqual(wilson_interval(2, 3), result["ditto_wilson_95"])

    def test_package_refuses_47_cells(self):
        manifest = _manifest()
        records = _records(manifest, 47)
        with self.assertRaisesRegex(ValueError, "48 valid cells"):
            build_publication(
                manifest,
                records,
                ship_approval=publication_approval_digest(manifest, records),
            )

    def test_package_refuses_wrong_cell_or_duplicate(self):
        manifest = _manifest()
        records = _records(manifest)
        records[-1]["cell_id"] = records[0]["cell_id"]
        with self.assertRaisesRegex(ValueError, "frozen 48-cell matrix"):
            publication_approval_digest(manifest, records)

    def test_package_refuses_forged_frozen_identity_fields(self):
        manifest = _manifest()
        for field, value in (
            ("pair_id", "pair-forged"),
            ("family", "write"),
            ("condition", "ditto"),
        ):
            records = _records(manifest)
            target = next(
                record for record in records if record[field] != value
            )
            target[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "frozen cell identity"
            ):
                publication_approval_digest(manifest, records)

    def test_every_frozen_pair_has_one_review_contribution(self):
        manifest = _manifest()
        records = _records(manifest)
        contribution = next(item for item in records if item["preference"] is not None)
        contribution["preference"] = None
        with self.assertRaisesRegex(ValueError, "one review contribution"):
            publication_approval_digest(manifest, records)

    def test_package_refuses_profile_rubric_as_headline(self):
        manifest = _manifest()
        records = _records(manifest)
        value = build_publication(
            manifest,
            records,
            publication_approval_digest(manifest, records),
        )
        value["headline_metric"] = "profile_rubric_adherence"
        with self.assertRaisesRegex(ValueError, "mechanism only"):
            validate_publication_record(value)

    def test_exact_ship_digest_is_required(self):
        manifest = _manifest()
        records = _records(manifest)
        with self.assertRaisesRegex(PermissionError, "exact evidence digest"):
            build_publication(manifest, records, "0" * 64)

    def test_ship_digest_binds_exclusions_and_is_record_order_independent(self):
        manifest = _manifest()
        records = _records(manifest)
        excluded = dict(records[0])
        excluded["cell_id"] = "superseded-attempt"
        excluded["publication_status"] = "superseded"
        excluded["retry_history"] = [{"reason": "provider outage"}]
        with_exclusion = records + [excluded]
        digest = publication_approval_digest(manifest, with_exclusion)

        changed = [dict(item) for item in with_exclusion]
        changed[-1]["retry_history"] = [{"reason": "different reason"}]
        self.assertNotEqual(digest, publication_approval_digest(manifest, changed))
        self.assertEqual(
            digest,
            publication_approval_digest(manifest, list(reversed(with_exclusion))),
        )

    def test_public_outcomes_keep_failures_invalidations_and_exclusions(self):
        manifest = _manifest()
        records = _records(manifest)
        writing = next(
            item
            for item in records
            if item["family"] == "write" and item["preference"] is not None
        )
        invalid_review = dict(records.evidence_store.load(writing["review_sha256"]))
        invalid_review["unfamiliar_with_operator_voice"] = False
        invalid_review["verdict"] = None
        writing["review_sha256"] = records.evidence_store.add(
            writing["cell_id"], "reviews", invalid_review
        )
        writing["review_status"] = "invalid"
        writing["preference"] = None
        writing["invalidation_reason"] = "reviewer familiar with operator voice"
        excluded = dict(records[0])
        excluded["cell_id"] = "superseded-attempt"
        excluded["publication_status"] = "superseded"
        excluded["retry_history"] = [{"reason": "provider outage"}]
        all_records = records + [excluded]

        result = build_publication(
            manifest,
            all_records,
            publication_approval_digest(manifest, all_records),
            evidence_store=records.evidence_store,
        )

        self.assertEqual(48, result["cell_count"])
        self.assertEqual(48, len(result["valid_cells"]))
        self.assertEqual(1, result["hard_failures"]["cold"]["total"] + result["hard_failures"]["ditto"]["total"])
        self.assertEqual(1, len(result["invalidations"]))
        self.assertEqual(1, len(result["exclusions"]))
        self.assertEqual(23, result["preferences"]["overall"]["counts"]["raw_denominator"])
        self.assertNotIn("profile", canonical_bytes(result).decode("ascii").lower())

    def test_output_states_scope_and_forbids_inflated_claims(self):
        manifest = _manifest()
        records = _records(manifest)
        result = build_publication(
            manifest,
            records,
            publication_approval_digest(manifest, records),
        )
        text = canonical_bytes(result).decode("ascii").lower()
        for required in (
            "complete-system comparison",
            "clean-host cold start",
            "small-n, directional only",
        ):
            self.assertIn(required, text)
        for forbidden in (
            "p-value",
            "statistically significant",
            "model ranking",
            "1000x",
            "star forecast",
            "traffic forecast",
        ):
            self.assertNotIn(forbidden, text)

    def test_render_is_byte_identical_and_privacy_scanned(self):
        manifest = _manifest()
        records = _records(manifest)
        publication = build_publication(
            manifest,
            records,
            publication_approval_digest(manifest, records),
        )
        with tempfile.TemporaryDirectory() as root:
            left = Path(root) / "left"
            right = Path(root) / "right"
            render_index(publication, left, canaries={"secret": "PRIVATE-CANARY"})
            render_index(publication, right, canaries={"secret": "PRIVATE-CANARY"})
            self.assertEqual(
                (left / "index.html").read_bytes(),
                (right / "index.html").read_bytes(),
            )
            self.assertEqual(
                (left / "results.json").read_bytes(),
                (right / "results.json").read_bytes(),
            )
            loaded = json.loads((left / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(publication, loaded)


if __name__ == "__main__":
    unittest.main()
