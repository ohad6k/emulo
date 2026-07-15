"""Prepare isolated homes and gate every provider execution behind exact approval."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from proof.canonical import canonical_bytes, safe_child, sha256_bytes, sha256_file
from proof.fixtures import reset_fixture, tree_hash


FORBIDDEN_CONTEXT = {
    "agents.md",
    "claude.md",
    ".claude",
    ".codex",
    "memory",
    "rules",
}


@dataclass(frozen=True)
class PreparedCell:
    workspace: Path
    home: Path
    fixture_sha256: str
    environment: dict
    home_audit_sha256: str


def _require_external_run_root(run_root, repository_root=None):
    supplied = Path(run_root)
    if not supplied.is_absolute():
        raise ValueError("private run root must be absolute")
    resolved = supplied.resolve()
    repository = Path(
        repository_root or Path(__file__).resolve().parents[1]
    ).resolve()
    try:
        resolved.relative_to(repository)
    except ValueError:
        return resolved
    raise ValueError("private run root must be outside repository")


def audit_clean_home(home):
    """Prove that no pre-existing host personalization is present."""
    home = Path(home)
    if not home.is_dir():
        raise ValueError("cell home must exist")
    present = sorted(
        path.relative_to(home).as_posix()
        for path in home.rglob("*")
        if path.name.casefold() in FORBIDDEN_CONTEXT
    )
    if present:
        raise ValueError("host persistent context is present: " + ", ".join(present))
    rows = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))
    return sha256_bytes(canonical_bytes(rows))


def prepare_cell(manifest, cell, run_root):
    """Create a new home and deterministic workspace for exactly one frozen cell."""
    del manifest  # The cell contains the frozen execution identity needed for preparation.
    root = _require_external_run_root(run_root)
    cell_root = safe_child(root, "cells", cell["cell_id"])
    workspace = safe_child(cell_root, "workspace")
    home = safe_child(cell_root, "home")
    if cell_root.exists():
        raise FileExistsError("cell root must not be reused")
    cell_root.mkdir(parents=True)
    home.mkdir()
    home_audit_sha256 = audit_clean_home(home)
    sealed = safe_child(root, "sealed-fixtures", cell["task_id"])
    reset_fixture(sealed, workspace, cell["fixture_sha256"])
    instruction = safe_child(workspace, "brief.md")
    if not instruction.is_file() or sha256_file(instruction) != cell.get(
        "instruction_sha256"
    ):
        raise ValueError("frozen instruction hash mismatch")
    environment = {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "CLAUDE_CONFIG_DIR": str(home / ".claude"),
        "DITTO_HOME": str(home / ".ditto"),
        "XDG_CONFIG_HOME": str(home / ".config"),
    }
    return PreparedCell(
        workspace=workspace,
        home=home,
        fixture_sha256=tree_hash(workspace),
        environment=environment,
        home_audit_sha256=home_audit_sha256,
    )


def _run_argv(argv, prepared, timeout):
    environment = os.environ.copy()
    environment.update(prepared.environment)
    return subprocess.run(
        argv,
        cwd=prepared.workspace,
        env=environment,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=timeout,
    )


def execute_cell(manifest, cell, run_root, execute, approval):
    """Run one cell only after an exact manifest-digest approval."""
    manifest_hash = sha256_bytes(canonical_bytes(manifest))
    if not execute:
        raise PermissionError("provider execution requires explicit approval")
    if approval != manifest_hash:
        raise PermissionError("approval must equal the exact manifest hash")
    systems = [
        item for item in manifest["systems"] if item["system_id"] == cell["system_id"]
    ]
    if len(systems) != 1:
        raise ValueError("cell system identity is not frozen exactly once")
    system = systems[0]
    if system["host"] != cell["host"]:
        raise ValueError("cell host does not match frozen system")
    prepared = prepare_cell(manifest, cell, run_root)
    timeout = cell["budget"]["time_seconds"]

    installed_context_sha256 = None
    if cell["condition"] == "ditto":
        installation = _run_argv(system["ditto_install_argv"], prepared, timeout)
        if installation.returncode != 0:
            raise RuntimeError("frozen Ditto installation failed before provider execution")
        installed_context_sha256 = tree_hash(prepared.home)
        if installed_context_sha256 != cell.get("profile_manifest_sha256"):
            raise ValueError(
                "installed context does not match the frozen profile manifest"
            )
    elif cell["condition"] != "cold":
        raise ValueError("cell condition must be cold or ditto")

    completed = _run_argv(system["run_argv"], prepared, timeout)
    return prepared, completed, installed_context_sha256
