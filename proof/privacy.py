"""Fail-closed privacy scanning for every prospective public artifact."""

import os
import re
import stat
from pathlib import Path

from proof.canonical import sha256_file


SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|token|password)\s*[:=]\s*\S+"),
)
PATH_PATTERNS = (
    re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s]+(?:\\[^\s]*)?"),
    re.compile(r"/home/[^/\s]+(?:/[^\s]*)?"),
    re.compile(r"/Users/[^/\s]+(?:/[^\s]*)?"),
)
ALLOWED_EXTENSIONS = {
    ".json", ".html", ".md", ".txt", ".css", ".js", ".vtt", ".srt",
    ".png", ".jpg", ".jpeg", ".webp", ".mp4",
}
TEXT_EXTENSIONS = {".json", ".html", ".md", ".txt", ".css", ".js", ".vtt", ".srt"}
RAW_PRIVATE_NAMES = {"you.md", "you-writer.md", "you-designer.md", "profile.json", "receipts.json"}


def scan_public_text(text, canaries, private_roots=()):
    if not isinstance(text, str):
        raise TypeError("public text scan requires text")
    findings = []
    for name, value in canaries.items():
        if value and value in text:
            findings.append(name)
    for root in private_roots:
        if root and str(root) in text:
            findings.append("private-root")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        findings.append("secret-pattern")
    path_matches = [pattern.pattern for pattern in PATH_PATTERNS if pattern.search(text)]
    if path_matches:
        if any("/home/" in pattern for pattern in path_matches):
            findings.append("home-path")
        else:
            findings.append("local-path")
    return {"passed": not findings, "findings": sorted(set(findings))}


def sanitize_text(text, canaries, private_roots=()):
    result = scan_public_text(text, canaries, private_roots)
    if not result["passed"]:
        raise ValueError("privacy scan failed: " + ", ".join(result["findings"]))
    return text.encode("utf-8").decode("utf-8")


def _is_link_or_reparse(path):
    path = Path(path)
    metadata = path.lstat()
    attributes = getattr(metadata, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & flag)


def _validate_public_name(relative):
    parts = Path(relative).parts
    if any(part.startswith(".") for part in parts):
        raise ValueError("hidden file is not allowed in a public package")
    name = parts[-1].casefold()
    if name in RAW_PRIVATE_NAMES:
        raise ValueError("raw profile is not allowed in a public package")
    if "transcript" in name:
        raise ValueError("raw transcript is not allowed in a public package")
    if "receipt" in name:
        raise ValueError("raw receipt is not allowed in a public package")
    suffix = Path(name).suffix
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("unrecognized extension in public package")


def scan_public_tree(root, canaries, manual_review_approved, private_roots=()):
    """Scan filenames and bodies after an explicit manual privacy approval."""
    if manual_review_approved is not True:
        raise ValueError("manual privacy review approval is required")
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("public package root must exist")
    records = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            if _is_link_or_reparse(path):
                raise ValueError("symlink or reparse point in public package")
        for name in files:
            path = current_path / name
            if _is_link_or_reparse(path):
                raise ValueError("symlink or reparse point in public package")
            relative = path.relative_to(root).as_posix()
            _validate_public_name(relative)
            filename_scan = scan_public_text(relative, canaries, private_roots)
            if not filename_scan["passed"]:
                raise ValueError(
                    "privacy scan failed in filename: "
                    + ", ".join(filename_scan["findings"])
                )
            if path.suffix.casefold() in TEXT_EXTENSIONS:
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise ValueError("public text artifact is not valid UTF-8") from exc
                body_scan = scan_public_text(text, canaries, private_roots)
                if not body_scan["passed"]:
                    raise ValueError(
                        "privacy scan failed in "
                        + relative
                        + ": "
                        + ", ".join(body_scan["findings"])
                    )
            else:
                payload = path.read_bytes()
                leaked = [
                    name
                    for name, value in canaries.items()
                    if value and value.encode("utf-8") in payload
                ]
                if leaked:
                    raise ValueError(
                        "privacy scan failed in binary artifact: " + ", ".join(leaked)
                    )
                decoded = [payload.decode("utf-8", errors="ignore")]
                if len(payload) % 2 == 0:
                    decoded.append(payload.decode("utf-16le", errors="ignore"))
                findings = sorted(
                    {
                        finding
                        for candidate in decoded
                        for finding in scan_public_text(
                            candidate, canaries, private_roots
                        )["findings"]
                    }
                )
                if findings:
                    raise ValueError(
                        "privacy scan failed in binary artifact: "
                        + ", ".join(findings)
                    )
            records.append({"path": relative, "sha256": sha256_file(path)})
    return {"passed": True, "files": sorted(records, key=lambda item: item["path"])}
