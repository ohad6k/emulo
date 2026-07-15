"""Strict structural contracts for Ditto Proof v1 records."""

from datetime import datetime

from proof import BENCHMARK_NAME, BENCHMARK_SCHEMA, DITTO_COMMIT, DITTO_REF

UNCERTAINTY_POLICY = (
    "small-n, directional only; Wilson 95%; no significance claims"
)

MANIFEST_KEYS = {
    "schema",
    "benchmark",
    "benchmark_version",
    "ditto_ref",
    "ditto_commit",
    "profile_manifest_sha256",
    "private_rubric_sha256",
    "public_rubric_sha256",
    "uncertainty_policy",
    "host_persistent_context",
    "systems",
    "pairs",
    "limitations",
    "created_at",
}

CELL_RECORD_KEYS = {
    "schema",
    "cell_id",
    "pair_id",
    "attempt",
    "system_id",
    "host",
    "task_id",
    "family",
    "variant",
    "trial",
    "condition",
    "order",
    "review_id",
    "fixture_sha256",
    "instruction_sha256",
    "profile_manifest_sha256",
    "host_persistent_context",
    "tool_policy_sha256",
    "permission_policy_sha256",
    "budget",
    "workspace_sha256",
    "home_audit_sha256",
    "installed_context_sha256",
    "exit_status",
    "exit_code",
    "meaningful_output",
    "stdout_sha256",
    "stderr_sha256",
    "artifact_hashes",
    "objective_result_sha256",
    "hard_failures",
    "redaction_state",
    "publication_status",
}

REVIEW_KEYS = {
    "schema",
    "review_id",
    "pair_id",
    "family",
    "reviewer_role",
    "consent_reference",
    "eligibility_attestation",
    "unfamiliar_with_operator_voice",
    "blinding_confirmed",
    "verdict",
    "left_review_id",
    "right_review_id",
    "invalidation_reason",
    "created_at",
}

PUBLICATION_KEYS = {
    "schema",
    "benchmark",
    "label",
    "manifest_sha256",
    "evidence_digest",
    "valid_cells",
    "cell_count",
    "preferences",
    "hard_failures",
    "invalidations",
    "exclusions",
    "limitations",
    "record_hashes",
    "generated_at",
}

SYSTEM_KEYS = {
    "system_id", "host", "menu_label", "model_id", "host_version",
    "run_argv", "ditto_install_argv", "selection_screenshot_sha256",
    "tool_policy_sha256", "permission_policy_sha256", "quota_snapshot",
    "expected_cost",
}
PAIR_KEYS = {
    "pair_id", "system_id", "host", "task_id", "family", "variant", "trial",
    "fixture_sha256", "instruction_sha256", "tool_policy_sha256",
    "permission_policy_sha256", "budget", "cells",
}
MANIFEST_CELL_KEYS = {
    "pair_id", "system_id", "host", "task_id", "family", "variant", "trial",
    "fixture_sha256", "instruction_sha256", "tool_policy_sha256",
    "permission_policy_sha256", "budget", "condition", "order", "cell_id",
    "review_id", "profile_manifest_sha256", "host_persistent_context",
}


def require_exact_keys(value, required, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{label} unexpected keys: {', '.join(extra)}")


def require_sha256(value, label):
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be lowercase hex")


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")


def _require_argv(value, label):
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{label} must be a nonempty argv list")


def _validate_budget(value, label):
    require_exact_keys(value, {"time_seconds", "max_turns"}, label)
    for key in ("time_seconds", "max_turns"):
        if not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] <= 0:
            raise ValueError(f"{label} {key} must be a positive integer")


def _validate_timestamp(value, label):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{label} must be an RFC 3339 UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{label} must be an RFC 3339 UTC timestamp") from exc


def validate_manifest(value):
    require_exact_keys(value, MANIFEST_KEYS, "manifest")
    if value["schema"] != BENCHMARK_SCHEMA:
        raise ValueError("unsupported schema")
    if value["benchmark"] != BENCHMARK_NAME:
        raise ValueError("wrong benchmark name")
    if value["benchmark_version"] != "1.0.0":
        raise ValueError("unsupported benchmark version")
    if value["ditto_ref"] != DITTO_REF or value["ditto_commit"] != DITTO_COMMIT:
        raise ValueError("mixed Ditto version")
    for key in (
        "profile_manifest_sha256",
        "private_rubric_sha256",
        "public_rubric_sha256",
    ):
        require_sha256(value[key], key)
    if value["uncertainty_policy"] != UNCERTAINTY_POLICY:
        raise ValueError("uncertainty policy changed")
    if value["host_persistent_context"] != "absent":
        raise ValueError("host persistent context must be absent")
    if not isinstance(value["systems"], list) or len(value["systems"]) != 2:
        raise ValueError("manifest requires exactly 2 systems")
    if not isinstance(value["pairs"], list) or len(value["pairs"]) != 24:
        raise ValueError("manifest requires exactly 24 pairs")
    if not isinstance(value["limitations"], list) or not value["limitations"]:
        raise ValueError("manifest limitations must be a nonempty list")
    if not all(isinstance(item, str) and item for item in value["limitations"]):
        raise ValueError("manifest limitations must contain nonempty text")
    _validate_timestamp(value["created_at"], "created_at")

    systems_by_id = {}
    for system in value["systems"]:
        require_exact_keys(system, SYSTEM_KEYS, "system")
        _require_text(system["system_id"], "system_id")
        if system["system_id"] in systems_by_id:
            raise ValueError("system IDs must be unique")
        if system["host"] not in {"codex", "claude"}:
            raise ValueError("system host must be codex or claude")
        for key in ("menu_label", "host_version", "quota_snapshot", "expected_cost"):
            _require_text(system[key], key)
        if system["model_id"] is not None:
            _require_text(system["model_id"], "model_id")
        _require_argv(system["run_argv"], "run_argv")
        _require_argv(system["ditto_install_argv"], "ditto_install_argv")
        for key in (
            "selection_screenshot_sha256", "tool_policy_sha256",
            "permission_policy_sha256",
        ):
            require_sha256(system[key], key)
        systems_by_id[system["system_id"]] = system
    if {item["host"] for item in value["systems"]} != {"codex", "claude"}:
        raise ValueError("manifest requires one codex and one claude system")

    expected_matrix = {
        (system_id, family, variant, trial)
        for system_id in systems_by_id
        for family in ("work", "design", "write")
        for variant in ("primary", "held-out")
        for trial in (1, 2)
    }
    observed_matrix = set()
    pair_ids = set()
    cell_ids = set()
    review_ids = set()
    for pair in value["pairs"]:
        require_exact_keys(pair, PAIR_KEYS, "pair")
        _require_text(pair["pair_id"], "pair_id")
        if pair["pair_id"] in pair_ids:
            raise ValueError("pair IDs must be unique")
        pair_ids.add(pair["pair_id"])
        system = systems_by_id.get(pair["system_id"])
        if system is None or pair["host"] != system["host"]:
            raise ValueError("pair system identity is not frozen")
        if pair["family"] not in {"work", "design", "write"}:
            raise ValueError("pair family is invalid")
        if pair["variant"] not in {"primary", "held-out"}:
            raise ValueError("pair variant is invalid")
        if pair["trial"] not in {1, 2}:
            raise ValueError("pair trial is invalid")
        if pair["task_id"] != f"{pair['family']}-{pair['variant']}":
            raise ValueError("pair task ID does not match family and variant")
        for key in (
            "fixture_sha256", "instruction_sha256", "tool_policy_sha256",
            "permission_policy_sha256",
        ):
            require_sha256(pair[key], key)
        if pair["tool_policy_sha256"] != system["tool_policy_sha256"] or pair[
            "permission_policy_sha256"
        ] != system["permission_policy_sha256"]:
            raise ValueError("pair policies do not match frozen system")
        _validate_budget(pair["budget"], "pair budget")
        identity = (
            pair["system_id"], pair["family"], pair["variant"], pair["trial"]
        )
        if identity in observed_matrix:
            raise ValueError("matrix contains a duplicate pair identity")
        observed_matrix.add(identity)
        if not isinstance(pair["cells"], list) or len(pair["cells"]) != 2:
            raise ValueError("each pair requires exactly two cells")
        if {cell.get("condition") for cell in pair["cells"]} != {"cold", "ditto"}:
            raise ValueError("each pair requires cold and ditto cells")
        if {cell.get("order") for cell in pair["cells"]} != {1, 2}:
            raise ValueError("each pair requires unique blind order")
        for cell in pair["cells"]:
            require_exact_keys(cell, MANIFEST_CELL_KEYS, "manifest cell")
            for field in (
                "pair_id", "system_id", "host", "task_id", "family", "variant",
                "trial", "fixture_sha256", "instruction_sha256",
                "tool_policy_sha256", "permission_policy_sha256", "budget",
            ):
                if cell[field] != pair[field]:
                    raise ValueError(f"manifest cell {field} does not match pair")
            if cell["host_persistent_context"] != "absent":
                raise ValueError("manifest cell persistent context must be absent")
            for key in ("cell_id", "review_id"):
                _require_text(cell[key], key)
            if cell["cell_id"] in cell_ids or cell["review_id"] in review_ids:
                raise ValueError("cell and review IDs must be unique")
            cell_ids.add(cell["cell_id"])
            review_ids.add(cell["review_id"])
            expected_profile = (
                value["profile_manifest_sha256"]
                if cell["condition"] == "ditto"
                else None
            )
            if cell["profile_manifest_sha256"] != expected_profile:
                raise ValueError("cell profile identity does not match condition")
    if observed_matrix != expected_matrix or len(cell_ids) != 48:
        raise ValueError("manifest does not contain the frozen 24-pair/48-cell matrix")
    return value


def validate_cell(value):
    if value.get("schema") != "ditto-proof-cell/1":
        raise ValueError("unsupported cell schema")
    if value.get("host_persistent_context") != "absent":
        raise ValueError("host persistent context must be absent")
    require_exact_keys(value, CELL_RECORD_KEYS, "cell record")
    return value


def validate_review_record(value):
    require_exact_keys(value, REVIEW_KEYS, "review record")
    if value["schema"] != "ditto-proof-review/1":
        raise ValueError("unsupported review schema")
    return value


def validate_publication_record(value):
    if value.get("headline_metric") == "profile_rubric_adherence":
        raise ValueError("profile rubric adherence is mechanism only")
    require_exact_keys(value, PUBLICATION_KEYS, "publication record")
    if value["schema"] != "ditto-proof-publication/1":
        raise ValueError("unsupported publication schema")
    return value
