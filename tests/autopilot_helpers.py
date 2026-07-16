from emulo_autopilot import contracts


def candidate_fixture(
    evidence=3,
    strata=2,
    contradiction_count=0,
    risk_categories=None,
    kind="directive",
    statement=None,
):
    receipts = []
    for index in range(evidence):
        month = 6 + (index % max(strata, 1))
        receipts.append(
            {
                "receipt_id": "rcpt_" + format(index + 1, "020x"),
                "session_id": format(index + 1, "016x"),
                "observed_at": "2026-{0:02d}-16T10:00:00Z".format(month),
                "time_stratum": "2026-{0:02d}".format(month),
            }
        )
    candidate = {
        "schema_version": contracts.CANDIDATE_SCHEMA,
        "candidate_id": "",
        "kind": kind,
        "domain": "work",
        "statement": statement
        or "Verify the live URL before claiming deployment is complete.",
        "scope": ["shipping"],
        "evidence": receipts,
        "contradiction_count": contradiction_count,
        "risk_categories": sorted(risk_categories or []),
        "source_packet_hash": "a" * 64,
        "prompt_contract_version": "emulo.autopilot-candidate-prompt/v1",
        "created_at": "2026-07-16T10:01:00Z",
    }
    candidate["candidate_id"] = contracts.candidate_identity(candidate)
    return candidate


def decision_fixture(
    candidate_id,
    decision="approve",
    reason="founder-review",
    policy_class="review",
    decided_at="2026-07-16T10:02:00Z",
):
    value = {
        "schema_version": contracts.DECISION_SCHEMA,
        "decision_id": "",
        "candidate_id": candidate_id,
        "decision": decision,
        "reason": reason,
        "policy_class": policy_class,
        "decided_at": decided_at,
    }
    value["decision_id"] = contracts.decision_identity(value)
    return value


def checkpoint_fixture():
    return {
        "schema_version": contracts.CHECKPOINT_SCHEMA,
        "path_hash": "d" * 64,
        "source": "codex",
        "identity": {"size": 1234, "mtime_ns": 1784192400000000000},
        "unchanged_since": 1784192400,
        "processed_fingerprint": None,
    }


def inbox_fixture(session_id="1" * 16, fingerprint="e" * 64):
    receipts = [
        {
            "receipt_id": "rcpt_" + format(index + 1, "020x"),
            "session_id": session_id,
            "message_sha256": format(index + 1, "064x"),
            "observed_at": "2026-0{0}-16T00:00:00Z".format(index + 6),
            "time_stratum": "2026-0{0}".format(index + 6),
        }
        for index in range(2)
    ]
    value = {
        "schema_version": contracts.INBOX_SCHEMA,
        "inbox_id": "",
        "session_id": session_id,
        "source": "codex",
        "session_fingerprint": fingerprint,
        "receipts": receipts,
        "message_count": len(receipts),
        "truncated_message_count": 0,
        "created_at": "2026-07-16T10:00:00Z",
    }
    value["inbox_id"] = contracts.inbox_identity(value)
    return value
