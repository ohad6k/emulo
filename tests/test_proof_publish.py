import json
import tempfile
import unittest
from pathlib import Path

from proof.canonical import canonical_bytes
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


def _records(manifest, count=48):
    values = []
    cells = [cell for pair in manifest["pairs"] for cell in pair["cells"]]
    for index, cell in enumerate(cells[:count]):
        record = {
            "cell_id": cell["cell_id"],
            "pair_id": cell["pair_id"],
            "condition": cell["condition"],
            "family": cell["family"],
            "publication_status": "eligible",
            "hard_failures": (["unsupported_claim"] if index == 3 else []),
            "objective_result_sha256": f"{index + 101:064x}",
            "artifact_hashes": [f"{index + 201:064x}"],
            "retry_history": [],
            "review_status": "valid",
            "preference": None,
            "invalidation_reason": "",
        }
        # One frozen preference per pair, never one vote per cell.
        if cell["order"] == 1:
            record["preference"] = ("ditto", "cold", "tie")[index % 3]
        values.append(record)
    return values


class PublishTest(unittest.TestCase):
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

    def test_public_outcomes_keep_failures_invalidations_and_exclusions(self):
        manifest = _manifest()
        records = _records(manifest)
        writing = next(
            item
            for item in records
            if item["family"] == "write" and item["preference"] is not None
        )
        writing["review_status"] = "invalid"
        writing["invalidation_reason"] = "reviewer recognized operator voice"
        excluded = dict(records[0])
        excluded["cell_id"] = "superseded-attempt"
        excluded["publication_status"] = "superseded"
        excluded["retry_history"] = [{"reason": "provider outage"}]
        all_records = records + [excluded]

        result = build_publication(
            manifest,
            all_records,
            publication_approval_digest(manifest, all_records),
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
