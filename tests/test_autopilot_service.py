import tempfile
import unittest
from pathlib import Path

from emulo_autopilot import contracts
from emulo_autopilot.service import record_review, review_queue, status_snapshot
from emulo_autopilot.store import AutopilotStore
from tests.autopilot_helpers import candidate_fixture


class AutopilotServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = AutopilotStore(self.temp.name)

    def _candidate(self, **changes):
        candidate = candidate_fixture()
        candidate.update(changes)
        candidate["candidate_id"] = contracts.candidate_identity(candidate)
        self.store.put_candidate(candidate)
        return candidate

    def test_empty_status_is_versioned_and_ready(self):
        self.assertEqual(
            {
                "schema_version": "emulo.autopilot-status/v1",
                "health": "ready",
                "lock": None,
                "active_generation_id": None,
                "counts": {
                    "inbox": 0,
                    "candidates": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0,
                    "generations": 0,
                },
            },
            status_snapshot(self.store),
        )

    def test_status_reports_lock_and_active_generation_without_private_fields(self):
        candidate = self._candidate(statement="Keep the active service rule.")
        record_review(
            self.store,
            candidate["candidate_id"],
            "approve",
            "founder-review",
            "2026-07-16T14:00:00Z",
        )
        generation = self.store.activate(
            [candidate["candidate_id"]], "2026-07-16T14:01:00Z"
        )
        with self.store.lock("status-test") as lock:
            status = status_snapshot(self.store)
        self.assertEqual("locked", status["health"])
        self.assertEqual(
            {
                "operation_id": lock["operation_id"],
                "operation": "status-test",
                "created_at": lock["created_at"],
            },
            status["lock"],
        )
        self.assertNotIn("pid", status["lock"])
        self.assertNotIn("hostname", status["lock"])
        self.assertEqual(generation["generation_id"], status["active_generation_id"])
        self.assertEqual(1, status["counts"]["approved"])
        self.assertEqual(1, status["counts"]["generations"])

    def test_review_queue_exposes_bounded_evidence_metadata_and_policy(self):
        candidate = self._candidate(statement="Review the deployment proof.")
        queue = review_queue(self.store)
        self.assertEqual("emulo.autopilot-review-queue/v1", queue["schema_version"])
        self.assertEqual(1, len(queue["items"]))
        item = queue["items"][0]
        self.assertEqual(candidate["candidate_id"], item["candidate_id"])
        self.assertEqual("Review the deployment proof.", item["statement"])
        self.assertEqual("review", item["policy_class"])
        self.assertEqual("auto-disabled", item["policy_reason"])
        self.assertEqual("pending", item["decision"])
        self.assertEqual(3, item["evidence"]["sessions"])
        self.assertEqual(2, item["evidence"]["time_strata"])
        self.assertNotIn("receipts", item)
        self.assertNotIn("source_packet_hash", item)

    def test_record_review_is_append_only_and_newest_decision_wins(self):
        candidate = self._candidate()
        approved = record_review(
            self.store,
            candidate["candidate_id"],
            "approve",
            "founder-review",
            "2026-07-16T14:00:00Z",
        )
        rejected = record_review(
            self.store,
            candidate["candidate_id"],
            "reject",
            "newer-contradiction",
            "2026-07-16T14:01:00Z",
        )
        self.assertNotEqual(approved["decision_id"], rejected["decision_id"])
        item = review_queue(self.store)["items"][0]
        self.assertEqual("reject", item["decision"])
        self.assertEqual(rejected["decision_id"], item["decision_id"])
        self.assertEqual(2, len(list((Path(self.store.root) / "decisions").glob("*.json"))))

    def test_reject_policy_cannot_be_overridden_by_approval(self):
        candidate = self._candidate(risk_categories=["novel-risk"])
        with self.assertRaisesRegex(ValueError, "policy rejects"):
            record_review(
                self.store,
                candidate["candidate_id"],
                "approve",
                "founder-review",
                "2026-07-16T14:00:00Z",
            )
        rejected = record_review(
            self.store,
            candidate["candidate_id"],
            "reject",
            "unknown-risk",
            "2026-07-16T14:01:00Z",
        )
        self.assertEqual("reject", rejected["policy_class"])


if __name__ == "__main__":
    unittest.main()
