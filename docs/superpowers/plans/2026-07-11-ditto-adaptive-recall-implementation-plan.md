# Ditto Adaptive Recall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace failed random bounded mining with frozen, salience-selected packets, domain-isolated reducers, and deterministic pack assembly that passes the unchanged 22-item private calibration.

**Architecture:** Keep `ditto.py` stdlib-only and single-file. Extract immutable message receipts, score them locally across the full history, construct six balanced 50K scout packets, reduce work/design/write independently, and let Python assemble and activate the validated pack. Adaptive expansions reuse the same frozen receipt ledger and require exact additional-cost approval.

**Tech Stack:** Python 3.11 stdlib, `unittest`, JSON/JSONL, Markdown skill files, Codex/Claude native plugin hosts.

---

## Scope And File Map

This plan owns only adaptive recall and private calibration.

- Modify `ditto.py`: receipt extraction, salience scoring, packet planning/storage, scout validation/cache, domain-draft validation/cache, deterministic assembly, adaptive-stage planning, CLI commands.
- Create `tests/test_adaptive_recall.py`: focused unit, integration, synthetic-recall, freeze, and assembly tests.
- Modify `tests/test_plugin_runtime.py`: replace public default-candidate assertions with adaptive-plan assertions while retaining legacy-cache compatibility coverage.
- Modify `tests/test_profile_store.py`: validate domain drafts and deterministic assembly against the existing atomic profile store.
- Replace `MINING_PROMPT.md`: high-recall scout contract plus isolated domain-reducer contract.
- Modify `skills/mine/SKILL.md`: prepare-before-approval orchestration and three domain reducers.
- Modify `README.md`: truthful adaptive cost and setup flow.
- Modify `docs/superpowers/specs/2026-07-10-ditto-plugin-design.md`: point the original plugin spec at the approved adaptive-recall amendment.
- Modify `docs/release/plugin-dogfood.md`: append the new calibration stages without private text.

Do not change plugin routing manifests, migration discovery rules, bootstrap download bounds, benchmark files, or video files in this plan.

## Fixed Interfaces

Add these constants and functions to `ditto.py`; later tasks must use these exact names:

Constants: `RECEIPT_SCHEMA_VERSION = "1"`, `SALIENCE_SCHEMA_VERSION = "1"`, `PACKET_SCHEMA_VERSION = "1"`, `SCOUT_REPORT_SCHEMA_VERSION = "2"`, and `DOMAIN_DRAFT_SCHEMA_VERSION = "1"`.

`STAGE_CONFIGS` contains `A` and `B`; each stage has six packets, a 50,000-token packet ceiling, and a 300,000-token selected-source ceiling.

Function signatures are `build_receipt_ledger(records)`, `score_receipts(receipts)`, `select_salience_stage(scored, stage, previously_selected=())`, `pack_selected_receipts(selected, packet_count, packet_tokens)`, `build_adaptive_preflight(result, ditto_home)`, `prepare_adaptive_run(result, ditto_home, stage="A", base_run_id=None)`, `validate_scout_report(report, packet)`, `compute_domain_evidence_hash(domain, evidence_by_id)`, `validate_domain_draft(draft, domain, evidence_by_id, run_plan)`, `assemble_profile_pack(ditto_home, run_plan, domain_drafts)`, and `build_next_stage_plan(ditto_home, run_id)`.

## Test Fixture Contract

Create these shared helpers at the top of `tests/test_adaptive_recall.py` before adding test classes. Later tasks extend the returned dictionaries but do not rename the helpers.

```python
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto_adaptive", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)

def make_record(session_id, messages, source="codex"):
    rendered = [f"===== session:{session_id} source:{source} ====="]
    rendered.extend(f"[{date}]\n{text}" for date, text in messages)
    text = "\n".join(rendered)
    return {
        "session_id": session_id,
        "source": source,
        "first_date": min(date for date, _ in messages),
        "last_date": max(date for date, _ in messages),
        "tokens": max(1, sum(len(value) for _, value in messages) // 4),
        "text": text,
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "messages": [
            {"date": date, "text": value, "ordinal": ordinal}
            for ordinal, (date, value) in enumerate(messages)
        ],
    }

def receipt_fixtures(texts, sessions=None, domains=None):
    sessions = sessions or [f"s{index}" for index in range(len(texts))]
    domains = domains or [("work",) for _ in texts]
    return [
        {
            "schema_version": "1",
            "receipt_id": f"rcpt-{index:020x}",
            "session_id": sessions[index],
            "source": "codex" if index % 2 == 0 else "claude",
            "date": f"2026-{(index % 9) + 1:02d}-01",
            "ordinal": 0,
            "text": text,
            "tokens": max(1, len(text) // 4),
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "domain_hints": list(domains[index]),
        }
        for index, text in enumerate(texts)
    ]

def scored_history_fixture(tokens):
    count = max(12, tokens // 1_000)
    domains = (("work",), ("design",), ("write",))
    receipts = receipt_fixtures(
        [f"specific preference {index} " + ("x" * 3_900) for index in range(count)],
        sessions=[f"session-{index}" for index in range(count)],
        domains=[domains[index % 3] for index in range(count)],
    )
    for index, item in enumerate(receipts):
        item.update({
            "tokens": 1_000,
            "salience": 100 - (index % 17),
            "signal_families": ["preference" if index % 2 else "exploration"],
            "recurrence_sessions": 2,
            "fixture_id": f"generic-{index}",
        })
    return receipts

def rare_signal_fixture(generic_receipts, rare_position):
    scored = scored_history_fixture(max(12_000, generic_receipts * 1_000))[:generic_receipts]
    rare = receipt_fixtures(
        ["never use a fake product screenshot"],
        sessions=["rare-session"],
        domains=[("design",)],
    )[0]
    rare.update({
        "tokens": 8,
        "salience": 10_000,
        "signal_families": ["rejection"],
        "recurrence_sessions": 1,
        "fixture_id": "rare-rejection",
    })
    return [rare] + scored if rare_position == "first" else scored + [rare]

def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

def history_fixture():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    log = root / "logs" / "session.jsonl"
    rows = [
        {
            "timestamp": f"2026-{(index % 9) + 1:02d}-{(index % 27) + 1:02d}T00:00:00Z",
            "payload": {"type": "message", "role": "user", "content": [{"text": f"preference {index} " + ("x" * 3_990)}]},
        }
        for index in range(300)
    ]
    write_jsonl(log, rows)
    return SimpleNamespace(tmp=tmp, root=root, logs=root / "logs", log=log, home=root / "private", rows=rows)

def run_plugin_prepare(history, stage):
    completed = subprocess.run(
        [sys.executable, str(ROOT / "ditto.py"), "plugin", "prepare", "--path", str(history.logs), "--stage", stage, "--ditto-home", str(history.home)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(completed.stdout)

def run_plugin_preflight(history, home):
    return subprocess.run(
        [sys.executable, str(ROOT / "ditto.py"), "plugin", "preflight", "--path", str(history.logs), "--ditto-home", str(home)],
        check=True, capture_output=True, text=True,
    )

def append_live_message(history, text):
    history.rows.append({
        "timestamp": "2026-02-01T00:00:00Z",
        "payload": {"type": "message", "role": "user", "content": [{"text": text}]},
    })
    write_jsonl(history.log, history.rows)

def packet_fixture():
    domains = ("work", "design", "write")
    receipts = receipt_fixtures(
        [f"exact receipt {index}" for index in range(36)],
        sessions=[f"session-{index}" for index in range(36)],
        domains=[(domains[index // 12],) for index in range(36)],
    )
    return {
        "schema_version": "1",
        "packet_hash": "a" * 64,
        "source_tokens": sum(item["tokens"] for item in receipts),
        "receipt_ids": [item["receipt_id"] for item in receipts],
        "receipts": receipts,
        "domain_counts": {domain: 12 for domain in domains},
        "signal_counts": {"preference": 36},
        "first_date": min(item["date"] for item in receipts),
        "last_date": max(item["date"] for item in receipts),
        "sources": ["claude", "codex"],
    }

def scout_evidence(item, domain, index):
    return {
        "evidence_id": f"ev-{domain}-{index:02d}",
        "domain": domain,
        "kind": "explicit",
        "scope": "universal",
        "context": "",
        "signal_family": "preference",
        "instruction": f"specific {domain} instruction {index}",
        "implication": f"perform the exact {domain} behavior {index}",
        "quotes": [{"receipt_id": item["receipt_id"], "session_id": item["session_id"], "date": item["date"], "text": item["text"]}],
        "contradictions": [],
    }

def valid_scout_report(items_per_domain=1):
    packet = packet_fixture()
    evidence = []
    for domain_index, domain in enumerate(("work", "design", "write")):
        for index in range(items_per_domain):
            evidence.append(scout_evidence(packet["receipts"][domain_index * 12 + index], domain, index))
    return {
        "schema_version": "2",
        "packet_hash": packet["packet_hash"],
        "coverage": {"receipt_ids": packet["receipt_ids"], "source_tokens": packet["source_tokens"]},
        "domain_coverage": {domain: "evidence" for domain in ("work", "design", "write")},
        "evidence": evidence,
    }

def extra_work_evidence():
    return scout_evidence(packet_fixture()["receipts"][11], "work", 99)

def evidence_fixture(domains=("work",)):
    out = {}
    for domain in domains:
        for suffix, session, quarter in (("a", "s1", "Q1"), ("b", "s2", "Q2")):
            out[f"ev-{domain}-{suffix}"] = {
                "domain": domain,
                "kind": "inferred",
                "scope": "universal",
                "context": "",
                "sessions": {session},
                "strata": {f"codex:2026-{quarter}"},
                "quote_count": 1,
                "quotes": [{"receipt_id": f"rcpt-{domain}-{suffix}", "session_id": session, "date": "2026-01-01", "text": f"{domain} receipt {suffix}"}],
                "contradictions": [],
            }
    return out

def valid_domain_draft(domain, evidence_ids=None, scope="universal", evidence=None):
    evidence = evidence or evidence_fixture((domain,))
    evidence_ids = evidence_ids or [f"ev-{domain}-a", f"ev-{domain}-b"]
    return {
        "schema_version": "1",
        "domain": domain,
        "evidence_set_hash": ditto.compute_domain_evidence_hash(domain, evidence),
        "status": "active",
        "rules": [{
            "text": f"Specific {domain} rule",
            "implication": f"Perform the specific {domain} action",
            "kind": "inferred",
            "scope": scope,
            "context": "named product" if scope == "contextual" else "",
            "evidence_ids": evidence_ids,
        }],
        "discarded": [],
        "coverage": {"evidence_items": 2, "distinct_sessions": 2, "strata": 2, "unresolved_contradictions": 0},
    }

def contextual_evidence_fixture():
    evidence = evidence_fixture(("design",))
    for item in evidence.values():
        item.update({"scope": "contextual", "context": "named product"})
    return evidence

def single_provider_two_quarter_fixture():
    return evidence_fixture(("write",))

def run_plan_fixture():
    return {"adequate_strata": True, "report_set_hash": "c" * 64, "source_coverage": {"sources": ["codex"], "first_date": "2026-01-01", "last_date": "2026-06-01"}}

def adaptive_run_fixture(active_domains=("work",), shared_receipts=False):
    tmp = tempfile.TemporaryDirectory()
    home = Path(tmp.name) / "private"
    run_dir = home / "runs" / "20260711T120000Z-1234abcd"
    run_dir.mkdir(parents=True)
    evidence = evidence_fixture(tuple(active_domains))
    report_evidence = []
    for evidence_id, item in sorted(evidence.items()):
        report_evidence.append({
            "evidence_id": evidence_id,
            "domain": item["domain"],
            "kind": item["kind"],
            "scope": item["scope"],
            "context": item["context"],
            "signal_family": "recurrence",
            "instruction": f"Specific {item['domain']} instruction",
            "implication": f"Perform the specific {item['domain']} action",
            "quotes": item["quotes"],
            "contradictions": item["contradictions"],
        })
    report_path = run_dir / "scout-report.json"
    report_path.write_text(json.dumps({
        "schema_version": "2",
        "packet_hash": "a" * 64,
        "coverage": {
            "receipt_ids": sorted({quote["receipt_id"] for item in report_evidence for quote in item["quotes"]}),
            "source_tokens": 100,
        },
        "domain_coverage": {
            domain: "evidence" if domain in active_domains else "no-signal"
            for domain in ("work", "design", "write")
        },
        "evidence": report_evidence,
    }), encoding="utf-8")
    drafts = {}
    for domain in ("work", "design", "write"):
        if domain in active_domains:
            drafts[domain] = valid_domain_draft(domain)
        else:
            drafts[domain] = {
                "schema_version": "1",
                "domain": domain,
                "evidence_set_hash": "b" * 64,
                "status": "inactive",
                "reason": "insufficient evidence",
                "deepen_instruction": f"run ditto and deepen {domain}",
                "rules": [],
                "discarded": [],
                "coverage": {"evidence_items": 0, "distinct_sessions": 0, "strata": 0, "unresolved_contradictions": 0},
            }
    plan = {
        "run_id": "20260711T120000Z-1234abcd",
        "run_dir": str(run_dir),
        "pack_path": str(run_dir / "pack"),
        "scout_report_paths": [str(report_path)],
        "report_set_hash": "c" * 64,
        "source_coverage": {"sources": ["claude", "codex"], "first_date": "2026-01-01", "last_date": "2026-06-01"},
        "selected_source_tokens": 100,
        "corpus_snapshot_hash": "d" * 64,
        "selected_receipt_ids": sorted({quote["receipt_id"] for item in report_evidence for quote in item["quotes"]}),
    }
    return SimpleNamespace(tmp=tmp, home=str(home), run_dir=run_dir, plan=plan, domain_drafts=drafts, shared_receipts=shared_receipts)

def directory_hash(path):
    digest = hashlib.sha256()
    for item in sorted(Path(path).iterdir(), key=lambda value: value.name):
        digest.update(item.name.encode("utf-8"))
        digest.update(item.read_bytes())
    return digest.hexdigest()

def load_assembled_card(run):
    result = ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)
    return json.loads((Path(result["pack_path"]) / "card.json").read_text(encoding="utf-8"))

def completed_stage_a_fixture(weak_domains):
    active = tuple(domain for domain in ("work", "design", "write") if domain not in weak_domains)
    run = adaptive_run_fixture(active_domains=active)
    ledger = scored_history_fixture(tokens=700_000)
    ledger_path = run.run_dir / "ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    run.plan.update({
        "stage": "A",
        "ledger_path": str(ledger_path),
        "planned_domains": list(weak_domains),
        "selected_receipt_ids": [item["receipt_id"] for item in ledger[:300]],
    })
    draft_paths = {}
    for domain, draft in run.domain_drafts.items():
        path = run.run_dir / f"{domain}-draft.json"
        path.write_text(json.dumps(draft), encoding="utf-8")
        draft_paths[domain] = str(path)
    run.plan["domain_draft_paths"] = draft_paths
    (run.run_dir / "plan.json").write_text(json.dumps(run.plan), encoding="utf-8")
    return run
```

Public CLI commands after this plan:

```text
python ditto.py plugin preflight [source args] [--deep | --deepen-domain work|design|write]
python ditto.py plugin prepare   [source args] [--stage A | --base-run-id ID]
python ditto.py plugin validate-scout --run-id ID --report PATH
python ditto.py plugin cache-scout    --run-id ID --report PATH
python ditto.py plugin validate-domain --run-id ID --domain work|design|write --draft PATH
python ditto.py plugin cache-domain    --run-id ID --domain work|design|write --draft PATH
python ditto.py plugin assemble        --run-id ID
python ditto.py plugin next-stage      --run-id ID
```

Keep `validate-report` and `cache-report` as compatibility aliases for schema-1 runs. Existing prepared runs and cached profile versions must remain readable.

### Task 1: Extract Immutable Message Receipts

**Files:**
- Modify: `ditto.py:120-260`
- Create: `tests/test_adaptive_recall.py`

- [ ] **Step 1: Write failing receipt-ledger tests**

```python
class ReceiptLedgerTest(unittest.TestCase):
    def test_large_session_becomes_individual_stable_receipts(self):
        record = make_record("s1", [
            ("2026-01-01", "first preference"),
            ("2026-01-02", "second preference"),
        ])
        first = ditto.build_receipt_ledger([record])
        second = ditto.build_receipt_ledger([record])
        self.assertEqual(first, second)
        self.assertEqual(2, len(first))
        self.assertEqual({"s1"}, {item["session_id"] for item in first})
        self.assertTrue(all(re.fullmatch(r"rcpt-[a-f0-9]{20}", item["receipt_id"]) for item in first))

    def test_receipt_text_is_redacted_before_ledger_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {"type": "message", "role": "user", "content": [{"text": "use sk-" + "a" * 24}]},
            }])
            result = ditto.mine_files([str(path)])
            ledger = ditto.build_receipt_ledger(result["records"])
            self.assertNotIn("sk-", ledger[0]["text"])
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.ReceiptLedgerTest -v`

Expected: errors because `build_receipt_ledger` and receipt-bearing records do not exist.

- [ ] **Step 3: Preserve message boundaries in extraction**

Change `mine_files` so each record contains `messages` alongside the existing combined `text`:

```python
record["messages"] = [
    {"date": message_date, "text": redacted_text, "ordinal": ordinal}
    for ordinal, (message_date, redacted_text) in enumerate(kept_messages)
]
```

Implement stable receipt IDs from schema version, session ID, date, ordinal, and exact redacted text hash. Return receipts sorted by `(source, date, session_id, ordinal, receipt_id)`.

- [ ] **Step 4: Run receipt and legacy extraction tests**

Run: `python -m unittest tests.test_adaptive_recall.ReceiptLedgerTest tests.test_ditto.DittoCliTest tests.test_plugin_runtime.SessionRecordTest -v`

Expected: all tests pass; legacy corpus text remains byte-compatible except for the extraction-schema cache bump.

- [ ] **Step 5: Commit**

```powershell
git add ditto.py tests/test_adaptive_recall.py
git commit -m "feat: extract stable Ditto receipts"
```

### Task 2: Score Salience And Cross-Session Recurrence

**Files:**
- Modify: `ditto.py`
- Modify: `tests/test_adaptive_recall.py`

- [ ] **Step 1: Write failing salience tests**

```python
class SalienceIndexTest(unittest.TestCase):
    def test_rare_correction_outranks_generic_request(self):
        receipts = receipt_fixtures([
            "can you help with this",
            "never call it done until you verified it live",
        ])
        scored = ditto.score_receipts(receipts)
        by_text = {item["text"]: item for item in scored}
        self.assertGreater(by_text[receipts[1]["text"]]["salience"], by_text[receipts[0]["text"]]["salience"])
        self.assertIn("directive", by_text[receipts[1]["text"]]["signal_families"])

    def test_repeated_pattern_requires_distinct_sessions(self):
        receipts = receipt_fixtures(["no em dash", "no em dash", "no em dash"], sessions=["a", "a", "b"])
        scored = ditto.score_receipts(receipts)
        self.assertTrue(all(item["recurrence_sessions"] == 2 for item in scored))

    def test_domain_hints_are_nonexclusive(self):
        item = ditto.score_receipts(receipt_fixtures(["make the launch UI real, not a fake screenshot"]))[0]
        self.assertIn("design", item["domain_hints"])
        self.assertIn("write", item["domain_hints"])

    def test_hebrew_and_mixed_unicode_round_trip_exactly(self):
        text = "אל תשתמש בצילום מסך מזויף — keep it real"
        item = ditto.score_receipts(receipt_fixtures([text]))[0]
        self.assertEqual(text, item["text"])
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.SalienceIndexTest -v`

Expected: errors because `score_receipts` is missing.

- [ ] **Step 3: Implement versioned deterministic features**

Add language-neutral structural features, small English/Hebrew marker sets, normalized 3-5-token shingles, and cross-session recurrence counts. The return item must preserve the complete receipt and add only:

```python
{
    "salience": integer_score,
    "signal_families": sorted(signal_families),
    "domain_hints": sorted(domain_hints),
    "recurrence_sessions": distinct_session_count,
    "salience_hash": sha256_text(canonical_json(feature_identity)),
}
```

Do not discard unknown-language receipts. Give them exploration eligibility and structural scores.

- [ ] **Step 4: Run salience tests and a determinism loop**

Run: `python -m unittest tests.test_adaptive_recall.SalienceIndexTest -v`

Run twice: `python -m unittest tests.test_adaptive_recall.SalienceIndexTest.test_repeated_pattern_requires_distinct_sessions -v`

Expected: identical passing output.

- [ ] **Step 5: Commit**

```powershell
git add ditto.py tests/test_adaptive_recall.py
git commit -m "feat: score high-signal Ditto receipts"
```

### Task 3: Build Balanced Salience Lanes And Packets

**Files:**
- Modify: `ditto.py`
- Modify: `tests/test_adaptive_recall.py`

- [ ] **Step 1: Write failing selection tests**

```python
class PacketSelectionTest(unittest.TestCase):
    def test_stage_a_is_deterministic_bounded_and_domain_balanced(self):
        scored = scored_history_fixture(tokens=600_000)
        selected = ditto.select_salience_stage(scored, "A")
        packets = ditto.pack_selected_receipts(selected, 6, 50_000)
        self.assertLessEqual(sum(item["tokens"] for item in selected), 300_000)
        self.assertLessEqual(len(packets), 6)
        self.assertTrue(all(packet["source_tokens"] <= 50_000 for packet in packets))
        for domain in ("work", "design", "write"):
            self.assertTrue(any(domain in item["domain_hints"] for item in selected))
        self.assertEqual(packets, ditto.pack_selected_receipts(selected, 6, 50_000))

    def test_rare_late_rejection_survives_large_generic_history(self):
        scored = rare_signal_fixture(generic_receipts=10_000, rare_position="last")
        selected = ditto.select_salience_stage(scored, "A")
        self.assertIn("rare-rejection", {item["fixture_id"] for item in selected})

    def test_stage_b_excludes_every_stage_a_receipt(self):
        scored = scored_history_fixture(tokens=800_000)
        first = ditto.select_salience_stage(scored, "A")
        second = ditto.select_salience_stage(scored, "B", [item["receipt_id"] for item in first])
        self.assertTrue({item["receipt_id"] for item in first}.isdisjoint(
            {item["receipt_id"] for item in second}
        ))
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.PacketSelectionTest -v`

Expected: missing selection functions.

- [ ] **Step 3: Implement round-robin lane selection**

Create queues keyed by `(domain, source, quarter, signal_family)`. Select high-salience receipts round-robin, then fill unused budget from the exploration reserve. Allow one receipt to satisfy multiple domain coverage counters but include its text only once in a packet.

Packet metadata must be:

```python
{
    "schema_version": PACKET_SCHEMA_VERSION,
    "packet_hash": packet_hash,
    "source_tokens": source_tokens,
    "receipt_ids": receipt_ids,
    "domain_counts": {"work": n, "design": n, "write": n},
    "signal_counts": signal_counts,
    "first_date": first_date,
    "last_date": last_date,
    "sources": sources,
}
```

- [ ] **Step 4: Run selection tests**

Run: `python -m unittest tests.test_adaptive_recall.PacketSelectionTest -v`

Expected: all pass without network access or filesystem writes.

- [ ] **Step 5: Commit**

```powershell
git add ditto.py tests/test_adaptive_recall.py
git commit -m "feat: select balanced Ditto scout packets"
```

### Task 4: Freeze Exact Adaptive Runs Before Approval

**Files:**
- Modify: `ditto.py`
- Modify: `tests/test_adaptive_recall.py`
- Modify: `tests/test_plugin_runtime.py`

- [ ] **Step 1: Write failing immutable-run tests**

```python
class AdaptivePlanTest(unittest.TestCase):
    def test_prepare_freezes_exact_packets_and_cost(self):
        prepared = run_plugin_prepare(history_fixture(), stage="A")
        self.assertEqual(6, prepared["planned_scout_calls"])
        self.assertEqual(3, prepared["planned_domain_reducer_calls"])
        self.assertEqual(["design", "work", "write"], prepared["planned_domains"])
        self.assertTrue(all(Path(path).is_file() for path in prepared["packet_paths"]))

    def test_live_history_change_does_not_change_prepared_run(self):
        prepared = run_plugin_prepare(history_fixture(), stage="A")
        before = Path(prepared["plan_path"]).read_bytes()
        append_live_message(history, "new message after approval")
        self.assertEqual(before, Path(prepared["plan_path"]).read_bytes())

    def test_preflight_remains_read_only(self):
        history = history_fixture()
        run_plugin_preflight(history, history.home)
        self.assertFalse(history.home.exists())
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.AdaptivePlanTest -v`

Expected: adaptive plan fields and frozen packet paths are missing.

- [ ] **Step 3: Add private receipt, packet, and run paths**

Extend `private_paths` with schema-versioned `receipts`, `salience`, `packets`, `scout_reports`, and `domain_drafts` roots. `prepare_adaptive_run` atomically writes:

```text
runs/{run_id}/ledger.json
runs/{run_id}/packets/{packet_hash}.txt
runs/{run_id}/packet-manifest.json
runs/{run_id}/plan.json
```

The plan stores exact selected receipt hashes, packet hashes, paths, planned calls, cache hits, source coverage, and a corpus snapshot hash.

- [ ] **Step 4: Make adaptive Stage A the public default**

`plugin preflight` returns an estimate. `plugin prepare --stage A` freezes the plan. Keep explicit legacy `--candidate` parsing only for already-documented development reproduction; omit it from public help and reject it without `DITTO_ALLOW_LEGACY_CANDIDATES=1`.

- [ ] **Step 5: Run plan tests and existing CLI tests**

Run: `python -m unittest tests.test_adaptive_recall.AdaptivePlanTest tests.test_plugin_runtime.PluginRuntimeCliTest tests.test_plugin_runtime.PreflightTest -v`

Expected: exact costs remain stable after live source mutation; preflight writes nothing.

- [ ] **Step 6: Commit**

```powershell
git add ditto.py tests/test_adaptive_recall.py tests/test_plugin_runtime.py
git commit -m "feat: freeze adaptive Ditto plans before approval"
```

### Task 5: Validate And Cache High-Recall Scout Reports

**Files:**
- Modify: `ditto.py`
- Modify: `tests/test_adaptive_recall.py`
- Modify: `MINING_PROMPT.md`

- [ ] **Step 1: Write failing schema tests**

```python
class ScoutReportTest(unittest.TestCase):
    def test_each_domain_has_an_independent_twelve_item_budget(self):
        report = valid_scout_report(items_per_domain=12)
        ditto.validate_scout_report(report, packet_fixture())
        report["evidence"].append(extra_work_evidence())
        with self.assertRaisesRegex(ValueError, "work evidence ceiling"):
            ditto.validate_scout_report(report, packet_fixture())

    def test_receipt_must_match_exact_packet_text_and_date(self):
        report = valid_scout_report(items_per_domain=1)
        report["evidence"][0]["quotes"][0]["receipt_id"] = "rcpt-" + "0" * 20
        with self.assertRaisesRegex(ValueError, "receipt"):
            ditto.validate_scout_report(report, packet_fixture())

    def test_contextual_evidence_requires_context(self):
        report = valid_scout_report(items_per_domain=1)
        report["evidence"][0]["scope"] = "contextual"
        report["evidence"][0]["context"] = ""
        with self.assertRaisesRegex(ValueError, "context"):
            ditto.validate_scout_report(report, packet_fixture())
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.ScoutReportTest -v`

Expected: schema-2 validator is missing.

- [ ] **Step 3: Implement schema-2 validation and cache**

Require exact `work`, `design`, and `write` domain coverage, maximum 12 evidence items per domain, maximum 24,576 canonical JSON bytes, valid scope/signal family, exact receipt membership, verbatim text/date, and contradiction receipts. Cache by `SCOUT_REPORT_SCHEMA_VERSION/packet_hash.json`.

- [ ] **Step 4: Replace the worker section in `MINING_PROMPT.md`**

Define the packet schema, independent domain budgets, receipt IDs, scope/context semantics, and exact `validate-scout` command. State that scouts maximize recall and never merge cross-packet rules.

- [ ] **Step 5: Run scout and prompt tests**

Run: `python -m unittest tests.test_adaptive_recall.ScoutReportTest tests.test_plugin_runtime.ReportCacheTest -v`

Expected: schema-1 compatibility and schema-2 scout validation both pass.

- [ ] **Step 6: Commit**

```powershell
git add ditto.py MINING_PROMPT.md tests/test_adaptive_recall.py tests/test_plugin_runtime.py
git commit -m "feat: validate high-recall Ditto scout reports"
```

### Task 6: Add Isolated Domain Drafts And Reducer Caches

**Files:**
- Modify: `ditto.py`
- Modify: `tests/test_adaptive_recall.py`
- Modify: `MINING_PROMPT.md`

- [ ] **Step 1: Write failing domain-draft tests**

```python
class DomainDraftTest(unittest.TestCase):
    def test_domain_draft_cannot_reference_another_domain(self):
        evidence = evidence_fixture(domains=("work", "design"))
        draft = valid_domain_draft("work", evidence_ids=["ev-design-a"], evidence=evidence)
        with self.assertRaisesRegex(ValueError, "work evidence"):
            ditto.validate_domain_draft(draft, "work", evidence, run_plan_fixture())

    def test_contextual_rule_cannot_be_universal(self):
        evidence = contextual_evidence_fixture()
        draft = valid_domain_draft("design", scope="universal", evidence=evidence)
        with self.assertRaisesRegex(ValueError, "scope"):
            ditto.validate_domain_draft(draft, "design", evidence, run_plan_fixture())

    def test_repeated_single_provider_rule_can_use_two_time_strata(self):
        evidence = single_provider_two_quarter_fixture()
        ditto.validate_domain_draft(valid_domain_draft("write", evidence=evidence), "write", evidence, run_plan_fixture())
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.DomainDraftTest -v`

Expected: domain draft validation is missing.

- [ ] **Step 3: Implement the exact domain-draft schema**

```json
{
  "schema_version": "1",
  "domain": "work",
  "evidence_set_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "status": "active",
  "rules": [],
  "discarded": [{"cluster_id": "cluster-x", "reason": "context-conflict"}],
  "coverage": {
    "evidence_items": 12,
    "distinct_sessions": 8,
    "strata": 3,
    "unresolved_contradictions": 0
  }
}
```

Validate rule evidence, scope, context, contradiction state, distinct sessions, and time/source support. Inactive design/write drafts require the existing exact deepen instruction. Work remains required for activation.

- [ ] **Step 4: Add validate/cache CLI commands**

`validate-domain` is read-only. `cache-domain` writes only the content-addressed validated draft and updates the run plan when all three domain drafts are present.

- [ ] **Step 5: Add one reducer contract per domain**

Update `MINING_PROMPT.md` so a reducer reads only the named domain evidence projection, writes one assigned JSON draft, records discarded conflicts, and self-validates before returning.

- [ ] **Step 6: Run domain tests**

Run: `python -m unittest tests.test_adaptive_recall.DomainDraftTest -v`

Expected: all pass, including single-provider/two-time-strata evidence.

- [ ] **Step 7: Commit**

```powershell
git add ditto.py MINING_PROMPT.md tests/test_adaptive_recall.py
git commit -m "feat: reduce Ditto evidence by domain"
```

### Task 7: Assemble Packs Deterministically In Python

**Files:**
- Modify: `ditto.py`
- Modify: `tests/test_adaptive_recall.py`
- Modify: `tests/test_profile_store.py`

- [ ] **Step 1: Write failing assembly tests**

```python
class DeterministicAssemblyTest(unittest.TestCase):
    def test_assembly_writes_only_exact_active_domain_files(self):
        run = adaptive_run_fixture(active_domains=("work", "write"))
        result = ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)
        self.assertEqual(
            {"you.md", "you-writer.md", "appendix.md", "card.json", "draft-manifest.json"},
            {item.name for item in Path(result["pack_path"]).iterdir()},
        )

    def test_assembly_is_byte_deterministic(self):
        run = adaptive_run_fixture(active_domains=("work", "design", "write"))
        first = directory_hash(ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)["pack_path"])
        second = directory_hash(ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)["pack_path"])
        self.assertEqual(first, second)

    def test_card_counts_distinct_sessions(self):
        run = adaptive_run_fixture(shared_receipts=True)
        card = load_assembled_card(run)
        self.assertEqual("2 sessions", card["laws"][0]["count"])
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.DeterministicAssemblyTest -v`

Expected: deterministic assembler is missing.

- [ ] **Step 3: Implement Markdown, appendix, card, and manifest renderers**

Sort domains, rules, evidence IDs, and receipts canonically. Escape Markdown control characters in private receipts. Render exact `ditto-work-profile`, `ditto-design-profile`, and `ditto-write-profile` frontmatter. Select at most three work laws by evidence-session count, then stable rule text.

- [ ] **Step 4: Add `plugin assemble --run-id`**

The command loads three validated cached domain drafts, assembles the assigned pack, runs the existing pack validator, and returns the pack path and manifest inputs. It performs no model call and does not activate. Existing `plugin activate` remains the only pointer mutation.

- [ ] **Step 5: Run assembly and atomic-store tests**

Run: `python -m unittest tests.test_adaptive_recall.DeterministicAssemblyTest tests.test_profile_store -v`

Expected: deterministic bytes, exact files, and rollback safety pass.

- [ ] **Step 6: Commit**

```powershell
git add ditto.py tests/test_adaptive_recall.py tests/test_profile_store.py
git commit -m "feat: assemble Ditto profiles deterministically"
```

### Task 8: Plan Adaptive Expansions From The Frozen Corpus

**Files:**
- Modify: `ditto.py`
- Modify: `tests/test_adaptive_recall.py`

- [ ] **Step 1: Write failing next-stage tests**

```python
class AdaptiveStageTest(unittest.TestCase):
    def test_next_stage_reuses_snapshot_and_prior_artifacts(self):
        run = completed_stage_a_fixture(weak_domains=("design", "write"))
        next_plan = ditto.build_next_stage_plan(run.home, run.run_id)
        self.assertEqual(run.plan["corpus_snapshot_hash"], next_plan["corpus_snapshot_hash"])
        self.assertEqual(["design", "write"], next_plan["planned_domains"])
        self.assertGreater(next_plan["cached_scout_reports"], 0)
        self.assertTrue(set(next_plan["selected_receipt_ids"]).isdisjoint(run.plan["selected_receipt_ids"]))

    def test_strong_stable_domains_are_not_rereduced(self):
        run = completed_stage_a_fixture(weak_domains=("write",))
        next_plan = ditto.build_next_stage_plan(run.home, run.run_id)
        self.assertEqual(["write"], next_plan["planned_domains"])
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.AdaptiveStageTest -v`

Expected: next-stage controller is missing.

- [ ] **Step 3: Implement non-semantic coverage metrics**

Use draft status, rule count, evidence count, distinct sessions, strata, unresolved contradictions, lane exhaustion, and new-cluster yield. Do not read the private calibration checklist.

- [ ] **Step 4: Implement `plugin next-stage --run-id`**

Write the next immutable stage under the original run's snapshot root. Return only additional selected tokens, packet calls, affected reducers, cache hits, and the separate full-history option. Do not start model work.

- [ ] **Step 5: Run stage tests**

Run: `python -m unittest tests.test_adaptive_recall.AdaptiveStageTest -v`

Expected: all pass; no live-source read occurs after the initial freeze.

- [ ] **Step 6: Commit**

```powershell
git add ditto.py tests/test_adaptive_recall.py
git commit -m "feat: plan adaptive Ditto expansions"
```

### Task 9: Update Native Mining Orchestration And Public Docs

**Files:**
- Modify: `skills/mine/SKILL.md`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-10-ditto-plugin-design.md`
- Modify: `tests/test_plugin_manifests.py`
- Modify: `tests/test_adaptive_recall.py`

- [ ] **Step 1: Write failing documentation-contract tests**

```python
def test_mine_skill_freezes_before_model_approval(self):
    text = (ROOT / "skills" / "mine" / "SKILL.md").read_text(encoding="utf-8")
    self.assertLess(text.index("plugin prepare"), text.index("wait for approval"))
    self.assertIn("three domain reducers", text)
    self.assertIn("plugin assemble", text)

def test_readme_states_stage_a_exact_ceiling(self):
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    self.assertIn("300K selected source tokens", text)
    self.assertIn("six scouts and three domain reducers", text)
    self.assertNotIn("6 × 25K", text)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_adaptive_recall.DocumentationContractTest tests.test_plugin_manifests -v`

Expected: old candidate-ladder wording causes failures.

- [ ] **Step 3: Rewrite `skills/mine/SKILL.md` flow**

The skill must:

1. run read-only preflight;
2. run local-only prepare;
3. display the exact frozen plan and wait for approval;
4. run one fast scout per uncached packet with self-validation;
5. cache each scout report;
6. run only the planned strong domain reducers with self-validation;
7. cache each draft;
8. run deterministic assemble and explicit activate;
9. report status, calls, cache reuse, card, and next-stage instruction.

- [ ] **Step 4: Update public documentation**

Remove the public random candidate ladder. Explain Stage A, prepare-before-approval, adaptive next stages, full-history fallback, zero-call installation, and no subscription-percentage claims. Link the original plugin design to the adaptive-recall amendment.

- [ ] **Step 5: Run docs and plugin tests**

Run: `python -m unittest tests.test_adaptive_recall.DocumentationContractTest tests.test_plugin_manifests -v`

Expected: all documentation truth tests pass.

- [ ] **Step 6: Commit**

```powershell
git add skills/mine/SKILL.md README.md docs/superpowers/specs/2026-07-10-ditto-plugin-design.md tests/test_plugin_manifests.py tests/test_adaptive_recall.py
git commit -m "docs: route Ditto through adaptive recall"
```

### Task 10: Run Full Regression, Privacy, And Performance Verification

**Files:**
- Modify only files required by failing in-scope tests.

- [ ] **Step 1: Run the complete suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass; no test contacts the network.

- [ ] **Step 2: Validate the plugin**

Run:

```powershell
python "$HOME\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" "D:\worktrees\ditto-plugin-release"
```

Expected: `Plugin validation passed`.

- [ ] **Step 3: Add the synthetic 3.2M-token performance test**

```python
class PerformanceTest(unittest.TestCase):
    def test_local_stage_a_planning_stays_under_two_minutes(self):
        records = [
            make_record(
                f"session-{index}",
                [(f"2026-{(index % 9) + 1:02d}-01", f"specific preference {index} " + ("x" * 3_980))],
                source="codex" if index % 2 == 0 else "claude",
            )
            for index in range(3_200)
        ]
        started = time.perf_counter()
        receipts = ditto.build_receipt_ledger(records)
        scored = ditto.score_receipts(receipts)
        selected = ditto.select_salience_stage(scored, "A")
        packets = ditto.pack_selected_receipts(selected, 6, 50_000)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 120)
        self.assertLessEqual(sum(item["tokens"] for item in selected), 300_000)
        self.assertLessEqual(len(packets), 6)
```

Add `import time` to the test module imports.

- [ ] **Step 4: Run the synthetic performance fixture**

Run: `python -m unittest tests.test_adaptive_recall.PerformanceTest -v`

Expected: local extraction, salience indexing, and Stage-A planning finish under 120 seconds on the development machine, schedule zero model calls, and select no more than 300K tokens.

- [ ] **Step 5: Verify privacy and diff hygiene**

Run:

```powershell
git diff --check
git status --short
rg -n "C:\\Users|session:[a-f0-9]|receipt text" docs README.md skills .codex-plugin
```

Expected: no private run files or raw receipt text in Git; only intended source/docs changes appear.

- [ ] **Step 6: Commit any test-driven corrections**

```powershell
git add -- ditto.py MINING_PROMPT.md README.md skills/mine/SKILL.md tests/test_adaptive_recall.py tests/test_plugin_runtime.py tests/test_profile_store.py tests/test_plugin_manifests.py docs/superpowers/specs/2026-07-10-ditto-plugin-design.md
git commit -m "test: harden adaptive Ditto recall"
```

Skip this commit when verification required no changes.

### Task 11: Re-Calibrate Stage A Against The Frozen Private Profile

**Files:**
- Modify: `docs/release/plugin-dogfood.md`
- Private only: `$HOME\.ditto`

- [ ] **Step 1: Confirm the frozen checklist identity**

Run:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "$HOME\.ditto\calibration\must-recover.json"
```

Expected SHA-256: `9778cb1eb2fcdbd7aafed01600fc7a1ceaf59f99943d54b692b0aaff9efaab09`.

- [ ] **Step 2: Prepare the immutable Stage-A run without model calls**

Run: `python ditto.py plugin prepare --stage A`

Record the exact run ID, selected tokens, packet paths, cache hits, planned scouts, and planned domain reducers. Confirm selected tokens are at most 300K and total planned calls are at most nine.

- [ ] **Step 3: Display the exact frozen cost and obtain approval**

Do not run a scout or reducer until the prepared immutable plan is approved. Approval applies only to that run ID.

- [ ] **Step 4: Execute scouts, reducers, assembly, and activation**

Follow `skills/mine/SKILL.md` exactly. Raw packets, reports, domain drafts, profiles, and receipts remain under `DITTO_HOME` and never enter Git.

- [ ] **Step 5: Apply the unchanged checklist**

Record only counts and hashes publicly. Passing requires work 10/10, design 5/5, and write 7/7.

- [ ] **Step 6: Handle the adaptive gate**

If Stage A fails, run `plugin next-stage --run-id ID`, display its exact additional plan, and obtain approval before any additional model pass. Do not alter the checklist or seed scouts/reducers with checklist text.

If no approved stage passes, keep the release stopped and record the honest result.

- [ ] **Step 7: Run three fresh installed-plugin probes only after 22/22**

Use one fresh work, design, and writing task. Each task must state the loaded Ditto skill, produce a real domain-relevant response, and receive a human pass/fail verdict. Store only transcript hashes publicly.

- [ ] **Step 8: Update and commit dogfood evidence**

Append stage tokens, planned/actual calls, cache reuse, checklist counts, probe verdicts, active manifest hash, and known gaps to `docs/release/plugin-dogfood.md` without raw private text.

Run:

```powershell
python -m unittest discover -s tests -v
git diff --check
git status --short
```

Commit only the non-private evidence and any selected default constant:

```powershell
git add docs/release/plugin-dogfood.md ditto.py tests/test_adaptive_recall.py
git commit -m "test: calibrate adaptive Ditto recall"
```

## Completion And Handoff

This plan is complete only when one approved adaptive stage passes 22/22 and all three fresh installed-plugin probes pass. Then resume `docs/superpowers/plans/2026-07-10-ditto-plugin-release-implementation-plan.md` at Task 17.

Task 17 proves live plugin activation, routing, updates, cache reuse, and safe migration. Task 18 runs separate specification and code-quality reviews. Task 19 prepares changelog and GitHub Release artifacts and stops at the explicit push/tag/publication approval gate.

Do not start benchmark execution, leaderboard work, proof clips, or launch-video production.
