import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from proof.fixtures import (
    load_fixture_lock,
    reset_fixture,
    seal_fixture,
    tree_hash,
    tree_manifest,
    verify_fixture,
)


ROOT = Path(__file__).resolve().parents[1]


def init_repo(path, files):
    path.mkdir()
    for name, text in files.items():
        destination = path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8", newline="\n")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "proof@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Proof Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "fixture"],
        check=True,
    )
    return path


class FixtureTest(unittest.TestCase):
    def test_reset_is_byte_deterministic_and_matches_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = init_repo(root / "source", {"brief.txt": "שלום\n"})
            private = root / "private"
            sealed = seal_fixture(source, private, "work-primary")
            lock = load_fixture_lock(private, "work-primary")

            first = reset_fixture(sealed, root / "cell-a", lock["fixture_sha256"])
            second = reset_fixture(sealed, root / "cell-b", lock["fixture_sha256"])

            self.assertEqual(verify_fixture(first), verify_fixture(second))
            self.assertEqual(lock["fixture_sha256"], tree_hash(first))
            self.assertEqual("שלום\n", (first / "brief.txt").read_text("utf-8"))

    def test_seal_rejects_repository_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = init_repo(Path(tmp) / "source", {"brief.txt": "private\n"})

            with self.assertRaisesRegex(ValueError, "outside repository"):
                seal_fixture(source, ROOT / "proof-private", "write-held-out")

    def test_seal_requires_clean_committed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = init_repo(root / "source", {"brief.txt": "first\n"})
            (source / "brief.txt").write_text("changed\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "clean Git commit"):
                seal_fixture(source, root / "private", "work-primary")

    def test_seal_rejects_ignored_untracked_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = init_repo(
                root / "source",
                {"brief.txt": "private\n", ".gitignore": "secret.env\n"},
            )
            (source / "secret.env").write_text(
                "API_KEY=private-value\n", encoding="utf-8"
            )
            self.assertEqual("", subprocess.check_output(
                ["git", "-C", str(source), "status", "--porcelain"],
                text=True,
            ).strip())

            with self.assertRaisesRegex(ValueError, "untracked or ignored"):
                seal_fixture(source, root / "private", "work-primary")

    def test_seal_rejects_task_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = init_repo(root / "source", {"brief.txt": "private\n"})

            with self.assertRaisesRegex(ValueError, "task ID"):
                seal_fixture(source, root / "private", "../escape")

    def test_reset_refuses_existing_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "used"
            destination.mkdir()

            with self.assertRaisesRegex(FileExistsError, "must not exist"):
                reset_fixture(root / "sealed", destination)

    def test_verify_detects_changed_or_missing_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = init_repo(root / "source", {"brief.txt": "first\n"})
            sealed = seal_fixture(source, root / "private", "work-primary")
            expected = tree_hash(sealed)
            (sealed / "brief.txt").write_text("changed\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "fixture hash mismatch"):
                verify_fixture(sealed, expected)

    def test_runtime_bytecode_cache_does_not_change_fixture_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "module.py").write_text("value = 1\n", encoding="utf-8")
            expected = tree_hash(root)
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "module.cpython-311.pyc").write_bytes(b"runtime cache")

            self.assertEqual(expected, tree_hash(root))

    def test_tree_manifest_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            target.write_text("target", encoding="utf-8")
            link = root / "link.txt"
            try:
                os.symlink(target, link)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "symlink"):
                tree_manifest(root)

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_tree_manifest_rejects_windows_junctions(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "root"
            root.mkdir()
            target = base / "outside"
            target.mkdir()
            (target / "private.txt").write_text("outside", encoding="utf-8")
            junction = root / "junction"
            completed = subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(junction), str(target)],
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                self.skipTest(f"junction creation unavailable: {completed.stderr}")

            with self.assertRaisesRegex(ValueError, "symlink or reparse point"):
                tree_manifest(root)


if __name__ == "__main__":
    unittest.main()
