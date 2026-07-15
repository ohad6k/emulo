"""Deterministic, privacy-gated publication for Ditto Proof v1."""

import html
from collections import Counter
from pathlib import Path

from proof import BENCHMARK_NAME
from proof.canonical import canonical_bytes, sha256_bytes, write_once_json
from proof.evaluate import wilson_interval
from proof.privacy import sanitize_text
from proof.schema import validate_manifest, validate_publication_record


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


def _frozen_cell_ids(manifest):
    return {
        cell["cell_id"]
        for pair in manifest["pairs"]
        for cell in pair["cells"]
    }


def _eligible_records(manifest, records):
    eligible = [
        record for record in records if record.get("publication_status") == "eligible"
    ]
    cell_ids = [record.get("cell_id") for record in eligible]
    if len(eligible) != 48:
        raise ValueError("Ditto Proof v1 requires 48 valid cells")
    if len(set(cell_ids)) != 48 or set(cell_ids) != _frozen_cell_ids(manifest):
        raise ValueError("eligible records must match the frozen 48-cell matrix")
    return sorted(eligible, key=lambda item: item["cell_id"])


def publication_approval_digest(manifest, records):
    """Return the approval token for exactly this manifest and eligible evidence."""
    validate_manifest(manifest)
    eligible = _eligible_records(manifest, records)
    return sha256_bytes(canonical_bytes({"manifest": manifest, "records": eligible}))


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
        "artifact_hashes": list(record.get("artifact_hashes", [])),
        "hard_failures": list(record.get("hard_failures", [])),
        "retry_history": list(record.get("retry_history", [])),
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


def build_publication(manifest, records, ship_approval):
    """Recalculate all public outcomes and require approval of the exact evidence."""
    validate_manifest(manifest)
    records = list(records)
    eligible = _eligible_records(manifest, records)
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
