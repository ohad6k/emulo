import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
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


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


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


def scored_history_fixture(tokens=600_000):
    domains = ("work", "design", "write", "video")
    per_receipt = 500
    count = tokens // per_receipt
    receipts = receipt_fixtures(
        [f"always preserve exact {domains[index % len(domains)]} preference " + "x" * 1950 for index in range(count)],
        sessions=[f"session-{index}" for index in range(count)],
        domains=[(domains[index % len(domains)],) for index in range(count)],
    )
    for index, item in enumerate(receipts):
        item["tokens"] = per_receipt
        item["salience"] = 100 - (index % 20)
        item["signal_families"] = ["directive"]
        item["fixture_id"] = f"fixture-{index}"
    return receipts


def rare_signal_fixture(generic_receipts=10_000, rare_position="last"):
    receipts = receipt_fixtures(
        ["generic exploration"] * generic_receipts + ["never use a fake screenshot"],
        sessions=[f"session-{index}" for index in range(generic_receipts + 1)],
        domains=[("work",)] * generic_receipts + [("design",)],
    )
    for index, item in enumerate(receipts):
        item["tokens"] = 40
        item["salience"] = 1
        item["signal_families"] = ["exploration"]
        item["fixture_id"] = f"generic-{index}"
    rare = receipts[-1]
    rare.update({"salience": 100, "signal_families": ["directive", "rejection"], "fixture_id": "rare-rejection"})
    if rare_position == "first":
        receipts.insert(0, receipts.pop())
    return receipts


def history_fixture():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    log = root / "logs" / "session.jsonl"
    rows = [
        {
            "timestamp": f"2026-{(index % 9) + 1:02d}-{(index % 27) + 1:02d}T00:00:00Z",
            "payload": {"type": "message", "role": "user", "content": [{
                "text": f"always preserve design write workflow preference {index} " + "x" * 3_990,
            }]},
        }
        for index in range(300)
    ]
    write_jsonl(log, rows)
    return SimpleNamespace(tmp=tmp, root=root, logs=root / "logs", log=log, home=root / "private", rows=rows)


def run_plugin_prepare(history, stage):
    completed = subprocess.run(
        [sys.executable, str(ROOT / "ditto.py"), "plugin", "prepare", "--path", str(history.logs),
         "--stage", stage, "--ditto-home", str(history.home)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(completed.stdout)


def run_plugin_preflight(history, home):
    return subprocess.run(
        [sys.executable, str(ROOT / "ditto.py"), "plugin", "preflight", "--path", str(history.logs),
         "--stage", "A", "--ditto-home", str(home)],
        check=True, capture_output=True, text=True,
    )


def append_live_message(history, text):
    history.rows.append({
        "timestamp": "2026-10-01T00:00:00Z",
        "payload": {"type": "message", "role": "user", "content": [{"text": text}]},
    })
    write_jsonl(history.log, history.rows)


def packet_fixture():
    domains = ("work", "design", "write", "video")
    receipts = receipt_fixtures(
        [f"exact receipt {index}" for index in range(48)],
        sessions=[f"session-{index}" for index in range(48)],
        domains=[(domains[index // 12],) for index in range(48)],
    )
    return {
        "schema_version": "1",
        "packet_hash": "a" * 64,
        "source_tokens": sum(item["tokens"] for item in receipts),
        "receipt_ids": [item["receipt_id"] for item in receipts],
        "receipts": receipts,
        "domain_counts": {domain: 12 for domain in domains},
        "signal_counts": {"preference": 48},
        "first_date": min(item["date"] for item in receipts),
        "last_date": max(item["date"] for item in receipts),
        "sources": ["claude", "codex"],
    }


def scout_evidence(item, domain, index):
    evidence = {
        "evidence_id": f"ev-{domain}-{index:02d}",
        "domain": domain,
        "kind": "explicit",
        "scope": "universal",
        "context": "",
        "signal_family": "preference",
        "instruction": f"specific {domain} instruction {index}",
        "implication": f"perform the exact {domain} behavior {index}",
        "quotes": [{
            "receipt_id": item["receipt_id"], "session_id": item["session_id"],
            "date": item["date"], "text": item["text"],
        }],
        "contradictions": [],
    }
    if domain == "write":
        evidence["register"] = "casual"
    return evidence


def valid_scout_report(items_per_domain=1):
    packet = packet_fixture()
    evidence = []
    for domain_index, domain in enumerate(("work", "design", "write", "video")):
        for index in range(items_per_domain):
            evidence.append(scout_evidence(packet["receipts"][domain_index * 12 + index], domain, index))
    return {
        "schema_version": "3",
        "packet_hash": packet["packet_hash"],
        "coverage": {"receipt_ids": packet["receipt_ids"], "source_tokens": packet["source_tokens"]},
        "domain_coverage": {domain: "evidence" for domain in ("work", "design", "write", "video")},
        "evidence": evidence,
    }


def extra_work_evidence():
    return scout_evidence(packet_fixture()["receipts"][11], "work", 99)


def evidence_fixture(domains=("work",)):
    out = {}
    for domain in domains:
        for suffix, session, quarter in (("a", "s1", "Q1"), ("b", "s2", "Q2")):
            out[f"ev-{domain}-{suffix}"] = {
                "domain": domain, "kind": "inferred", "scope": "universal", "context": "",
                "sessions": {session}, "strata": {f"codex:2026-{quarter}"}, "quote_count": 1,
                "quotes": [{"receipt_id": f"rcpt-{domain}-{suffix}", "session_id": session,
                            "date": "2026-01-01", "text": f"{domain} receipt {suffix}"}],
                "contradictions": [],
            }
            if domain == "write":
                out[f"ev-{domain}-{suffix}"]["register"] = "casual"
    return out


def valid_domain_draft(domain, evidence_ids=None, scope="universal", evidence=None):
    evidence = evidence or evidence_fixture((domain,))
    evidence_ids = evidence_ids or [f"ev-{domain}-a", f"ev-{domain}-b"]
    rule = {"text": f"Specific {domain} rule", "implication": f"Perform the specific {domain} action",
            "kind": "inferred", "scope": scope,
            "context": "named product" if scope == "contextual" else "",
            "evidence_ids": evidence_ids}
    if domain == "write":
        registers = {evidence[evidence_id].get("register", "shared") for evidence_id in evidence_ids if evidence_id in evidence}
        rule["register"] = next(iter(registers)) if len(registers) == 1 else "shared"
    return {
        "schema_version": "2", "domain": domain,
        "evidence_set_hash": ditto.compute_domain_evidence_hash(domain, evidence),
        "status": "active",
        "rules": [rule],
        "discarded": [],
        "coverage": {"evidence_items": 2, "distinct_sessions": 2, "strata": 2,
                     "unresolved_contradictions": 0},
    }


def contextual_evidence_fixture():
    evidence = evidence_fixture(("design",))
    for item in evidence.values():
        item.update({"scope": "contextual", "context": "named product"})
    return evidence


def single_provider_two_quarter_fixture():
    return evidence_fixture(("write",))


def run_plan_fixture():
    return {"adequate_strata": True, "report_set_hash": "c" * 64,
            "source_coverage": {"sources": ["codex"], "first_date": "2026-01-01", "last_date": "2026-06-01"}}


def adaptive_run_fixture(active_domains=("work",), shared_receipts=False):
    tmp = tempfile.TemporaryDirectory()
    home = Path(tmp.name) / "private"
    run_dir = home / "runs" / "20260711T120000Z-1234abcd"
    run_dir.mkdir(parents=True)
    evidence = evidence_fixture(tuple(active_domains))
    if shared_receipts and "work" in active_domains:
        evidence["ev-work-b"]["sessions"] = {"s2"}
    plan = {
        "run_id": "20260711T120000Z-1234abcd", "run_dir": str(run_dir),
        "pack_path": str(run_dir / "pack"), "report_set_hash": "c" * 64,
        "source_coverage": {"sources": ["claude", "codex"], "first_date": "2026-01-01", "last_date": "2026-06-01"},
        "selected_source_tokens": 100, "adequate_strata": True,
        "evidence_by_id": evidence,
    }
    drafts = {}
    for domain in ("work", "design", "write", "video"):
        if domain in active_domains:
            drafts[domain] = valid_domain_draft(domain, evidence=evidence)
        else:
            domain_evidence = evidence_fixture((domain,))
            drafts[domain] = {
                "schema_version": "2", "domain": domain,
                "evidence_set_hash": ditto.compute_domain_evidence_hash(domain, evidence),
                "status": "inactive", "reason": "insufficient evidence",
                "deepen_instruction": f"run ditto and deepen {domain}", "rules": [], "discarded": [],
                "coverage": {"evidence_items": 0, "distinct_sessions": 0, "strata": 0,
                             "unresolved_contradictions": 0},
            }
    return SimpleNamespace(tmp=tmp, home=str(home), run_dir=run_dir, plan=plan, domain_drafts=drafts)


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
    active = tuple(domain for domain in ("work", "design", "write", "video") if domain not in weak_domains)
    run = adaptive_run_fixture(active_domains=active)
    run.run_id = run.plan["run_id"]
    run.plan.pop("evidence_by_id", None)
    ledger = scored_history_fixture(tokens=700_000)
    ledger_path = run.run_dir / "ledger.json"
    ledger_path.write_text(json.dumps({"schema_version": "1", "receipts": ledger}), encoding="utf-8")
    draft_paths = {}
    for domain, draft in run.domain_drafts.items():
        path = run.run_dir / f"{domain}-draft.json"
        path.write_text(json.dumps(draft), encoding="utf-8")
        draft_paths[domain] = str(path)
    scout_path = run.run_dir / "scout-a.json"
    scout_path.write_text("{}", encoding="utf-8")
    run.plan.update({
        "stage": "A", "ledger_path": str(ledger_path), "domain_draft_paths": draft_paths,
        "scout_report_paths": [str(scout_path)], "corpus_snapshot_hash": "d" * 64,
        "selected_receipt_ids": [item["receipt_id"] for item in ledger[:600]],
    })
    (run.run_dir / "plan.json").write_text(json.dumps(run.plan), encoding="utf-8")
    return run


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
        self.assertTrue(all(
            re.fullmatch(r"rcpt-[a-f0-9]{20}", item["receipt_id"])
            for item in first
        ))

    def test_receipt_text_is_redacted_before_ledger_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "use sk-" + "a" * 24}],
                },
            }])

            result = ditto.mine_files([str(path)])
            ledger = ditto.build_receipt_ledger(result["records"])

            self.assertNotIn("sk-", ledger[0]["text"])


class SalienceIndexTest(unittest.TestCase):
    def test_rare_correction_outranks_generic_request(self):
        receipts = receipt_fixtures([
            "can you help with this",
            "never call it done until you verified it live",
        ])

        scored = ditto.score_receipts(receipts)
        by_text = {item["text"]: item for item in scored}

        self.assertGreater(
            by_text[receipts[1]["text"]]["salience"],
            by_text[receipts[0]["text"]]["salience"],
        )
        self.assertIn("directive", by_text[receipts[1]["text"]]["signal_families"])

    def test_repeated_pattern_counts_distinct_sessions(self):
        receipts = receipt_fixtures(
            ["no em dash", "no em dash", "no em dash"],
            sessions=["a", "a", "b"],
        )

        scored = ditto.score_receipts(receipts)

        self.assertTrue(all(item["recurrence_sessions"] == 2 for item in scored))

    def test_domain_hints_are_nonexclusive(self):
        item = ditto.score_receipts(receipt_fixtures([
            "make the launch UI real, not a fake screenshot",
        ]))[0]

        self.assertIn("design", item["domain_hints"])
        self.assertIn("write", item["domain_hints"])

    def test_hebrew_and_mixed_unicode_round_trip_exactly(self):
        text = "אל תשתמש בצילום מסך מזויף — keep it real"

        item = ditto.score_receipts(receipt_fixtures([text]))[0]

        self.assertEqual(text, item["text"])


class PacketSelectionTest(unittest.TestCase):
    def test_stage_a_is_deterministic_bounded_and_domain_balanced(self):
        scored = scored_history_fixture(tokens=600_000)
        selected = ditto.select_salience_stage(scored, "A")
        packets = ditto.pack_selected_receipts(selected, 6, 50_000)

        self.assertLessEqual(sum(item["tokens"] for item in selected), 300_000)
        self.assertLessEqual(len(packets), 6)
        self.assertTrue(all(packet["source_tokens"] <= 50_000 for packet in packets))
        for domain in ("work", "design", "write", "video"):
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


class AdaptivePlanTest(unittest.TestCase):
    def test_prepare_freezes_exact_packets_and_cost(self):
        history = history_fixture()
        self.addCleanup(history.tmp.cleanup)
        prepared = run_plugin_prepare(history, stage="A")

        self.assertEqual(6, prepared["planned_scout_calls"])
        self.assertEqual(4, prepared["planned_domain_reducer_calls"])
        self.assertEqual(["design", "video", "work", "write"], prepared["planned_domains"])
        self.assertTrue(all(Path(path).is_file() for path in prepared["packet_paths"]))

    def test_live_history_change_does_not_change_prepared_run(self):
        history = history_fixture()
        self.addCleanup(history.tmp.cleanup)
        prepared = run_plugin_prepare(history, stage="A")
        before = Path(prepared["plan_path"]).read_bytes()

        append_live_message(history, "new message after approval")

        self.assertEqual(before, Path(prepared["plan_path"]).read_bytes())

    def test_preflight_remains_read_only(self):
        history = history_fixture()
        self.addCleanup(history.tmp.cleanup)

        run_plugin_preflight(history, history.home)

        self.assertFalse(history.home.exists())


class ScoutReportTest(unittest.TestCase):
    def test_each_domain_has_an_independent_twelve_item_budget(self):
        report = valid_scout_report(items_per_domain=12)
        ditto.validate_scout_report(report, packet_fixture())
        report["evidence"].append(extra_work_evidence())

        with self.assertRaisesRegex(ValueError, "work evidence ceiling"):
            ditto.validate_scout_report(report, packet_fixture())

    def test_receipt_must_match_exact_packet_text_and_date(self):
        report = valid_scout_report(items_per_domain=1)
        report["evidence"][0]["quotes"][0]["receipt_id"] = "rcpt-" + "f" * 20

        with self.assertRaisesRegex(ValueError, "receipt"):
            ditto.validate_scout_report(report, packet_fixture())

    def test_contextual_evidence_requires_context(self):
        report = valid_scout_report(items_per_domain=1)
        report["evidence"][0]["scope"] = "contextual"
        report["evidence"][0]["context"] = ""

        with self.assertRaisesRegex(ValueError, "context"):
            ditto.validate_scout_report(report, packet_fixture())


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


class DeterministicAssemblyTest(unittest.TestCase):
    def test_assembly_rejects_pack_path_outside_the_assigned_run(self):
        run = adaptive_run_fixture(active_domains=("work",))
        self.addCleanup(run.tmp.cleanup)
        victim = Path(run.tmp.name) / "victim"
        victim.mkdir()
        sentinel = victim / "keep.txt"
        sentinel.write_text("do not delete", encoding="utf-8")
        run.plan["pack_path"] = str(victim)

        with self.assertRaisesRegex(ValueError, "assigned run directory"):
            ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)

        self.assertEqual("do not delete", sentinel.read_text(encoding="utf-8"))

    def test_assembly_writes_only_exact_active_domain_files(self):
        run = adaptive_run_fixture(active_domains=("work", "write"))
        self.addCleanup(run.tmp.cleanup)

        result = ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)

        self.assertEqual(
            {"you.md", "you-writer.md", "appendix.md", "card.json", "draft-manifest.json"},
            {item.name for item in Path(result["pack_path"]).iterdir()},
        )

    def test_assembly_is_byte_deterministic(self):
        run = adaptive_run_fixture(active_domains=("work", "design", "write", "video"))
        self.addCleanup(run.tmp.cleanup)

        first = directory_hash(ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)["pack_path"])
        second = directory_hash(ditto.assemble_profile_pack(run.home, run.plan, run.domain_drafts)["pack_path"])

        self.assertEqual(first, second)

    def test_card_counts_distinct_sessions(self):
        run = adaptive_run_fixture(active_domains=("work",), shared_receipts=True)
        self.addCleanup(run.tmp.cleanup)

        card = load_assembled_card(run)

        self.assertEqual("2 sessions", card["laws"][0]["count"])


class AdaptiveStageTest(unittest.TestCase):
    def test_next_stage_reuses_snapshot_and_prior_artifacts(self):
        run = completed_stage_a_fixture(weak_domains=("design", "write"))
        self.addCleanup(run.tmp.cleanup)

        next_plan = ditto.build_next_stage_plan(run.home, run.run_id)

        self.assertEqual(run.plan["corpus_snapshot_hash"], next_plan["corpus_snapshot_hash"])
        self.assertEqual(["design", "write"], next_plan["planned_domains"])
        self.assertGreater(next_plan["cached_scout_reports"], 0)
        self.assertTrue(set(next_plan["selected_receipt_ids"]).isdisjoint(run.plan["selected_receipt_ids"]))

    def test_strong_stable_domains_are_not_rereduced(self):
        run = completed_stage_a_fixture(weak_domains=("write",))
        self.addCleanup(run.tmp.cleanup)

        next_plan = ditto.build_next_stage_plan(run.home, run.run_id)

        self.assertEqual(["write"], next_plan["planned_domains"])


class DocumentationContractTest(unittest.TestCase):
    def test_mine_skill_uses_full_default_and_labels_preview_and_adaptive_honestly(self):
        text = (ROOT / "skills" / "mine" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("full-history quality default", text.lower())
        self.assertIn("quick preview creates a starter profile", text.lower())
        self.assertIn("experimental", text.lower())
        self.assertIn("plugin prepare", text)
        self.assertNotIn("plugin prepare --stage A", text)

    def test_readme_keeps_adaptive_recall_out_of_quality_default_release_path(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("quick-preview ladder", text)
        self.assertIn("full-history quality default", text.lower())
        self.assertIn("Experimental adaptive recall", text)
        self.assertNotIn("Stage A has a hard ceiling", text)


class ExperimentalAdaptiveRoutingTest(unittest.TestCase):
    def run_preflight(self, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "logs" / "one.jsonl", [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {"type": "message", "role": "user", "content": [{"text": "specific signal"}]},
            }])
            completed = subprocess.run(
                [sys.executable, str(ROOT / "ditto.py"), "plugin", "preflight", "--path",
                 str(root / "logs"), *extra, "--ditto-home", str(root / "private")],
                check=True, capture_output=True, text=True,
            )
            return json.loads(completed.stdout)

    def test_default_preflight_uses_full_history_not_adaptive(self):
        plan = self.run_preflight()

        self.assertEqual("full", plan["mode"])
        self.assertIsNone(plan["candidate_index"])
        self.assertIn("planned_worker_calls", plan)
        self.assertNotIn("planned_scout_calls", plan)

    def test_adaptive_stage_requires_explicit_flag(self):
        plan = self.run_preflight("--stage", "A")

        self.assertEqual("adaptive", plan["mode"])
        self.assertEqual("A", plan["stage"])


class PerformanceTest(unittest.TestCase):
    def test_local_stage_a_planning_stays_under_two_minutes(self):
        records = [
            make_record(
                f"session-{index}",
                [(f"2026-{(index % 9) + 1:02d}-01", f"specific preference {index} " + "x" * 3_980)],
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


if __name__ == "__main__":
    unittest.main()
