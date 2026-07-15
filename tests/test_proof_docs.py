import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "proof" / "README.md"


class ProofDocumentationTest(unittest.TestCase):
    def test_runbook_preserves_every_gate(self):
        text = RUNBOOK.read_text(encoding="utf-8")
        required = (
            "48 isolated cell executions",
            "clean-host cold start",
            "small-n, directional only",
            "independent third party",
            "Ohad cannot cast a blind verdict",
            "explicit cost approval",
            "explicit ship approval",
            "v0.3.7",
            "held-out",
            "private run root outside the repository",
            "both attempts are retained",
            "unavailable systems are not substituted",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_names_commands_and_all_private_fixture_ids(self):
        text = RUNBOOK.read_text(encoding="utf-8")
        for command in (
            "validate",
            "freeze-system",
            "prepare-cell",
            "execute-cell",
            "evaluate",
            "package",
        ):
            self.assertIn(f"python -m proof.cli {command}", text)
        for family in ("work", "design", "write"):
            for variant in ("primary", "held-out"):
                self.assertIn(f"{family}-{variant}", text)
        for filename in ("brief.md", "policy.json", "checks.json"):
            self.assertIn(filename, text)

    def test_consent_and_invalidation_contracts_are_explicit(self):
        text = RUNBOOK.read_text(encoding="utf-8")
        for field in (
            '"consent_reference"',
            '"eligibility_attestation"',
            '"unfamiliar_with_operator_voice"',
            '"blinding_confirmed"',
            '"verdict"',
            '"invalidation_reason"',
        ):
            self.assertIn(field, text)
        self.assertIn("recognizing the operator or condition ends the review", text)

    def test_docs_make_no_new_benchmark_result_claim_before_execution(self):
        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertNotIn("Ditto wins", text)
        self.assertNotIn("statistically significant", text)
        self.assertIn("no public result exists", text)

    def test_private_roots_are_ignored_and_readme_marks_method_unexecuted(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for path in (".ditto-proof-private/", "proof-private/", "ditto-proof-runs/"):
            self.assertIn(path, ignored)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/proof/README.md", readme)
        self.assertIn("unexecuted methodology", readme)

    def test_example_is_explicitly_synthetic_non_scored_and_non_comparable(self):
        example = ROOT / "docs" / "proof" / "example-publication"
        result = json.loads((example / "results.json").read_text(encoding="utf-8"))
        self.assertEqual("synthetic-example", result["label"])
        self.assertFalse(result["scored"])
        self.assertFalse(result["comparable"])
        self.assertIn("synthetic", (example / "index.html").read_text("utf-8").lower())

    def test_verification_receipt_preserves_observed_boundaries(self):
        text = (ROOT / "docs" / "proof" / "implementation-verification.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "7b584430dc6f0df33cd6ce3453e70f496d1ca3e0",
            "Python 3.11.4",
            "266 tests",
            "26.333s",
            "90 proof tests",
            "fresh Windows clone",
            "e08c4e23921065839a234530261aae3f466c517fa0b93214669990f4dbdbe9ab",
            "no provider execution",
            "no scored fixture execution",
            "no public result",
            "no Antigravity dependency",
            "no modification to normal Ditto behavior",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
