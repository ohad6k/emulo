from . import contracts
from .policy import classify_candidate


STATUS_SCHEMA = "emulo.autopilot-status/v1"
QUEUE_SCHEMA = "emulo.autopilot-review-queue/v1"


def _candidate_item(candidate, latest):
    policy = classify_candidate(candidate, auto_activate_enabled=False)
    evidence = candidate["evidence"]
    return {
        "candidate_id": candidate["candidate_id"],
        "kind": candidate["kind"],
        "domain": candidate["domain"],
        "statement": candidate["statement"],
        "scope": list(candidate["scope"]),
        "contradiction_count": candidate["contradiction_count"],
        "risk_categories": list(candidate["risk_categories"]),
        "evidence": {
            "receipts": len(evidence),
            "sessions": len({item["session_id"] for item in evidence}),
            "time_strata": len({item["time_stratum"] for item in evidence}),
        },
        "policy_class": policy.policy_class,
        "policy_reason": policy.reason,
        "decision": "pending" if latest is None else latest["decision"],
        "decision_id": None if latest is None else latest["decision_id"],
        "decision_reason": None if latest is None else latest["reason"],
        "decided_at": None if latest is None else latest["decided_at"],
    }


def review_queue(store):
    latest_by_candidate = {}
    for decision in store.list_decisions():
        latest_by_candidate[decision["candidate_id"]] = decision
    items = [
        _candidate_item(item, latest_by_candidate.get(item["candidate_id"]))
        for item in store.list_candidates()
    ]
    return {"schema_version": QUEUE_SCHEMA, "items": items}


def status_snapshot(store):
    lock = store.get_lock()
    head = store.get_head()
    items = review_queue(store)["items"]
    decisions = [item["decision"] for item in items]
    return {
        "schema_version": STATUS_SCHEMA,
        "health": "locked" if lock is not None else "ready",
        "lock": (
            None
            if lock is None
            else {
                "operation_id": lock["operation_id"],
                "operation": lock["operation"],
                "created_at": lock["created_at"],
            }
        ),
        "active_generation_id": (
            None if head is None else head["generation_id"]
        ),
        "counts": {
            "inbox": len(store.list_inbox()),
            "candidates": len(items),
            "pending": decisions.count("pending"),
            "approved": decisions.count("approve"),
            "rejected": decisions.count("reject"),
            "generations": len(store.list_generations()),
        },
    }


def record_review(store, candidate_id, decision, reason, decided_at):
    candidate = store.get_candidate(candidate_id)
    policy = classify_candidate(candidate, auto_activate_enabled=False)
    if decision == "approve" and policy.policy_class == "reject":
        raise ValueError("candidate policy rejects approval")
    value = {
        "schema_version": contracts.DECISION_SCHEMA,
        "decision_id": "",
        "candidate_id": candidate_id,
        "decision": decision,
        "reason": reason,
        "policy_class": policy.policy_class,
        "decided_at": decided_at,
    }
    value["decision_id"] = contracts.decision_identity(value)
    value = contracts.validate_decision(value)
    store.append_decision(value)
    return value
