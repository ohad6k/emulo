"""Private fixture sealing, hashing, and deterministic reset helpers."""

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from proof.canonical import canonical_bytes, safe_child, sha256_bytes, sha256_file, write_once_json


TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _is_link_or_reparse(path):
    path = Path(path)
    metadata = path.lstat()
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _require_outside_repository(path, repository_root):
    candidate = Path(path).resolve()
    repository = Path(repository_root).resolve()
    try:
        candidate.relative_to(repository)
    except ValueError:
        return
    raise ValueError("private fixture root must be outside repository")


def tree_manifest(root):
    """Return a sorted, symlink-free manifest for regular files below root."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("fixture root must be a directory")
    rows = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories if name not in {".git", "__pycache__"}
        )
        for name in tuple(directories):
            if _is_link_or_reparse(current_path / name):
                raise ValueError("fixture tree must not contain a symlink or reparse point")
        for name in sorted(files):
            path = current_path / name
            if ".git" in path.relative_to(root).parts:
                continue
            if path.suffix.casefold() in {".pyc", ".pyo"}:
                continue
            if _is_link_or_reparse(path):
                raise ValueError("fixture tree must not contain a symlink or reparse point")
            if not path.is_file():
                raise ValueError("fixture tree contains a non-regular file")
            relative = path.relative_to(root).as_posix()
            if relative.startswith("/") or ".." in Path(relative).parts:
                raise ValueError("fixture path is not normalized")
            rows.append(
                {
                    "path": relative,
                    "sha256": sha256_file(path),
                    "size": path.stat().st_size,
                }
            )
    return rows


def tree_hash(root):
    return sha256_bytes(canonical_bytes(tree_manifest(root)))


def _git_text(source, *args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(source), *args],
            text=True,
            encoding="utf-8",
            stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError("fixture source must be a clean Git commit") from exc


def _git_tracked_files(source):
    try:
        payload = subprocess.check_output(
            ["git", "-C", str(source), "ls-files", "-z", "--cached"],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError("fixture source must be a clean Git commit") from exc
    return {
        item.decode("utf-8")
        for item in payload.split(b"\0")
        if item
    }


def seal_fixture(source, private_root, task_id, repository_root=None):
    """Copy one clean committed fixture into an immutable private run root."""
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("task ID must be normalized lowercase text")
    source = Path(source).resolve()
    private_root = Path(private_root).resolve()
    repository_root = Path(
        repository_root or Path(__file__).resolve().parents[1]
    ).resolve()
    _require_outside_repository(private_root, repository_root)
    if not source.is_dir():
        raise ValueError("fixture source must be a directory")
    if _git_text(source, "status", "--porcelain"):
        raise ValueError("fixture source must be a clean Git commit")
    fixture_commit = _git_text(source, "rev-parse", "HEAD")
    source_files = tree_manifest(source)
    if not source_files:
        raise ValueError("fixture source must contain at least one file")
    if {item["path"] for item in source_files} != _git_tracked_files(source):
        raise ValueError("fixture source contains untracked or ignored files")

    destination = safe_child(private_root, "sealed-fixtures", task_id)
    if destination.exists():
        raise FileExistsError("sealed fixture already exists")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git"))
    files = tree_manifest(destination)
    if files != source_files:
        raise ValueError("sealed fixture bytes changed during copy")
    lock = {
        "schema": "ditto-proof-fixture/1",
        "task_id": task_id,
        "fixture_commit": fixture_commit,
        "files": files,
        "fixture_sha256": sha256_bytes(canonical_bytes(files)),
    }
    write_once_json(
        safe_child(private_root, "fixture-locks", f"{task_id}.json"), lock
    )
    return destination


def load_fixture_lock(private_root, task_id):
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("task ID must be normalized lowercase text")
    path = safe_child(private_root, "fixture-locks", f"{task_id}.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "ditto-proof-fixture/1" or value.get("task_id") != task_id:
        raise ValueError("fixture lock identity mismatch")
    if value.get("fixture_sha256") != sha256_bytes(canonical_bytes(value.get("files"))):
        raise ValueError("fixture lock hash mismatch")
    return value


def verify_fixture(path, expected_sha256=None):
    digest = tree_hash(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("fixture hash mismatch")
    return digest


def reset_fixture(sealed, destination, expected_sha256=None):
    """Create a fresh cell workspace and optionally verify its frozen hash."""
    sealed = Path(sealed).resolve()
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("workspace must not exist")
    if not sealed.is_dir():
        raise ValueError("sealed fixture does not exist")
    shutil.copytree(sealed, destination)
    verify_fixture(destination, expected_sha256)
    return destination
