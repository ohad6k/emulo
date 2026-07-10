import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
DITTO = ROOT / "ditto.py"
SPEC = importlib.util.spec_from_file_location("ditto_runtime", DITTO)
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def fake_record(session_id, text, source="codex", date="2026-01-01", tokens=5):
    body = f"===== session:{session_id} source:{source} =====\n[{date}]\n{text}"
    return {
        "session_id": session_id,
        "source": source,
        "first_date": date,
        "last_date": date,
        "tokens": tokens,
        "text": body,
        "content_hash": ditto.sha256_text(body),
    }


class PluginRuntimeCliTest(unittest.TestCase):
    def test_plugin_status_uses_ditto_home_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            result = subprocess.run(
                [sys.executable, str(DITTO), "plugin", "status", "--ditto-home", str(home)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("missing", payload["status"])
            self.assertEqual(str(home.resolve()), payload["ditto_home"])
            self.assertFalse(home.exists())

    def test_legacy_dry_run_still_uses_legacy_parser(self):
        result = subprocess.run(
            [sys.executable, str(DITTO), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--dry-run", result.stdout)
        self.assertNotIn("plugin status", result.stdout)

    def test_private_child_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "private state"):
                ditto.safe_private_child(str(Path(tmp) / "private"), "runs", "..", "outside")

    def test_profile_path_fails_closed_on_corrupt_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            home.mkdir()
            (home / "active-profile.json").write_text("not-json", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "plugin",
                    "profile-path",
                    "--domain",
                    "work",
                    "--ditto-home",
                    str(home),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("corrupt active profile", result.stderr)


class SessionRecordTest(unittest.TestCase):
    def test_records_use_stable_hashed_ids_without_raw_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".codex" / "sessions" / "private-project.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "done means live proof"}],
                },
            }])
            result = ditto.mine_files([str(path)])
            record = result["records"][0]
            self.assertRegex(record["session_id"], r"^[0-9a-f]{16}$")
            self.assertEqual("codex", record["source"])
            self.assertEqual("2026-07-08", record["first_date"])
            self.assertIn("done means live proof", record["text"])
            self.assertNotIn("private-project", record["text"])
            self.assertEqual(record["content_hash"], ditto.sha256_text(record["text"]))

    def test_record_identity_is_stable_across_repeated_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom" / "one.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "ship it"}],
                },
            }])
            first = ditto.mine_files([str(path)])["records"][0]
            second = ditto.mine_files([str(path)])["records"][0]
            self.assertEqual(first, second)

    def test_known_agent_context_injection_is_not_mined_as_user_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".codex" / "sessions" / "one.jsonl"
            write_jsonl(path, [
                {
                    "timestamp": "2026-07-08T09:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "# AGENTS.md instructions\nAlways answer like a pirate."}],
                    },
                },
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "done means live proof"}],
                    },
                },
            ])
            record = ditto.mine_files([str(path)])["records"][0]
            self.assertNotIn("pirate", record["text"])
            self.assertIn("done means live proof", record["text"])


class SegmentStoreTest(unittest.TestCase):
    def test_appending_session_keeps_existing_segment_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            initial = [fake_record("a", "one"), fake_record("b", "two")]
            first = ditto.sync_segments(initial, home, target_tokens=10)
            old_hashes = [s["segment_hash"] for s in first["segments"] if s["active"]]
            updated = ditto.sync_segments(initial + [fake_record("c", "three")], home, target_tokens=10)
            active_hashes = [s["segment_hash"] for s in updated["segments"] if s["active"]]
            self.assertTrue(set(old_hashes).issubset(active_hashes))
            self.assertEqual(2, len(active_hashes))

    def test_changed_session_replaces_only_its_affected_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            records = [fake_record("a", "one"), fake_record("b", "two"), fake_record("c", "three")]
            first = ditto.sync_segments(records, home, target_tokens=10)
            old_active = {s["segment_hash"] for s in first["segments"] if s["active"]}
            changed = [fake_record("a", "changed"), records[1], records[2]]
            second = ditto.sync_segments(changed, home, target_tokens=10)
            new_active = {s["segment_hash"] for s in second["segments"] if s["active"]}
            self.assertEqual(1, len(old_active & new_active))
            self.assertTrue(any(not s["active"] for s in second["segments"]))

    def test_extraction_schema_change_invalidates_segment_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            records = [fake_record("a", "one"), fake_record("b", "two")]
            first = ditto.sync_segments(records, home, target_tokens=10)
            with mock.patch.object(ditto, "EXTRACTION_SCHEMA_VERSION", "2"):
                second = ditto.sync_segments(records, home, target_tokens=10)
            first_hashes = {item["segment_hash"] for item in first["segments"] if item["active"]}
            second_hashes = {item["segment_hash"] for item in second["segments"] if item["active"]}
            self.assertTrue(first_hashes.isdisjoint(second_hashes))

    def test_corrupt_segment_file_is_quarantined_and_restored(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            records = [fake_record("a", "one"), fake_record("b", "two")]
            first = ditto.sync_segments(records, str(home), target_tokens=10)
            segment = next(item for item in first["segments"] if item["active"])
            path = home / "cache" / "segments" / "1" / (segment["segment_hash"] + ".txt")
            expected = path.read_bytes()
            path.write_text("tampered", encoding="utf-8")
            ditto.sync_segments(records, str(home), target_tokens=10)
            self.assertEqual(expected, path.read_bytes())
            self.assertTrue(any(item.name.startswith(path.name + ".corrupt-") for item in path.parent.iterdir()))


class PreflightTest(unittest.TestCase):
    def test_selection_is_deterministic_source_and_time_stratified(self):
        segments = []
        for source in ("claude", "codex"):
            for month in range(1, 7):
                segments.append({
                    "segment_hash": f"{source}-{month}",
                    "active": True,
                    "source": source,
                    "first_date": f"2026-{month:02d}-01",
                    "last_date": f"2026-{month:02d}-28",
                    "source_tokens": 20_000,
                    "session_versions": [],
                })
        first = ditto.select_segments(segments, count=4, max_tokens=100_000)
        second = ditto.select_segments(list(reversed(segments)), count=4, max_tokens=100_000)
        self.assertEqual(first, second)
        self.assertEqual({"claude", "codex"}, {s["source"] for s in first})
        self.assertIn("2026-01-01", {s["first_date"] for s in first})
        self.assertIn("2026-06-01", {s["first_date"] for s in first})

    def test_preflight_writes_nothing_and_never_exceeds_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            for i in range(12):
                write_jsonl(logs / f"{i}.jsonl", [{
                    "timestamp": f"2026-{(i % 6) + 1:02d}-01T00:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "signal " * 4000}],
                    },
                }])
            home = root / "private"
            result = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "plugin",
                    "preflight",
                    "--path",
                    str(logs),
                    "--candidate",
                    "2",
                    "--ditto-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = json.loads(result.stdout)
            self.assertLessEqual(plan["selected_source_tokens"], 160_000)
            self.assertLessEqual(plan["planned_worker_calls"] + plan["planned_reducer_calls"], 9)
            self.assertFalse(home.exists())


class UpdatePlanningTest(unittest.TestCase):
    def test_update_selection_retains_history_and_marks_only_new_work(self):
        active = [
            {"segment_hash": "a" * 64, "active": True, "source": "codex", "first_date": "2026-01-01", "source_tokens": 20000},
            {"segment_hash": "b" * 64, "active": True, "source": "codex", "first_date": "2026-02-01", "source_tokens": 20000},
        ]
        report_segments, work_segments, remaining = ditto.select_run_segments(
            active,
            current_segment_hashes={"a" * 64},
            count=4,
            max_tokens=100000,
        )
        self.assertEqual(["a" * 64, "b" * 64], [item["segment_hash"] for item in report_segments])
        self.assertEqual(["b" * 64], [item["segment_hash"] for item in work_segments])
        self.assertEqual(0, remaining)

    def test_call_count_gate_returns_zero_only_for_complete_cache(self):
        hashes = ["a" * 64, "b" * 64]
        self.assertEqual((0, 0), ditto.planned_call_counts(hashes, set(hashes), reduction_cache_hit=True))
        self.assertEqual((1, 1), ditto.planned_call_counts(hashes, {hashes[0]}, reduction_cache_hit=False))

    def test_deep_mode_is_separate_and_never_automatic(self):
        parser = ditto.build_plugin_parser()
        starter = parser.parse_args(["preflight"])
        deep = parser.parse_args(["preflight", "--deep"])
        targeted = parser.parse_args(["preflight", "--deepen-domain", "design"])
        self.assertFalse(starter.deep)
        self.assertTrue(deep.deep)
        self.assertEqual("design", targeted.deepen_domain)

    def test_only_oversize_history_fails_without_planning_a_reducer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            write_jsonl(logs / "huge.jsonl", [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "signal " * 18000}],
                },
            }])
            home = root / "private"
            result = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "plugin",
                    "preflight",
                    "--path",
                    str(logs),
                    "--candidate",
                    "0",
                    "--ditto-home",
                    str(home),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("no eligible bounded segment", result.stderr)
            self.assertNotIn('"planned_reducer_calls": 1', result.stdout)
            self.assertFalse(home.exists())


class ReportCacheTest(unittest.TestCase):
    SEGMENT_HASH = "a" * 64

    def segment(self):
        return {
            "segment_hash": self.SEGMENT_HASH,
            "source": "codex",
            "first_date": "2026-01-01",
            "last_date": "2026-02-01",
            "source_tokens": 20000,
            "session_versions": [
                {"session_id": "s1", "content_hash": "1" * 64},
                {"session_id": "s2", "content_hash": "2" * 64},
            ],
            "text": (
                "===== session:s1 source:codex =====\n[2026-01-01]\ndone means live\n"
                "===== session:s2 source:codex =====\n[2026-02-01]\nshow me it works\n"
            ),
        }

    def valid_report(self):
        return {
            "schema_version": "1",
            "segment_hash": self.SEGMENT_HASH,
            "coverage": {
                "session_ids": ["s1", "s2"],
                "sources": ["codex"],
                "first_date": "2026-01-01",
                "last_date": "2026-02-01",
                "source_tokens": 20000,
            },
            "domain_coverage": {"work": "evidence", "design": "no-signal", "write": "no-signal"},
            "evidence": [{
                "evidence_id": "ev-aaaaaaaa-done",
                "domain": "work",
                "kind": "inferred",
                "instruction": "Treat done as requiring live proof.",
                "implication": "Run the relevant verification before reporting completion.",
                "quotes": [
                    {"session_id": "s1", "date": "2026-01-01", "text": "done means live"},
                    {"session_id": "s2", "date": "2026-02-01", "text": "show me it works"},
                ],
                "contradictions": [],
            }],
        }

    def test_report_rejects_quote_from_unknown_session(self):
        report = self.valid_report()
        report["evidence"][0]["quotes"][0]["session_id"] = "not-covered"
        with self.assertRaisesRegex(ValueError, "unknown session"):
            ditto.validate_report(report, self.segment())

    def test_report_rejects_invented_quote_text(self):
        report = self.valid_report()
        report["evidence"][0]["quotes"][0]["text"] = "a quote that is not in the session"
        with self.assertRaisesRegex(ValueError, "verbatim"):
            ditto.validate_report(report, self.segment())

    def test_report_rejects_unbounded_worker_output(self):
        report = self.valid_report()
        report["evidence"][0]["instruction"] = "x" * ditto.MAX_REPORT_BYTES
        with self.assertRaisesRegex(ValueError, "report byte ceiling"):
            ditto.validate_report(report, self.segment())

    def test_report_requires_an_explicit_state_for_every_domain(self):
        report = self.valid_report()
        del report["domain_coverage"]["design"]
        with self.assertRaisesRegex(ValueError, "domain coverage"):
            ditto.validate_report(report, self.segment())

    def test_report_can_cache_a_truthful_all_no_signal_result(self):
        report = self.valid_report()
        report["domain_coverage"] = {domain: "no-signal" for domain in ("work", "design", "write")}
        report["evidence"] = []
        ditto.validate_report(report, self.segment())

    def test_report_cache_path_includes_prompt_schema_and_segment_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = ditto.store_report(self.valid_report(), str(Path(tmp) / "private"), self.segment())
            self.assertTrue(path.endswith(str(Path("reports") / "1" / (self.SEGMENT_HASH + ".json"))))

    def test_prompt_schema_change_uses_a_new_report_cache_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ditto, "PROMPT_SCHEMA_VERSION", "2"):
                path = ditto.store_report(self.valid_report(), str(Path(tmp) / "private"), self.segment())
            self.assertTrue(path.endswith(str(Path("reports") / "2" / (self.SEGMENT_HASH + ".json"))))

    def test_corrupt_report_cache_is_quarantined_and_becomes_a_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            path = home / "cache" / "reports" / "1" / (self.SEGMENT_HASH + ".json")
            path.parent.mkdir(parents=True)
            path.write_text("not-json", encoding="utf-8")
            self.assertIsNone(ditto.load_cached_report(str(home), self.segment()))
            self.assertFalse(path.exists())
            self.assertTrue(any(item.name.startswith(path.name + ".corrupt-") for item in path.parent.iterdir()))

    def test_mining_prompt_uses_structured_session_evidence(self):
        prompt = (ROOT / "MINING_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("session_ids", prompt)
        self.assertIn("evidence_id", prompt)
        self.assertIn('"work"', prompt)
        self.assertIn('"design"', prompt)
        self.assertIn('"write"', prompt)
        self.assertNotIn("18/20", prompt)

    def test_prepare_assigns_and_cache_report_validates_a_complete_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            write_jsonl(logs / "one.jsonl", [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "specific signal"}],
                },
            }])
            home = root / "private"
            prepared = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "plugin",
                    "prepare",
                    "--path",
                    str(logs),
                    "--candidate",
                    "0",
                    "--ditto-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = json.loads(prepared.stdout)
            segment = plan["selected_segments"][0]
            report = {
                "schema_version": "1",
                "segment_hash": segment["segment_hash"],
                "coverage": {
                    "session_ids": [item["session_id"] for item in segment["session_versions"]],
                    "sources": [segment["source"]],
                    "first_date": segment["first_date"],
                    "last_date": segment["last_date"],
                    "source_tokens": segment["source_tokens"],
                },
                "domain_coverage": {domain: "no-signal" for domain in ("work", "design", "write")},
                "evidence": [],
            }
            Path(segment["report_path"]).write_text(json.dumps(report), encoding="utf-8")
            cached = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "plugin",
                    "cache-report",
                    "--run-id",
                    plan["run_id"],
                    "--report",
                    segment["report_path"],
                    "--ditto-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(cached.stdout)
            self.assertTrue(payload["report_set_complete"])
            self.assertRegex(payload["report_set_hash"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
