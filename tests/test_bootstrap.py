import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = ROOT / ".agents" / "skills" / "emulo" / "scripts" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("emulo_bootstrap", BOOTSTRAP_PATH)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata(version="0.0.0-dev", ref=None, py_hash=None, prompt_hash=None):
    return {
        "schema_version": "1",
        "version": version,
        "ref": ref,
        "files": {
            "emulo.py": {"sha256": py_hash},
            "MINING_PROMPT.md": {"sha256": prompt_hash},
        },
    }


class BootstrapTest(unittest.TestCase):
    def make_source(self, root):
        source = root / "source"
        source.mkdir()
        (source / "emulo.py").write_bytes(b"print('emulo')\n")
        (source / "MINING_PROMPT.md").write_bytes(b"# prompt\n")
        return source

    def test_dev_metadata_refuses_network_without_source_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "development runtime requires --source-root"):
                bootstrap.install_runtime(metadata(), str(Path(tmp) / "private"))

    def test_repository_runtime_metadata_is_valid(self):
        value = bootstrap.load_metadata(ROOT / ".agents" / "skills" / "emulo" / "runtime.json")
        self.assertEqual(value, bootstrap.validate_metadata(value))

    def test_release_runtime_hashes_match_canonical_repository_bytes(self):
        value = bootstrap.load_metadata(ROOT / ".agents" / "skills" / "emulo" / "runtime.json")
        self.assertEqual("v0.6.0", value["ref"])
        for name in ("emulo.py", "MINING_PROMPT.md"):
            canonical = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(digest(canonical), value["files"][name]["sha256"])

    def test_source_root_installs_both_files_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            home = root / "private"
            result = bootstrap.install_runtime(metadata(), str(home), source_root=str(source))
            runtime = Path(result["runtime_dir"])
            self.assertEqual(b"print('emulo')\n", (runtime / "emulo.py").read_bytes())
            self.assertEqual(b"# prompt\n", (runtime / "MINING_PROMPT.md").read_bytes())
            self.assertTrue(str(runtime).startswith(str(home)))
            self.assertTrue((home / "runtime" / "current.json").is_file())

    def test_hash_mismatch_preserves_previous_runtime_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            home = root / "private"
            bootstrap.install_runtime(metadata(), str(home), source_root=str(source))
            pointer = home / "runtime" / "current.json"
            before = pointer.read_bytes()
            release = metadata("0.2.0", "v0.2.0", "0" * 64, digest(b"# prompt\n"))
            with self.assertRaisesRegex(ValueError, "sha256 mismatch for emulo.py"):
                bootstrap.install_runtime(release, str(home), source_root=str(source))
            self.assertEqual(before, pointer.read_bytes())


if __name__ == "__main__":
    unittest.main()
