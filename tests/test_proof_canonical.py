import json
import tempfile
import unittest
from pathlib import Path

from proof.canonical import (
    canonical_bytes,
    safe_child,
    sha256_bytes,
    sha256_file,
    write_once_json,
)


class CanonicalEvidenceTest(unittest.TestCase):
    def test_canonical_json_is_order_independent_and_utf8_exact(self):
        left = canonical_bytes({"hebrew": "שלום", "count": 2})
        right = canonical_bytes({"count": 2, "hebrew": "שלום"})

        self.assertEqual(left, right)
        self.assertEqual(
            b'{"count":2,"hebrew":"\\u05e9\\u05dc\\u05d5\\u05dd"}',
            left,
        )

    def test_hash_helpers_are_byte_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.txt"
            path.write_bytes("תוצאה\n".encode("utf-8"))

            self.assertEqual(sha256_bytes(path.read_bytes()), sha256_file(path))

    def test_safe_child_rejects_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "outside root"):
                safe_child(Path(tmp), "..", "escape")

    def test_write_once_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            digest = write_once_json(path, {"state": "first"})

            self.assertEqual(sha256_bytes(path.read_bytes()), digest)
            self.assertEqual(
                {"state": "first"}, json.loads(path.read_text(encoding="utf-8"))
            )
            with self.assertRaises(FileExistsError):
                write_once_json(path, {"state": "second"})
            self.assertEqual(
                {"state": "first"}, json.loads(path.read_text(encoding="utf-8"))
            )


if __name__ == "__main__":
    unittest.main()
