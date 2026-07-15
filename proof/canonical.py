"""Canonical serialization and write-once evidence primitives."""

import hashlib
import json
import os
from pathlib import Path


def canonical_bytes(value):
    """Return deterministic ASCII JSON bytes without insignificant whitespace."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value):
    """Hash an immutable byte payload."""
    if not isinstance(value, bytes):
        raise TypeError("sha256_bytes requires bytes")
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    """Hash a file without loading it all into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_child(root, *parts):
    """Resolve a path and require it to remain below the resolved root."""
    resolved_root = Path(root).resolve()
    child = resolved_root.joinpath(*parts).resolve()
    try:
        child.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("path is outside root") from exc
    return child


def write_once_json(path, value):
    """Create one canonical JSON record and refuse every overwrite."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value) + b"\n"
    with destination.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return sha256_bytes(payload)
