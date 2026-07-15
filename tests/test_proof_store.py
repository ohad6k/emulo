import tempfile
import unittest
from pathlib import Path

from proof.store import EvidenceStore, validate_attempt_identity


def attempt(exit_status="ok", meaningful=True):
    return {
        "schema": "ditto-proof-attempt/1",
        "cell_id": "cell-a",
        "pair_id": "pair-a",
        "system_id": "system-a",
        "fixture_sha256": "a" * 64,
        "instruction_sha256": "b" * 64,
        "profile_manifest_sha256": None,
        "tool_policy_sha256": "c" * 64,
        "permission_policy_sha256": "d" * 64,
        "budget": {"time_seconds": 60, "max_turns": 2},
        "workspace_sha256": "e" * 64,
        "exit_status": exit_status,
        "meaningful_output": meaningful,
    }


def cell():
    return {
        "cell_id": "cell-a",
        "pair_id": "pair-a",
        "system_id": "system-a",
        "fixture_sha256": "a" * 64,
        "instruction_sha256": "b" * 64,
        "profile_manifest_sha256": None,
        "tool_policy_sha256": "c" * 64,
        "permission_policy_sha256": "d" * 64,
        "budget": {"time_seconds": 60, "max_turns": 2},
    }


def evaluation():
    return {
        "schema": "ditto-proof-evaluation/1",
        "cell_id": "cell-a",
        "hard_failures": [],
        "checks": {"tests": "passed"},
        "supersedes_sha256": None,
        "supersession_reason": "",
    }


class EvidenceStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = EvidenceStore(self.root, {"cell-a": cell()})

    def tearDown(self):
        self.temporary.cleanup()

    def test_model_failure_is_scored_without_retry(self):
        self.store.record_attempt("cell-a", attempt("model_error", meaningful=True))

        with self.assertRaisesRegex(ValueError, "result, not retryable"):
            self.store.authorize_retry("cell-a", "operator-approved provider retry")

    def test_provider_failure_allows_one_retained_retry(self):
        self.store.record_attempt("cell-a", attempt("provider_error", meaningful=False))
        authorization = self.store.authorize_retry("cell-a", "provider failed before output")
        self.store.record_attempt("cell-a", attempt("ok", meaningful=True))

        self.assertEqual(2, len(self.store.attempts("cell-a")))
        self.assertEqual(1, len(self.store.events("cell-a", "retry-authorizations")))
        self.assertEqual(authorization["sha256"], self.store.events("cell-a", "retry-authorizations")[0]["sha256"])
        with self.assertRaisesRegex(ValueError, "one retry"):
            self.store.authorize_retry("cell-a", "another")

    def test_second_attempt_requires_authorization(self):
        self.store.record_attempt("cell-a", attempt("provider_error", meaningful=False))

        with self.assertRaisesRegex(ValueError, "retry authorization"):
            self.store.record_attempt("cell-a", attempt("ok", meaningful=True))

    def test_correction_creates_superseding_record_and_keeps_prior(self):
        first = self.store.record_evaluation("cell-a", evaluation())
        second = self.store.supersede_evaluation(
            "cell-a", first, "clerical correction", evaluation()
        )

        self.assertNotEqual(first, second)
        self.assertEqual(first, self.store.load(second)["supersedes_sha256"])
        self.assertEqual("", self.store.load(first)["supersession_reason"])
        self.assertEqual(2, len(self.store.events("cell-a", "evaluations")))

    def test_identity_mismatch_invalidates_attempt(self):
        changed = attempt()
        changed["fixture_sha256"] = "f" * 64

        with self.assertRaisesRegex(ValueError, "fixture_sha256 mismatch"):
            validate_attempt_identity(changed, cell())
        with self.assertRaisesRegex(ValueError, "fixture_sha256 mismatch"):
            self.store.record_attempt("cell-a", changed)

    def test_evaluation_can_only_supersede_prior_evaluation(self):
        attempt_receipt = self.store.record_attempt("cell-a", attempt())

        with self.assertRaisesRegex(ValueError, "prior evaluation"):
            self.store.supersede_evaluation(
                "cell-a", attempt_receipt["sha256"], "wrong event kind", evaluation()
            )

    def test_cell_id_cannot_escape_run_root(self):
        with self.assertRaisesRegex(ValueError, "cell ID"):
            self.store.record_attempt("../escape", attempt())

    def test_invalidation_is_append_only(self):
        first = self.store.record_invalidation("cell-a", "workspace contamination", "pair")
        second = self.store.record_invalidation("cell-a", "blind label leak", "review")

        self.assertNotEqual(first, second)
        self.assertEqual(2, len(self.store.events("cell-a", "invalidations")))


if __name__ == "__main__":
    unittest.main()
