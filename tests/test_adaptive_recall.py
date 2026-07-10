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
    domains = ("work", "design", "write")
    per_receipt = 500
    count = tokens // per_receipt
    receipts = receipt_fixtures(
        [f"always preserve exact {domains[index % 3]} preference " + "x" * 1950 for index in range(count)],
        sessions=[f"session-{index}" for index in range(count)],
        domains=[(domains[index % 3],) for index in range(count)],
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
         "--ditto-home", str(home)],
        check=True, capture_output=True, text=True,
    )


def append_live_message(history, text):
    history.rows.append({
        "timestamp": "2026-10-01T00:00:00Z",
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
        "quotes": [{
            "receipt_id": item["receipt_id"], "session_id": item["session_id"],
            "date": item["date"], "text": item["text"],
        }],
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


class AdaptivePlanTest(unittest.TestCase):
    def test_prepare_freezes_exact_packets_and_cost(self):
        history = history_fixture()
        self.addCleanup(history.tmp.cleanup)
        prepared = run_plugin_prepare(history, stage="A")

        self.assertEqual(6, prepared["planned_scout_calls"])
        self.assertEqual(3, prepared["planned_domain_reducer_calls"])
        self.assertEqual(["design", "work", "write"], prepared["planned_domains"])
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


if __name__ == "__main__":
    unittest.main()
