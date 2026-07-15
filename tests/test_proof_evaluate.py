import json
import unittest

from proof.evaluate import (
    build_blind_pair,
    evaluate_objective,
    reveal_verdict,
    validate_review,
    wilson_interval,
)


def valid_review():
    return {
        "reviewer_role": "independent",
        "consent_reference": "consent-record-sha256",
        "eligibility_attestation": "not Ohad; no stake in outcome",
        "blinding_confirmed": True,
        "unfamiliar_with_operator_voice": True,
        "verdict": "left",
    }


def pair(family="design"):
    return {
        "pair_id": "pair-a",
        "cells": [
            {
                "condition": "cold", "system_id": "system-codex", "order": 2,
                "review_id": "review-111", "family": family,
            },
            {
                "condition": "ditto", "system_id": "system-codex", "order": 1,
                "review_id": "review-222", "family": family,
            },
        ],
    }


class EvaluationTest(unittest.TestCase):
    def test_fabricated_test_claim_is_hard_failure(self):
        record = {
            "checks": {}, "hard_failures": [], "mechanism_checks": [],
            "claimed_tests": True, "test_report_sha256": None,
            "changed_paths": [], "actions": [], "claimed_complete": False,
        }
        result = evaluate_objective(record, {"family": "work", "allowed_paths": ["src/"]})

        self.assertIn("fabricated_test_result", result["hard_failures"])

    def test_allowed_path_boundary_does_not_accept_similar_prefix(self):
        record = {
            "checks": {}, "hard_failures": [], "mechanism_checks": [],
            "claimed_tests": False, "changed_paths": ["src/foobar.py"],
            "actions": [], "claimed_complete": False,
        }
        result = evaluate_objective(
            record, {"family": "work", "allowed_paths": ["src/foo"]}
        )

        self.assertIn("out_of_scope_change", result["hard_failures"])

    def test_operator_cannot_cast_blind_verdict(self):
        review = valid_review()
        review["reviewer_role"] = "operator"

        with self.assertRaisesRegex(ValueError, "independent third party"):
            validate_review(review, family="design")

    def test_writing_review_requires_unfamiliar_reviewer(self):
        review = valid_review()
        review["unfamiliar_with_operator_voice"] = False

        result = validate_review(review, family="write")

        self.assertEqual("invalid", result["status"])
        self.assertEqual("reviewer familiar with operator voice", result["invalidation_reason"])
        self.assertIsNone(result["verdict"])

    def test_blind_packet_contains_no_condition_system_path_or_order(self):
        frozen_pair = pair()
        outputs = {
            "review-111": {"artifact_sha256": "a" * 64, "sanitized_output": "left output"},
            "review-222": {"artifact_sha256": "b" * 64, "sanitized_output": "right output"},
        }

        packet = build_blind_pair(frozen_pair, outputs)
        encoded = json.dumps(packet).lower()

        for forbidden in ("cold", "ditto", "codex", "claude", "workspace", "order"):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual("review-222", packet["left"]["review_id"])

    def test_reveal_maps_left_right_only_to_frozen_condition(self):
        frozen_pair = pair()
        packet = build_blind_pair(
            frozen_pair,
            {
                "review-111": {"artifact_sha256": "a" * 64, "sanitized_output": "A"},
                "review-222": {"artifact_sha256": "b" * 64, "sanitized_output": "B"},
            },
        )
        review = validate_review({
            **valid_review(),
            "left_review_id": packet["left"]["review_id"],
            "right_review_id": packet["right"]["review_id"],
        }, family="design")

        self.assertEqual("ditto", reveal_verdict(review, frozen_pair))

    def test_reveal_rejects_unvalidated_or_invalid_review(self):
        with self.assertRaisesRegex(ValueError, "validated eligible review"):
            reveal_verdict({"verdict": "tie"}, pair())

    def test_writing_policy_catches_unsupported_hype_spam_and_em_dash(self):
        record = {
            "checks": {}, "hard_failures": [], "mechanism_checks": ["voice_match"],
            "claimed_tests": False, "changed_paths": [], "actions": [],
            "claimed_complete": False,
            "text_output": "Guaranteed 1000x results — star and repost now!",
            "claims": [{"kind": "metric", "supported": False}],
            "invented_testimonial": True,
            "false_availability": True,
            "privacy_leak": True,
        }

        result = evaluate_objective(
            record,
            {"family": "write", "allowed_paths": [], "channel": "x", "character_limit": 280},
        )

        self.assertEqual(["voice_match"], result["mechanism_checks"])
        self.assertTrue(
            {
                "unsupported_claim",
                "invented_testimonial",
                "false_availability",
                "privacy_leak",
                "spam_pressure",
                "prohibited_em_dash",
            }.issubset(result["hard_failures"])
        )

    def test_design_policy_catches_recolor_only_and_missing_render(self):
        record = {
            "checks": {"primary_flow": False, "accessibility_floor": False},
            "hard_failures": [], "mechanism_checks": [], "claimed_tests": False,
            "changed_paths": ["other/page.html"], "actions": [], "claimed_complete": True,
            "verification_sha256": "a" * 64, "recolor_only": True,
            "claimed_rendered_verification": True, "rendered_artifact_sha256": None,
        }

        result = evaluate_objective(record, {"family": "design", "allowed_paths": ["card/"]})

        self.assertTrue(
            {
                "out_of_scope_change", "broken_primary_flow", "failed_accessibility_floor",
                "recolor_only", "fabricated_visual_verification",
            }.issubset(result["hard_failures"])
        )

    def test_wilson_interval_handles_edges(self):
        self.assertIsNone(wilson_interval(0, 0))
        low, high = wilson_interval(0, 10)
        self.assertEqual(0.0, low)
        self.assertGreater(high, 0.0)
        low, high = wilson_interval(10, 10)
        self.assertLess(low, 1.0)
        self.assertEqual(1.0, high)


if __name__ == "__main__":
    unittest.main()
