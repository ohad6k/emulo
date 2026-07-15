"""Deterministic, privacy-gated publication for Ditto Proof v1."""

import html
from collections import Counter
from pathlib import Path

from proof import BENCHMARK_NAME
from proof.canonical import canonical_bytes, sha256_bytes, write_once_json
from proof.evaluate import reveal_verdict, validate_review, wilson_interval
from proof.privacy import sanitize_text
from proof.schema import (
    validate_manifest,
    validate_publication_record,
    validate_review_record,
)
from proof.store import validate_attempt_identity


STANDARD_LIMITATIONS = (
    "complete-system comparison of the systems exactly as configured",
    "clean-host cold start with host persistent context absent",
    "small-n, directional only",
)
PROHIBITED_PUBLIC_CLAIMS = (
    "p-value",
    "p value",
    "statistically significant",
    "significance",
    "model ranking",
    "1000x",
    "star forecast",
    "traffic forecast",
)


def aggregate_preferences(verdicts):
    """Aggregate independent pair verdicts without counting ties as losses."""
    verdicts = list(verdicts)
    unexpected = sorted(set(verdicts) - {"ditto", "cold", "tie"})
    if unexpected:
        raise ValueError("unexpected preference verdict: " + ", ".join(unexpected))
    counts = {
        "ditto_wins": verdicts.count("ditto"),
        "cold_wins": verdicts.count("cold"),
        "ties": verdicts.count("tie"),
    }
    counts["binary_denominator"] = counts["ditto_wins"] + counts["cold_wins"]
    counts["raw_denominator"] = len(verdicts)
    return {
        "counts": counts,
        "ditto_wilson_95": wilson_interval(
            counts["ditto_wins"], counts["binary_denominator"]
        ),
    }


def _frozen_cells(manifest):
    return {
        cell["cell_id"]: cell
        for pair in manifest["pairs"]
        for cell in pair["cells"]
    }


def _eligible_records(manifest, records):
    eligible = [
        record for record in records if record.get("publication_status") == "eligible"
    ]
    cell_ids = [record.get("cell_id") for record in eligible]
    frozen = _frozen_cells(manifest)
    if len(eligible) != 48:
        raise ValueError("Ditto Proof v1 requires 48 valid cells")
    if len(set(cell_ids)) != 48 or set(cell_ids) != set(frozen):
        raise ValueError("eligible records must match the frozen 48-cell matrix")
    for record in eligible:
        cell = frozen[record["cell_id"]]
        if any(
            record.get(field) != cell[field]
            for field in ("pair_id", "family", "condition")
        ):
            raise ValueError("eligible record does not match frozen cell identity")
        if record.get("review_status") not in {"valid", "invalid"}:
            raise ValueError("review status must be valid or invalid")
    for pair in manifest["pairs"]:
        pair_records = [
            record for record in eligible if record["pair_id"] == pair["pair_id"]
        ]
        contributions = [
            record
            for record in pair_records
            if record.get("preference") is not None
            or record.get("review_status") == "invalid"
        ]
        if len(contributions) != 1:
            raise ValueError("each frozen pair requires one review contribution")
        contribution = contributions[0]
        if contribution["review_status"] == "invalid":
            if not contribution.get("invalidation_reason"):
                raise ValueError("invalid review requires an invalidation reason")
        elif contribution.get("preference") not in {"ditto", "cold", "tie"}:
            raise ValueError("valid review requires a frozen preference")
    return sorted(eligible, key=lambda item: item["cell_id"])


def publication_approval_digest(manifest, records):
    """Return the approval token for the manifest and complete evidence set."""
    validate_manifest(manifest)
    records = list(records)
    _eligible_records(manifest, records)
    ordered = sorted(records, key=canonical_bytes)
    return sha256_bytes(canonical_bytes({"manifest": manifest, "records": ordered}))


def _preference_summary(records):
    accepted = []
    invalidations = []
    seen_pairs = set()
    for record in records:
        status = record.get("review_status")
        reason = record.get("invalidation_reason", "")
        if status == "invalid":
            invalidations.append(
                {
                    "pair_id": record.get("pair_id"),
                    "cell_id": record["cell_id"],
                    "family": record.get("family"),
                    "reason": reason or "review invalidated",
                    "record_sha256": sha256_bytes(canonical_bytes(record)),
                }
            )
            continue
        verdict = record.get("preference")
        if verdict is None:
            continue
        pair_id = record.get("pair_id")
        if pair_id in seen_pairs:
            raise ValueError("each pair may contribute at most one preference")
        seen_pairs.add(pair_id)
        accepted.append((record.get("family"), verdict))
    by_family = {
        family: aggregate_preferences(
            [verdict for candidate, verdict in accepted if candidate == family]
        )
        for family in ("work", "design", "write")
    }
    return (
        {
            "overall": aggregate_preferences([verdict for _, verdict in accepted]),
            "by_family": by_family,
        },
        sorted(invalidations, key=lambda item: (item["pair_id"] or "", item["cell_id"])),
    )


def _failure_summary(records):
    result = {}
    for condition in ("cold", "ditto"):
        failures = [
            failure
            for record in records
            if record.get("condition") == condition
            for failure in record.get("hard_failures", [])
        ]
        result[condition] = {
            "total": len(failures),
            "by_reason": dict(sorted(Counter(failures).items())),
        }
    return result


def _public_cell(record):
    """Project one private evidence record onto an intentionally narrow surface."""
    return {
        "cell_id": record["cell_id"],
        "pair_id": record.get("pair_id"),
        "condition": record.get("condition"),
        "family": record.get("family"),
        "objective_result_sha256": record.get("objective_result_sha256"),
        "attempt_sha256": record.get("attempt_sha256"),
        "evaluation_sha256": record.get("evaluation_sha256"),
        "review_sha256": record.get("review_sha256"),
        "artifact_hashes": list(record.get("artifact_hashes", [])),
        "hard_failures": list(record.get("hard_failures", [])),
        "redaction_state": record.get("redaction_state"),
        "retry_history": list(record.get("retry_history", [])),
        "record_sha256": sha256_bytes(canonical_bytes(record)),
    }


def _public_exclusion(record):
    return {
        "cell_id": record.get("cell_id"),
        "pair_id": record.get("pair_id"),
        "publication_status": record.get("publication_status", "unknown"),
        "invalidation_reason": record.get("invalidation_reason", ""),
        "retry_history": list(record.get("retry_history", [])),
    }


def _reject_prohibited_claims(publication):
    text = canonical_bytes(publication).decode("ascii").casefold()
    found = [phrase for phrase in PROHIBITED_PUBLIC_CLAIMS if phrase in text]
    if found:
        raise ValueError("prohibited public claim: " + ", ".join(found))


def _resolve_event(store, cell_id, kind, digest):
    if not isinstance(digest, str):
        raise ValueError(f"{kind} evidence hash is required")
    events = store.events(cell_id, kind)
    matches = [event for event in events if event["sha256"] == digest]
    if len(matches) != 1:
        raise ValueError(f"{kind} evidence hash is not in the append-only store")
    return matches[0]["value"]


def _verify_hash_bound_evidence(manifest, records, store):
    frozen = _frozen_cells(manifest)
    pairs = {pair["pair_id"]: pair for pair in manifest["pairs"]}
    for record in records:
        cell = frozen[record["cell_id"]]
        attempt = _resolve_event(
            store, record["cell_id"], "attempts", record.get("attempt_sha256")
        )
        validate_attempt_identity(attempt, cell)
        attempt_events = store.events(record["cell_id"], "attempts")
        if attempt_events[-1]["sha256"] != record["attempt_sha256"]:
            raise ValueError("publication must reference the final retained attempt")
        stored_retries = [
            event["value"]
            for event in store.events(record["cell_id"], "retry-authorizations")
        ]
        if record.get("retry_history") != stored_retries:
            raise ValueError("published retry history does not match evidence store")

        evaluation = _resolve_event(
            store,
            record["cell_id"],
            "evaluations",
            record.get("evaluation_sha256"),
        )
        if evaluation.get("schema") != "ditto-proof-evaluation/1" or evaluation.get(
            "cell_id"
        ) != record["cell_id"]:
            raise ValueError("evaluation evidence identity mismatch")
        if store.events(record["cell_id"], "evaluations")[-1]["sha256"] != record[
            "evaluation_sha256"
        ]:
            raise ValueError("publication must reference the final evaluation")
        if record.get("objective_result_sha256") != record["evaluation_sha256"]:
            raise ValueError("objective result must reference the stored evaluation")
        if evaluation.get("hard_failures") != record.get("hard_failures"):
            raise ValueError("published hard failures do not match evaluation evidence")
        if evaluation.get("artifact_hashes") != record.get("artifact_hashes"):
            raise ValueError("published artifacts do not match evaluation evidence")
        if evaluation.get("redaction_state") != "passed" or record.get(
            "redaction_state"
        ) != "passed":
            raise ValueError("publication requires a passed redaction evaluation")
        for digest in record.get("artifact_hashes", []):
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError("artifact hashes must be SHA-256 values")

        contributes = record.get("preference") is not None or record.get(
            "review_status"
        ) == "invalid"
        review_sha256 = record.get("review_sha256")
        if not contributes:
            if review_sha256 is not None:
                raise ValueError("only one cell may reference the pair review")
            continue
        review = _resolve_event(
            store, record["cell_id"], "reviews", review_sha256
        )
        if store.events(record["cell_id"], "reviews")[-1]["sha256"] != review_sha256:
            raise ValueError("publication must reference the final review record")
        validate_review_record(review)
        pair = pairs[cell["pair_id"]]
        if review["pair_id"] != pair["pair_id"] or review["family"] != pair["family"]:
            raise ValueError("review evidence does not match the frozen pair")
        ordered = sorted(pair["cells"], key=lambda item: item["order"])
        if review["left_review_id"] != ordered[0]["review_id"] or review[
            "right_review_id"
        ] != ordered[1]["review_id"]:
            raise ValueError("review evidence does not match the blind packet")
        checked = validate_review(review, pair["family"])
        if checked["status"] != record["review_status"]:
            raise ValueError("published review status does not match review evidence")
        if checked["status"] == "invalid":
            if record.get("preference") is not None or record.get(
                "invalidation_reason"
            ) != checked["invalidation_reason"]:
                raise ValueError("invalid review must publish no preference")
        else:
            if record.get("preference") != reveal_verdict(checked, pair):
                raise ValueError("published preference does not match blind review")


def build_publication(manifest, records, ship_approval, evidence_store=None):
    """Recalculate all public outcomes and require approval of the exact evidence."""
    validate_manifest(manifest)
    if evidence_store is None:
        evidence_store = getattr(records, "evidence_store", None)
    if evidence_store is None:
        raise ValueError("publication requires an append-only evidence store")
    records = list(records)
    eligible = _eligible_records(manifest, records)
    _verify_hash_bound_evidence(manifest, eligible, evidence_store)
    evidence_digest = publication_approval_digest(manifest, records)
    if ship_approval != evidence_digest:
        raise PermissionError("ship approval must match the exact evidence digest")

    preferences, invalidations = _preference_summary(eligible)
    exclusions = sorted(
        [
            _public_exclusion(record)
            for record in records
            if record.get("publication_status") != "eligible"
        ],
        key=lambda item: (
            item["cell_id"] or "",
            item["publication_status"],
        ),
    )
    publication = {
        "schema": "ditto-proof-publication/1",
        "benchmark": BENCHMARK_NAME,
        "label": "small-n, directional only",
        "manifest_sha256": sha256_bytes(canonical_bytes(manifest)),
        "evidence_digest": evidence_digest,
        "valid_cells": [_public_cell(record) for record in eligible],
        "cell_count": 48,
        "preferences": preferences,
        "hard_failures": _failure_summary(eligible),
        "invalidations": invalidations,
        "exclusions": exclusions,
        "limitations": list(dict.fromkeys([*STANDARD_LIMITATIONS, *manifest["limitations"]])),
        "record_hashes": [
            {
                "cell_id": record["cell_id"],
                "sha256": sha256_bytes(canonical_bytes(record)),
            }
            for record in eligible
        ],
        "generated_at": manifest["created_at"],
    }
    validate_publication_record(publication)
    _reject_prohibited_claims(publication)
    return publication


def render_index(publication, destination, canaries, private_roots=()):
    """Write a byte-stable two-file static package after scanning both payloads."""
    validate_publication_record(publication)
    title = "Ditto Proof v1"
    counts = publication["preferences"]["overall"]["counts"]
    body = (
        "<!doctype html>\n"
        "<html lang=\"en\"><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        f"<h1>{html.escape(title)}</h1>"
        "<p>Complete-system comparison from a clean-host cold start. "
        "Small-n, directional only.</p>"
        f"<p>Ditto wins: {counts['ditto_wins']}; cold wins: "
        f"{counts['cold_wins']}; ties: {counts['ties']}.</p>"
        "</html>\n"
    )
    results = canonical_bytes(publication) + b"\n"
    sanitize_text(body, canaries, private_roots)
    sanitize_text(results.decode("utf-8"), canaries, private_roots)

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "index.html").open("xb") as handle:
        handle.write(body.encode("utf-8"))
    results_hash = write_once_json(destination / "results.json", publication)
    return {
        "index_sha256": sha256_bytes(body.encode("utf-8")),
        "results_sha256": results_hash,
    }
