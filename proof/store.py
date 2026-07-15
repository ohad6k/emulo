"""Append-only evidence lifecycle for attempts, corrections, and invalidations."""

import json
import re
from pathlib import Path

from proof.canonical import safe_child, sha256_file, write_once_json


RETRYABLE = {"provider_error", "host_error_before_output"}
CELL_ID_RE = re.compile(r"^cell-[0-9a-f]{1,64}$|^cell-[a-z0-9-]{1,64}$|^cell-a$")
IDENTITY_FIELDS = (
    "cell_id",
    "pair_id",
    "system_id",
    "fixture_sha256",
    "instruction_sha256",
    "profile_manifest_sha256",
    "tool_policy_sha256",
    "permission_policy_sha256",
    "budget",
)


def _require_cell_id(cell_id):
    if not isinstance(cell_id, str) or not CELL_ID_RE.fullmatch(cell_id):
        raise ValueError("cell ID must be normalized")


def validate_attempt_identity(value, frozen_cell):
    """Require an attempt to match every frozen pair identity field."""
    for field in IDENTITY_FIELDS:
        if value.get(field) != frozen_cell.get(field):
            raise ValueError(f"{field} mismatch")
    return value


class EvidenceStore:
    def __init__(self, run_root, frozen_cells):
        self.root = Path(run_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if not isinstance(frozen_cells, dict) or not frozen_cells:
            raise ValueError("evidence store requires frozen cells")
        self.frozen_cells = dict(frozen_cells)

    def _frozen_cell(self, cell_id):
        _require_cell_id(cell_id)
        try:
            return self.frozen_cells[cell_id]
        except KeyError as exc:
            raise ValueError("cell ID is not in the frozen manifest") from exc

    def _event_files(self, cell_id, kind):
        _require_cell_id(cell_id)
        if not isinstance(kind, str) or not re.fullmatch(r"[a-z][a-z-]{0,63}", kind):
            raise ValueError("event kind must be normalized")
        folder = safe_child(self.root, "cells", cell_id, kind)
        return sorted(folder.glob("*.json")) if folder.exists() else []

    def events(self, cell_id, kind):
        rows = []
        for path in self._event_files(cell_id, kind):
            rows.append(
                {
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "value": json.loads(path.read_text(encoding="utf-8")),
                }
            )
        return rows

    def _append(self, cell_id, kind, value):
        files = self._event_files(cell_id, kind)
        index = len(files) + 1
        path = safe_child(self.root, "cells", cell_id, kind, f"{index:04d}.json")
        digest = write_once_json(path, value)
        return {"path": str(path), "sha256": digest}

    def attempts(self, cell_id):
        return [event["value"] for event in self.events(cell_id, "attempts")]

    def record_attempt(self, cell_id, value):
        frozen_cell = self._frozen_cell(cell_id)
        if value.get("schema") != "ditto-proof-attempt/1":
            raise ValueError("unsupported attempt schema")
        if value.get("cell_id") != cell_id:
            raise ValueError("attempt cell ID mismatch")
        validate_attempt_identity(value, frozen_cell)
        attempts = self.attempts(cell_id)
        if len(attempts) >= 2:
            raise ValueError("cell already has the maximum two attempts")
        if len(attempts) == 1 and not self.events(cell_id, "retry-authorizations"):
            raise ValueError("second attempt requires a retry authorization")
        return self._append(cell_id, "attempts", value)

    def authorize_retry(self, cell_id, reason):
        self._frozen_cell(cell_id)
        attempts = self.attempts(cell_id)
        if len(attempts) != 1 or self.events(cell_id, "retry-authorizations"):
            raise ValueError("one retry requires exactly one prior attempt")
        prior = attempts[0]
        if prior.get("meaningful_output") or prior.get("exit_status") not in RETRYABLE:
            raise ValueError("model behavior is a result, not retryable")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("retry reason is required")
        return self._append(
            cell_id,
            "retry-authorizations",
            {
                "schema": "ditto-proof-retry-authorization/1",
                "cell_id": cell_id,
                "prior_attempt_sha256": self.events(cell_id, "attempts")[0]["sha256"],
                "reason": reason,
            },
        )

    def record_evaluation(self, cell_id, value):
        self._frozen_cell(cell_id)
        if value.get("schema") != "ditto-proof-evaluation/1":
            raise ValueError("unsupported evaluation schema")
        if value.get("cell_id") != cell_id:
            raise ValueError("evaluation cell ID mismatch")
        return self._append(cell_id, "evaluations", value)["sha256"]

    def record_review(self, cell_id, value):
        from proof.evaluate import validate_review
        from proof.schema import validate_review_record

        frozen = self._frozen_cell(cell_id)
        validate_review_record(value)
        pair_cells = [
            cell
            for cell in self.frozen_cells.values()
            if cell.get("pair_id") == frozen.get("pair_id")
        ]
        if len(pair_cells) != 2:
            raise ValueError("review pair is not frozen exactly once")
        if value["pair_id"] != frozen["pair_id"] or value["family"] != frozen.get(
            "family"
        ):
            raise ValueError("review identity does not match frozen pair")
        ordered = sorted(pair_cells, key=lambda item: item["order"])
        if value["left_review_id"] != ordered[0]["review_id"] or value[
            "right_review_id"
        ] != ordered[1]["review_id"]:
            raise ValueError("review IDs do not match frozen blind order")
        checked = validate_review(value, frozen["family"])
        if checked["invalidation_reason"] != value["invalidation_reason"]:
            raise ValueError("review invalidation reason does not match eligibility")
        return self._append(cell_id, "reviews", value)["sha256"]

    def supersede_evaluation(self, cell_id, prior_sha256, reason, value):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("supersession reason is required")
        prior_events = {
            event["sha256"]: event["value"]
            for event in self.events(cell_id, "evaluations")
        }
        if prior_sha256 not in prior_events:
            raise ValueError("supersession target must be a prior evaluation")
        prior = prior_events[prior_sha256]
        corrected = dict(
            value,
            supersedes_sha256=prior_sha256,
            supersession_reason=reason,
        )
        return self.record_evaluation(cell_id, corrected)

    def record_invalidation(self, cell_id, reason, scope):
        self._frozen_cell(cell_id)
        if scope not in ("cell", "pair", "review"):
            raise ValueError("invalidation scope must be cell, pair, or review")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("invalidation reason is required")
        return self._append(
            cell_id,
            "invalidations",
            {
                "schema": "ditto-proof-invalidation/1",
                "cell_id": cell_id,
                "scope": scope,
                "reason": reason,
            },
        )["sha256"]

    def load(self, digest):
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("event digest must be lowercase SHA-256")
        for path in self.root.rglob("*.json"):
            if sha256_file(path) == digest:
                return json.loads(path.read_text(encoding="utf-8"))
        raise FileNotFoundError("event digest was not found")
