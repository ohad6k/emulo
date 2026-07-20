import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
EMULO = ROOT / "emulo.py"
SPEC = importlib.util.spec_from_file_location("emulo_runtime", EMULO)
emulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulo)


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
        "content_hash": emulo.sha256_text(body),
    }


class PluginRuntimeCliTest(unittest.TestCase):
    def test_plugin_status_uses_emulo_home_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            result = subprocess.run(
                [sys.executable, str(EMULO), "plugin", "status", "--emulo-home", str(home)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("missing", payload["status"])
            self.assertEqual(str(home.resolve()), payload["emulo_home"])
            self.assertFalse(home.exists())

    def test_legacy_dry_run_still_uses_legacy_parser(self):
        result = subprocess.run(
            [sys.executable, str(EMULO), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--dry-run", result.stdout)
        self.assertNotIn("plugin status", result.stdout)

    def test_private_child_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "private state"):
                emulo.safe_private_child(str(Path(tmp) / "private"), "runs", "..", "outside")

    def test_profile_path_fails_closed_on_corrupt_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            home.mkdir()
            (home / "active-profile.json").write_text("not-json", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "plugin",
                    "profile-path",
                    "--domain",
                    "work",
                    "--emulo-home",
                    str(home),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("corrupt active profile", result.stderr)


class SessionRecordTest(unittest.TestCase):
    def test_assistant_lines_are_rejected_before_json_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one.jsonl"
            assistant = {
                "timestamp": "2026-07-08T09:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"text": "large irrelevant output " * 1000}],
                },
            }
            user = {
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "done means live proof"}],
                },
            }
            write_jsonl(path, [assistant, user])
            with mock.patch.object(emulo.json, "loads", wraps=json.loads) as decoder:
                messages = emulo.user_messages(str(path))
            self.assertEqual(1, decoder.call_count)
            self.assertEqual([("2026-07-08", "done means live proof")], messages)

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
            result = emulo.mine_files([str(path)])
            record = result["records"][0]
            self.assertRegex(record["session_id"], r"^[0-9a-f]{16}$")
            self.assertEqual("codex", record["source"])
            self.assertEqual("2026-07-08", record["first_date"])
            self.assertIn("done means live proof", record["text"])
            self.assertNotIn("private-project", record["text"])
            self.assertEqual(record["content_hash"], emulo.sha256_text(record["text"]))

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
            first = emulo.mine_files([str(path)])["records"][0]
            second = emulo.mine_files([str(path)])["records"][0]
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
            record = emulo.mine_files([str(path)])["records"][0]
            self.assertNotIn("pirate", record["text"])
            self.assertIn("done means live proof", record["text"])


class SegmentStoreTest(unittest.TestCase):
    def test_appending_session_keeps_existing_segment_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            initial = [fake_record("a", "one"), fake_record("b", "two")]
            first = emulo.sync_segments(initial, home, target_tokens=10)
            old_hashes = [s["segment_hash"] for s in first["segments"] if s["active"]]
            updated = emulo.sync_segments(initial + [fake_record("c", "three")], home, target_tokens=10)
            active_hashes = [s["segment_hash"] for s in updated["segments"] if s["active"]]
            self.assertTrue(set(old_hashes).issubset(active_hashes))
            self.assertEqual(2, len(active_hashes))

    def test_changed_session_replaces_only_its_affected_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            records = [fake_record("a", "one"), fake_record("b", "two"), fake_record("c", "three")]
            first = emulo.sync_segments(records, home, target_tokens=10)
            old_active = {s["segment_hash"] for s in first["segments"] if s["active"]}
            changed = [fake_record("a", "changed"), records[1], records[2]]
            second = emulo.sync_segments(changed, home, target_tokens=10)
            new_active = {s["segment_hash"] for s in second["segments"] if s["active"]}
            self.assertEqual(1, len(old_active & new_active))
            self.assertTrue(any(not s["active"] for s in second["segments"]))

    def test_extraction_schema_change_invalidates_segment_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            records = [fake_record("a", "one"), fake_record("b", "two")]
            first = emulo.sync_segments(records, home, target_tokens=10)
            with mock.patch.object(emulo, "EXTRACTION_SCHEMA_VERSION", "999-test"):
                second = emulo.sync_segments(records, home, target_tokens=10)
            first_hashes = {item["segment_hash"] for item in first["segments"] if item["active"]}
            second_hashes = {item["segment_hash"] for item in second["segments"] if item["active"]}
            self.assertTrue(first_hashes.isdisjoint(second_hashes))

    def test_corrupt_segment_file_is_quarantined_and_restored(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            records = [fake_record("a", "one"), fake_record("b", "two")]
            first = emulo.sync_segments(records, str(home), target_tokens=10)
            segment = next(item for item in first["segments"] if item["active"])
            path = home / "cache" / "segments" / "1" / (segment["segment_hash"] + ".txt")
            expected = path.read_bytes()
            path.write_text("tampered", encoding="utf-8")
            emulo.sync_segments(records, str(home), target_tokens=10)
            self.assertEqual(expected, path.read_bytes())
            self.assertTrue(any(item.name.startswith(path.name + ".corrupt-") for item in path.parent.iterdir()))


class PreflightTest(unittest.TestCase):
    def test_prepare_requires_the_exact_approved_preflight_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            write_jsonl(logs / "one.jsonl", [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "type": "message", "role": "user",
                    "content": [{"text": "specific working preference"}],
                },
            }])
            home = root / "private"
            result = subprocess.run(
                [
                    sys.executable, str(EMULO), "plugin", "prepare",
                    "--path", str(logs), "--preview", "--emulo-home", str(home),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("approved preflight hash", result.stderr)
            self.assertFalse(home.exists())

    def test_no_flag_preflight_is_the_full_history_quality_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            write_jsonl(logs / "one.jsonl", [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "specific working preference"}],
                },
            }])
            result = subprocess.run(
                [sys.executable, str(EMULO), "plugin", "preflight", "--path", str(logs)],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = json.loads(result.stdout)
            self.assertEqual("full", plan["mode"])
            self.assertEqual("full_profile", plan["profile_scope"])
            self.assertTrue(plan["quality_default"])
            self.assertIsNone(plan["candidate_index"])

    def test_preview_is_explicitly_labeled_as_a_starter_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            write_jsonl(logs / "one.jsonl", [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "specific working preference"}],
                },
            }])
            result = subprocess.run(
                [
                    sys.executable, str(EMULO), "plugin", "preflight",
                    "--path", str(logs), "--preview",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = json.loads(result.stdout)
            self.assertEqual("quick_preview", plan["mode"])
            self.assertEqual("starter_profile", plan["profile_scope"])
            self.assertFalse(plan["quality_default"])
            self.assertEqual(emulo.DEFAULT_CANDIDATE_INDEX, plan["candidate_index"])
            self.assertEqual(
                "Quick preview creates a starter profile from selected history, not the full profile.",
                plan["notice"],
            )

    def test_candidate_ladder_reuses_one_segmentation_and_only_expands_selection(self):
        configs = [emulo.candidate_config(index) for index in range(3)]
        self.assertEqual({config["segment_tokens"] for config in configs}, {25_000})
        self.assertEqual([config["segments"] for config in configs], [4, 6, 8])

        segments = []
        for source in ("claude", "codex"):
            for month in range(1, 7):
                segments.append({
                    "segment_hash": f"{source}-{month}",
                    "active": True,
                    "source": source,
                    "first_date": f"2026-{month:02d}-01",
                    "last_date": f"2026-{month:02d}-28",
                    "source_tokens": 24_000,
                    "session_versions": [],
                })
        selections = [
            {
                segment["segment_hash"]
                for segment in emulo.select_segments(
                    segments,
                    count=config["segments"],
                    max_tokens=emulo.STARTER_MAX_SOURCE_TOKENS,
                )
            }
            for config in configs
        ]
        self.assertLess(selections[0], selections[1])
        self.assertTrue(selections[1].issubset(selections[2]))

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
        first = emulo.select_segments(segments, count=4, max_tokens=100_000)
        second = emulo.select_segments(list(reversed(segments)), count=4, max_tokens=100_000)
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
                    str(EMULO),
                    "plugin",
                    "preflight",
                    "--path",
                    str(logs),
                    "--candidate",
                    "2",
                    "--emulo-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "EMULO_ALLOW_LEGACY_CANDIDATES": "1"},
            )
            plan = json.loads(result.stdout)
            self.assertLessEqual(plan["selected_source_tokens"], 160_000)
            self.assertLessEqual(plan["planned_worker_calls"] + plan["planned_reducer_calls"], 9)
            self.assertFalse(home.exists())


class UpdatePlanningTest(unittest.TestCase):
    def test_empty_reduction_cache_directory_is_not_a_zero_call_hit(self):
        segment = {
            "segment_hash": "a" * 64,
            "active": True,
            "source": "codex",
            "first_date": "2026-01-01",
            "last_date": "2026-01-01",
            "source_tokens": 10,
            "session_versions": [],
        }
        result = {"records": [], "sessions": 1, "chars": 40}
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            corrupt = home / "cache" / "reductions" / "2" / ("b" * 64)
            corrupt.mkdir(parents=True)
            with mock.patch.object(emulo, "sync_segments", return_value={"segments": [segment]}), \
                    mock.patch.object(emulo, "load_cached_report", return_value={}), \
                    mock.patch.object(emulo, "compute_report_set_hash", return_value="b" * 64):
                plan = emulo.build_deep_preflight(result, str(home))

        self.assertEqual(0, plan["planned_worker_calls"])
        self.assertEqual(1, plan["planned_reducer_calls"])

    def test_incomplete_reduction_manifest_is_not_a_zero_call_hit(self):
        segment = {
            "segment_hash": "a" * 64, "active": True, "source": "codex",
            "first_date": "2026-01-01", "last_date": "2026-01-01",
            "source_tokens": 10, "session_versions": [],
        }
        result = {"records": [], "sessions": 1, "chars": 40}
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            corrupt = home / "cache" / "reductions" / "2" / ("b" * 64)
            corrupt.mkdir(parents=True)
            (corrupt / "manifest.json").write_text(json.dumps({
                "schema_version": "1", "profile_id": "default",
                "profile_version": "c" * 20, "report_set_hash": "b" * 64,
                "domains": {}, "files": {},
            }), encoding="utf-8")
            with mock.patch.object(emulo, "sync_segments", return_value={"segments": [segment]}), \
                    mock.patch.object(emulo, "load_cached_report", return_value={}), \
                    mock.patch.object(emulo, "compute_report_set_hash", return_value="b" * 64):
                plan = emulo.build_deep_preflight(result, str(home))

        self.assertEqual(1, plan["planned_reducer_calls"])

    def test_full_history_preflight_is_zero_call_when_reports_and_reduction_are_cached(self):
        segment = {
            "segment_hash": "a" * 64,
            "active": True,
            "source": "codex",
            "first_date": "2026-01-01",
            "last_date": "2026-01-01",
            "source_tokens": 10,
            "session_versions": [],
        }
        result = {"records": [], "sessions": 1, "chars": 40}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(emulo, "sync_segments", return_value={"segments": [segment]}), \
                mock.patch.object(emulo, "load_cached_report", return_value={}), \
                mock.patch.object(emulo, "compute_report_set_hash", return_value="b" * 64), \
                mock.patch.object(emulo, "reduction_cache_is_valid", return_value=True):
            plan = emulo.build_deep_preflight(result, str(Path(tmp) / "private"))

        self.assertEqual("b" * 64, plan["report_set_hash"])
        self.assertEqual(0, plan["planned_worker_calls"])
        self.assertEqual(0, plan["planned_reducer_calls"])

    def test_update_selection_retains_history_and_marks_only_new_work(self):
        active = [
            {"segment_hash": "a" * 64, "active": True, "source": "codex", "first_date": "2026-01-01", "source_tokens": 20000},
            {"segment_hash": "b" * 64, "active": True, "source": "codex", "first_date": "2026-02-01", "source_tokens": 20000},
        ]
        report_segments, work_segments, remaining = emulo.select_run_segments(
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
        self.assertEqual((0, 0), emulo.planned_call_counts(hashes, set(hashes), reduction_cache_hit=True))
        self.assertEqual((1, 1), emulo.planned_call_counts(hashes, {hashes[0]}, reduction_cache_hit=False))

    def test_full_mode_is_default_and_preview_is_explicit(self):
        parser = emulo.build_plugin_parser()
        full = parser.parse_args(["preflight"])
        preview = parser.parse_args(["preflight", "--preview"])
        deep = parser.parse_args(["preflight", "--deep"])
        targeted = parser.parse_args(["preflight", "--deepen-domain", "design"])
        self.assertFalse(full.preview)
        self.assertTrue(preview.preview)
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
                    str(EMULO),
                    "plugin",
                    "preflight",
                    "--path",
                    str(logs),
                    "--candidate",
                    "0",
                    "--emulo-home",
                    str(home),
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "EMULO_ALLOW_LEGACY_CANDIDATES": "1"},
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
            "schema_version": "2",
            "segment_hash": self.SEGMENT_HASH,
            "coverage": {
                "session_ids": ["s1", "s2"],
                "sources": ["codex"],
                "first_date": "2026-01-01",
                "last_date": "2026-02-01",
                "source_tokens": 20000,
            },
            "domain_coverage": {"work": "evidence", "design": "no-signal", "write": "no-signal", "video": "no-signal"},
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
            emulo.validate_report(report, self.segment())

    def test_report_rejects_invented_quote_text(self):
        report = self.valid_report()
        report["evidence"][0]["quotes"][0]["text"] = "a quote that is not in the session"
        with self.assertRaisesRegex(ValueError, "verbatim"):
            emulo.validate_report(report, self.segment())

    def test_report_rejects_unbounded_worker_output(self):
        report = self.valid_report()
        report["evidence"][0]["instruction"] = "x" * emulo.MAX_REPORT_BYTES
        with self.assertRaisesRegex(ValueError, "report byte ceiling"):
            emulo.validate_report(report, self.segment())

    def test_report_requires_an_explicit_state_for_every_domain(self):
        report = self.valid_report()
        del report["domain_coverage"]["design"]
        with self.assertRaisesRegex(ValueError, "domain coverage"):
            emulo.validate_report(report, self.segment())

    def test_report_can_cache_a_truthful_all_no_signal_result(self):
        report = self.valid_report()
        report["domain_coverage"] = {domain: "no-signal" for domain in ("work", "design", "write", "video")}
        report["evidence"] = []
        emulo.validate_report(report, self.segment())

    def test_report_cache_path_includes_prompt_schema_and_segment_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = emulo.store_report(self.valid_report(), str(Path(tmp) / "private"), self.segment())
            self.assertTrue(path.endswith(str(Path("reports") / "2" / (self.SEGMENT_HASH + ".json"))))

    def test_prompt_schema_change_uses_a_new_report_cache_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(emulo, "PROMPT_SCHEMA_VERSION", "3"):
                path = emulo.store_report(self.valid_report(), str(Path(tmp) / "private"), self.segment())
            self.assertTrue(path.endswith(str(Path("reports") / "3" / (self.SEGMENT_HASH + ".json"))))

    def write_evidence(self, register="casual"):
        item = {
            "evidence_id": "ev-aaaaaaaa-voice",
            "domain": "write",
            "kind": "inferred",
            "instruction": "Prove claims with live output.",
            "implication": "Attach the real result before claiming the copy works.",
            "quotes": [
                {"session_id": "s1", "date": "2026-01-01", "text": "done means live"},
                {"session_id": "s2", "date": "2026-02-01", "text": "show me it works"},
            ],
            "contradictions": [],
        }
        if register is not None:
            item["register"] = register
        return item

    def test_write_evidence_requires_a_register(self):
        report = self.valid_report()
        report["domain_coverage"] = {"work": "no-signal", "design": "no-signal", "write": "evidence", "video": "no-signal"}
        report["evidence"] = [self.write_evidence(register=None)]
        with self.assertRaisesRegex(ValueError, "register"):
            emulo.validate_report(report, self.segment())

    def test_write_evidence_rejects_an_unknown_register(self):
        report = self.valid_report()
        report["domain_coverage"] = {"work": "no-signal", "design": "no-signal", "write": "evidence", "video": "no-signal"}
        report["evidence"] = [self.write_evidence(register="boss")]
        with self.assertRaisesRegex(ValueError, "register"):
            emulo.validate_report(report, self.segment())

    def test_register_is_rejected_outside_the_write_domain(self):
        report = self.valid_report()
        report["evidence"][0]["register"] = "casual"
        with self.assertRaisesRegex(ValueError, "only valid on write"):
            emulo.validate_report(report, self.segment())

    def test_write_evidence_accepts_a_valid_register(self):
        report = self.valid_report()
        report["domain_coverage"] = {"work": "no-signal", "design": "no-signal", "write": "evidence", "video": "no-signal"}
        report["evidence"] = [self.write_evidence(register="professional")]
        emulo.validate_report(report, self.segment())

    def test_corrupt_report_cache_is_quarantined_and_becomes_a_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            path = home / "cache" / "reports" / "2" / (self.SEGMENT_HASH + ".json")
            path.parent.mkdir(parents=True)
            path.write_text("not-json", encoding="utf-8")
            self.assertIsNone(emulo.load_cached_report(str(home), self.segment()))
            self.assertFalse(path.exists())
            self.assertTrue(any(item.name.startswith(path.name + ".corrupt-") for item in path.parent.iterdir()))

    def test_structurally_invalid_report_cache_is_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            path = home / "cache" / "reports" / "2" / (self.SEGMENT_HASH + ".json")
            path.parent.mkdir(parents=True)
            path.write_text("[]", encoding="utf-8")

            self.assertIsNone(emulo.load_cached_report(str(home), self.segment()))

            self.assertFalse(path.exists())
            self.assertTrue(any(item.name.startswith(path.name + ".corrupt-") for item in path.parent.iterdir()))

    def test_mining_prompt_uses_structured_session_evidence(self):
        prompt = (ROOT / "MINING_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("session_ids", prompt)
        self.assertIn("evidence_id", prompt)
        self.assertIn('"work"', prompt)
        self.assertIn('"design"', prompt)
        self.assertIn('"write"', prompt)
        self.assertIn("exact containing `[YYYY-MM-DD]` message header", prompt)
        self.assertIn("plugin validate-report", prompt)
        self.assertIn("The truth must sting", prompt)
        self.assertIn("real bottleneck is trust recovery", prompt)
        self.assertNotIn("18/20", prompt)

    def test_mining_prompt_mines_repeated_procedures(self):
        prompt = (ROOT / "MINING_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("repeated procedure", prompt)
        self.assertIn("ordered steps", prompt)
        self.assertIn("## Workflow", prompt)
        self.assertIn("same rule shape and the same evidence bar", prompt)

    def test_validate_report_command_is_read_only(self):
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
            preflight = subprocess.run(
                [
                    sys.executable, str(EMULO), "plugin", "preflight", "--path", str(logs),
                    "--candidate", "0", "--emulo-home", str(home),
                ],
                check=True, capture_output=True, text=True,
                env={**os.environ, "EMULO_ALLOW_LEGACY_CANDIDATES": "1"},
            )
            approval_hash = json.loads(preflight.stdout)["approval_hash"]
            prepared = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "plugin",
                    "prepare",
                    "--path",
                    str(logs),
                    "--candidate",
                    "0",
                    "--approved-plan-hash",
                    approval_hash,
                    "--emulo-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "EMULO_ALLOW_LEGACY_CANDIDATES": "1"},
            )
            plan = json.loads(prepared.stdout)
            segment = plan["selected_segments"][0]
            report = {
                "schema_version": "2",
                "segment_hash": segment["segment_hash"],
                "coverage": {
                    "session_ids": [item["session_id"] for item in segment["session_versions"]],
                    "sources": [segment["source"]],
                    "first_date": segment["first_date"],
                    "last_date": segment["last_date"],
                    "source_tokens": segment["source_tokens"],
                },
                "domain_coverage": {domain: "no-signal" for domain in ("work", "design", "write", "video")},
                "evidence": [],
            }
            Path(segment["report_path"]).write_text(json.dumps(report), encoding="utf-8")

            validated = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "plugin",
                    "validate-report",
                    "--run-id",
                    plan["run_id"],
                    "--report",
                    segment["report_path"],
                    "--emulo-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(validated.stdout)
            self.assertEqual(payload["status"], "valid")
            self.assertEqual(payload["segment_hash"], segment["segment_hash"])
            self.assertFalse((home / "cache" / "reports" / "2" / (segment["segment_hash"] + ".json")).exists())
            stored_plan = json.loads((Path(plan["run_dir"]) / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(stored_plan["report_paths"], [])
            self.assertIsNone(stored_plan["report_set_hash"])

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
            preflight = subprocess.run(
                [
                    sys.executable, str(EMULO), "plugin", "preflight", "--path", str(logs),
                    "--candidate", "0", "--emulo-home", str(home),
                ],
                check=True, capture_output=True, text=True,
                env={**os.environ, "EMULO_ALLOW_LEGACY_CANDIDATES": "1"},
            )
            approval_hash = json.loads(preflight.stdout)["approval_hash"]
            prepared = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "plugin",
                    "prepare",
                    "--path",
                    str(logs),
                    "--candidate",
                    "0",
                    "--approved-plan-hash",
                    approval_hash,
                    "--emulo-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "EMULO_ALLOW_LEGACY_CANDIDATES": "1"},
            )
            plan = json.loads(prepared.stdout)
            segment = plan["selected_segments"][0]
            report = {
                "schema_version": "2",
                "segment_hash": segment["segment_hash"],
                "coverage": {
                    "session_ids": [item["session_id"] for item in segment["session_versions"]],
                    "sources": [segment["source"]],
                    "first_date": segment["first_date"],
                    "last_date": segment["last_date"],
                    "source_tokens": segment["source_tokens"],
                },
                "domain_coverage": {domain: "no-signal" for domain in ("work", "design", "write", "video")},
                "evidence": [],
            }
            Path(segment["report_path"]).write_text(json.dumps(report), encoding="utf-8")
            cached = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "plugin",
                    "cache-report",
                    "--run-id",
                    plan["run_id"],
                    "--report",
                    segment["report_path"],
                    "--emulo-home",
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
