import tempfile
import unittest
from pathlib import Path

from proof.privacy import sanitize_text, scan_public_text, scan_public_tree


CANARIES = {
    "secret": "sk-proof-canary-1234567890",
    "username": "private-user-canary",
    "windows_path": r"C:\Users\private-canary\vault",
    "unix_path": "/home/private-canary/vault",
    "profile": "PROFILE-CANARY-do-not-publish",
    "receipt": "RECEIPT-CANARY-do-not-publish",
}


class PrivacyTest(unittest.TestCase):
    def test_every_seeded_private_marker_blocks_packaging(self):
        for kind, marker in CANARIES.items():
            with self.subTest(kind=kind):
                result = scan_public_text(f"safe before {marker} safe after", CANARIES)
                self.assertFalse(result["passed"])
                self.assertIn(kind, result["findings"])

    def test_secret_and_local_path_patterns_block(self):
        samples = {
            "secret-pattern": "api_key = super-secret-value",
            "local-path": r"opened C:\Users\ohad\vault\note.md",
            "home-path": "opened /home/ohad/vault/note.md",
        }
        for finding, sample in samples.items():
            with self.subTest(finding=finding):
                self.assertIn(finding, scan_public_text(sample, {})["findings"])

    def test_hebrew_round_trip_survives_when_safe(self):
        text = "תוצאה ציבורית בטוחה"

        self.assertEqual(text, sanitize_text(text, canaries={}))

    def test_tree_requires_manual_review_and_scans_every_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("safe", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "manual privacy review"):
                scan_public_tree(root, CANARIES, manual_review_approved=False)
            self.assertTrue(
                scan_public_tree(root, CANARIES, manual_review_approved=True)["passed"]
            )
            (root / "results.json").write_text(CANARIES["profile"], encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "profile"):
                scan_public_tree(root, CANARIES, manual_review_approved=True)

    def test_tree_rejects_hidden_raw_profile_and_unknown_extension(self):
        cases = {
            ".private": "hidden file",
            "you.md": "raw profile",
            "session-transcript.json": "raw transcript",
            "environment.env": "unrecognized extension",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / filename).write_text("safe", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, expected):
                    scan_public_tree(root, {}, manual_review_approved=True)

    def test_private_root_string_blocks_even_without_canary(self):
        with tempfile.TemporaryDirectory() as tmp:
            private_root = str(Path(tmp).resolve())
            result = scan_public_text(
                f"artifact came from {private_root}", {}, private_roots=[private_root]
            )

            self.assertFalse(result["passed"])
            self.assertIn("private-root", result["findings"])

    def test_binary_artifact_blocks_secret_path_and_private_root_without_canary(self):
        samples = (
            b"png-prefix api_key=super-secret-value png-suffix",
            rb"png-prefix C:\Users\private-canary\vault png-suffix",
        )
        for payload in samples:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "frame.png").write_bytes(payload)
                with self.assertRaisesRegex(ValueError, "binary artifact"):
                    scan_public_tree(
                        root,
                        {},
                        manual_review_approved=True,
                        private_roots=[r"C:\Users\private-canary\vault"],
                    )


if __name__ == "__main__":
    unittest.main()
