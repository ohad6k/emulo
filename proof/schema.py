"""Strict structural contracts for Ditto Proof v1 records."""

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
