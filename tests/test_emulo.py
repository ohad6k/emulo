import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMULO = ROOT / "emulo.py"


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


class EmuloCliTest(unittest.TestCase):
    def test_dry_run_counts_without_writing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "emulo-out"
            write_jsonl(logs / "codex.jsonl", [
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "done means live proof. token=abc123456789"}],
                    },
                },
                {
                    "timestamp": "2026-07-08T10:01:00Z",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"text": "ignore assistant text"}],
                    },
                },
            ])
            write_jsonl(logs / "claude.jsonl", [
                {
                    "timestamp": "2026-07-08T11:00:00Z",
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": "do not touch files outside the task",
                    },
                },
            ])

            result = subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out), "--dry-run"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("dry run: no files written", result.stdout)
            self.assertIn("jsonl files: 2", result.stdout)
            self.assertIn("sessions: 2", result.stdout)
            self.assertIn("your messages: 2", result.stdout)
            self.assertIn("messages with secrets/PII redacted: 1", result.stdout)
            self.assertFalse(out.exists())

    def test_run_writes_redacted_corpus_and_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "emulo-out"
            write_jsonl(logs / "codex.jsonl", [
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "api_key=supersecret123 do the smallest fix"}],
                    },
                },
                {
                    "timestamp": "2026-07-08T10:01:00Z",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"text": "assistant output should not appear"}],
                    },
                },
            ])

            result = subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out), "--chunks", "1"],
                check=True,
                capture_output=True,
                text=True,
            )

            corpus = (out / "you-corpus.txt").read_text(encoding="utf-8")
            chunk = (out / "chunks" / "chunk-01.txt").read_text(encoding="utf-8")

            self.assertIn("sessions: 1", result.stdout)
            self.assertIn("api_key=[REDACTED]", corpus)
            self.assertNotIn("supersecret123", corpus)
            self.assertNotIn("assistant output should not appear", corpus)
            self.assertEqual(corpus, chunk)

    def test_run_me_names_only_files_that_exist(self):
        # The old handoff told users to paste MINING_PROMPT.md, which pip never
        # installed. Assert every path RUN_ME.md points the agent at is real.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "emulo-out"
            write_jsonl(logs / "codex.jsonl", [
                {
                    "timestamp": f"2026-07-0{i}T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": f"message number {i} " + ("x" * 400)}],
                    },
                }
                for i in range(1, 8)
            ])

            result = subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out), "--chunks", "3"],
                check=True,
                capture_output=True,
                text=True,
            )

            run_me_path = out / "RUN_ME.md"
            self.assertTrue(run_me_path.exists(), "RUN_ME.md was not written")
            run_me = run_me_path.read_text(encoding="utf-8")

            chunks = sorted((out / "chunks").glob("chunk-*.txt"))
            self.assertTrue(chunks, "no chunks were written")

            referenced = [
                line.strip()[2:]
                for line in run_me.splitlines()
                if line.startswith("- ") and line.strip().endswith(".txt")
            ]
            self.assertEqual(len(chunks), len(referenced))
            for path in referenced:
                self.assertTrue(Path(path).exists(), f"RUN_ME.md points at a missing file: {path}")

            # it must be self-contained: never send the user hunting for a repo file
            self.assertNotIn("MINING_PROMPT", run_me)
            self.assertIn("you.md", run_me)
            self.assertIn("read", result.stdout)
            self.assertIn("RUN_ME.md", result.stdout)

    def test_redacts_bare_and_is_form_credentials_without_eating_prose(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("emulo", EMULO)
        emulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(emulo)

        for secret in ("the password is Hunter2!x", "psk Tr0ub4dor3",
                       "wifi key abc12345", "password: sekritvalue1"):
            self.assertIn("[REDACTED]", emulo.redact(secret), secret)

        for prose in ("the password is wrong", "password reset email",
                      "my token store", "passwd prompt appeared",
                      "boarding pass QF12345", "pwd C:/Users/me/project1"):
            self.assertNotIn("[REDACTED]", emulo.redact(prose), prose)

    def test_redacts_anthropic_google_and_openai_project_keys(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("emulo", EMULO)
        emulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(emulo)

        body = "Ab3_dE-fGh" * 9
        anthropic = "sk-" + "ant-api03-" + body + "AA"
        oauth = "sk-" + "ant-oat01-" + body
        google = "AI" + "za" + ("SyD3_x-9QwErTyUiOpAsDfGhJkLzXcVbN12")[:35]
        openai_project = "sk-" + "proj-" + body + "_T3BlbkFJ" + body
        self.assertEqual(39, len(google))

        for text, label, secret in (
            (f"use {anthropic} for the eval", "[ANTHROPIC_KEY]", anthropic),
            (f"ANTHROPIC_API_KEY {oauth}", "[ANTHROPIC_KEY]", oauth),
            (f"maps key {google}.", "[GOOGLE_API_KEY]", google),
            (f"?key={google}&v=3", "[GOOGLE_API_KEY]", google),
            (f"old key {openai_project} rotated", "[OPENAI_KEY]", openai_project),
        ):
            out = emulo.redact(text)
            self.assertIn(label, out, text)
            self.assertNotIn(secret, out)
            self.assertNotIn(body[:10], out, out)

        for prose in ("the AIza prefix marks a Google key",
                      "AIzaShort-123 is not a key",
                      "AIza" + "x" * 20 + " too short",
                      "sk-ant is the prefix Anthropic uses"):
            self.assertEqual(prose, emulo.redact(prose), prose)

    def test_redacts_passwords_in_connection_urls(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("emulo", EMULO)
        emulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(emulo)

        exact = {
            "postgres://app:s3cr3tpw@localhost:5432/db":
                "postgres://app:[REDACTED]@localhost:5432/db",
            "DATABASE_URL=postgresql://app:hunter2@localhost/app_dev":
                "DATABASE_URL=postgresql://app:[REDACTED]@localhost/app_dev",
            "mysql://root:rootpw@dbhost:3306/shop":
                "mysql://root:[REDACTED]@dbhost:3306/shop",
            "redis://:redispass@localhost:6379/0":
                "redis://:[REDACTED]@localhost:6379/0",
            "amqp://guest:guestpw@rabbit:5672/":
                "amqp://guest:[REDACTED]@rabbit:5672/",
            "jdbc:postgresql://svc:pw1@localhost/x":
                "jdbc:postgresql://svc:[REDACTED]@localhost/x",
            "postgres://u:p@ss@localhost/db":
                "postgres://u:[REDACTED]@localhost/db",
        }
        for text, expected in exact.items():
            self.assertEqual(expected, emulo.redact(text), text)

        for text, secret in (
            ("mongodb+srv://admin:M0ng0!pass@cluster0.abcde.mongodb.net/test", "M0ng0!pass"),
            ("git clone https://deploy:tok3nvalue@git.example.com/repo.git", "tok3nvalue"),
            ("postgres://app:pw@10.0.0.5/db", ":pw@"),
        ):
            out = emulo.redact(text)
            self.assertNotIn(secret, out, out)
            self.assertIn("[REDACTED]", out, out)

        for keep in ("https://example.com/path?q=1",
                     "http://localhost:3000/api",
                     "postgres://app@localhost/db",
                     "ssh://deploy@build-box:22/srv/repo",
                     "see http://host:8080/a:b for details",
                     "https://host:8443/path?u=a@b"):
            self.assertEqual(keep, emulo.redact(keep), keep)

        # a port followed by a query or fragment holding an @ is not a password:
        # the address in it is still an email, and the port stays
        self.assertEqual("http://localhost:3000?next=[EMAIL]",
                         emulo.redact("http://localhost:3000?next=a@b.com"))
        self.assertEqual("http://localhost:3000#to=[EMAIL]",
                         emulo.redact("http://localhost:3000#to=a@b.com"))

    def test_connection_url_rule_stays_linear_on_long_tokens(self):
        import importlib.util
        import time
        spec = importlib.util.spec_from_file_location("emulo", EMULO)
        emulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(emulo)
        # Only the URL rule: the scheme is anchored to the start of a word so a
        # long pasted token is scanned once, not once per character.
        blob = "a" * 200_000 + " " + "b://" + "c" * 200_000 + " x://u:" + "p" * 200_000
        started = time.perf_counter()
        emulo.CONNECTION_URL_PASSWORD.sub(emulo.CONNECTION_URL_REPLACEMENT, blob)
        self.assertLess(time.perf_counter() - started, 2.0)

    def test_redaction_count_is_labelled_as_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            write_jsonl(logs / "codex.jsonl", [{
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {"type": "message", "role": "user",
                            "content": [{"text": "mail a@example.com and b@example.com token=abc123456789"}]},
            }])
            result = subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--dry-run"],
                check=True, capture_output=True, text=True, cwd=tmp,
            )
            # three items redacted in one message: the count is messages, and says so
            self.assertIn("messages with secrets/PII redacted: 1", result.stdout)

    def test_phone_redaction_does_not_eat_dates_versions_or_part_numbers(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("emulo", EMULO)
        emulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(emulo)

        for keep in ("2026-06-14", "07/09/2026", "v0.8.0", "0x04", "4.6 V",
                     "acer-15-6-aspire-lite-n4500", "18 payments of 150",
                     "PEX 543 777 2996", "129424534", "1,656 sessions"):
            self.assertNotIn("[PHONE]", emulo.redact(keep), keep)

        for phone in ("07 5477 4500", "+61 400 123 456", "0400123456",
                      "052-1234567", "0521234567", "03-1234567",
                      "+972 52-123-4567", "+14155552671",
                      "reach me at +972 52-123-4567.",
                      "(02) 9876 5432", "(03) 123-4567", "+1 (415) 555-2671",
                      "07700 900123", "+49 151 12345678"):
            self.assertIn("[PHONE]", emulo.redact(phone), phone)

    def test_install_codex_writes_skill_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test profile\n---\n\n# profile\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "codex",
                    "--home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            dest = home / ".codex" / "skills" / "you" / "SKILL.md"
            self.assertEqual(profile.read_text(encoding="utf-8"), dest.read_text(encoding="utf-8"))

            second = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "codex",
                    "--home",
                    str(home),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("destination already exists", second.stdout)

    def test_install_agents_appends_marked_block_without_deleting_existing_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            agents = repo / "AGENTS.md"
            agents.write_text("# existing rules\n\nkeep this\n", encoding="utf-8")
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test profile\n---\n\n# profile\n\n- done means live\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "agents",
                    "--repo",
                    str(repo),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            installed = agents.read_text(encoding="utf-8")
            self.assertIn("keep this", installed)
            self.assertIn("<!-- emulo profile:start -->", installed)
            self.assertIn("- done means live", installed)
            self.assertNotIn("name: you", installed)

    def test_install_opencode_writes_global_rules_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test profile\n---\n\n# profile\n\n- done means live\n",
                encoding="utf-8",
            )
            cmd = [sys.executable, str(EMULO), "--install", str(profile),
                   "--target", "opencode", "--home", str(home)]

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            dest = home / ".config" / "opencode" / "AGENTS.md"
            installed = dest.read_text(encoding="utf-8")
            self.assertIn("<!-- emulo profile:start -->", installed)
            self.assertIn("- done means live", installed)
            self.assertNotIn("name: you", installed)

            # a second install without --yes refuses to replace the block
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(0, second.returncode)

            # --yes replaces the block and keeps unrelated content
            dest.write_text("# my own rules\n\n" + installed, encoding="utf-8")
            subprocess.run(cmd + ["--yes"], check=True, capture_output=True, text=True)
            replaced = dest.read_text(encoding="utf-8")
            self.assertIn("# my own rules", replaced)
            self.assertEqual(1, replaced.count("<!-- emulo profile:start -->"))

    def test_install_cursor_writes_mdc_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test profile\n---\n\n# profile\n\n- keep answers short\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "cursor",
                    "--repo",
                    str(repo),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            rule = (repo / ".cursor" / "rules" / "you.mdc").read_text(encoding="utf-8")
            self.assertTrue(rule.startswith("---\ndescription: emulo user profile\nalwaysApply: true\n---"))
            self.assertIn("- keep answers short", rule)
            self.assertNotIn("name: you", rule)

    def test_dedupe_collapses_repeated_long_messages_keeps_short(self):
        long_spec = "PLEASE IMPLEMENT THIS PLAN: " + ("do the thing carefully. " * 20)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "emulo-out"
            rows = []
            # same long spec pasted into three sessions + short "yes" repeated three times
            for i in range(3):
                rows.append({
                    "timestamp": f"2026-07-0{i+1}T10:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": long_spec}]},
                })
                rows.append({
                    "timestamp": f"2026-07-0{i+1}T10:01:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "yes"}]},
                })
            write_jsonl(logs / "codex.jsonl", rows)

            result = subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out), "--chunks", "1"],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("duplicate specs/rules collapsed: 2", result.stdout)
            corpus = (out / "you-corpus.txt").read_text(encoding="utf-8")
            self.assertEqual(corpus.count("PLEASE IMPLEMENT THIS PLAN"), 1)   # long spec kept once
            self.assertEqual(corpus.count("\nyes"), 3)                        # every short "yes" kept

            # --no-dedupe keeps all three copies
            out2 = root / "emulo-out2"
            subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out2), "--chunks", "1", "--no-dedupe"],
                check=True, capture_output=True, text=True,
            )
            corpus2 = (out2 / "you-corpus.txt").read_text(encoding="utf-8")
            self.assertEqual(corpus2.count("PLEASE IMPLEMENT THIS PLAN"), 3)

    def test_run_writes_stats_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "emulo-out"
            write_jsonl(logs / "codex.jsonl", [
                {
                    "timestamp": "2025-11-02T10:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "first message"}]},
                },
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "last message"}]},
                },
            ])

            subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out), "--chunks", "1"],
                check=True,
                capture_output=True,
                text=True,
            )

            stats = json.loads((out / "stats.json").read_text(encoding="utf-8"))
            self.assertEqual(stats["sessions"], 1)
            self.assertEqual(stats["messages"], 2)
            self.assertEqual(stats["first_date"], "2025-11-02")
            self.assertEqual(stats["last_date"], "2026-07-08")

    def test_card_renders_terminal_and_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "emulo-out"
            out.mkdir()
            (out / "card.json").write_text(json.dumps({
                "archetype": "Proof-First Builder",
                "laws": [
                    {"text": "done means it runs live", "count": "18/20"},
                    {"text": "fix the one thing", "count": "15/20"},
                ],
                "truth": "asks the agent to explain his own system back",
            }), encoding="utf-8")
            (out / "stats.json").write_text(json.dumps({
                "sessions": 1656,
                "messages": 7678,
                "tokens": 2950000,
                "first_date": "2025-11-02",
                "last_date": "2026-07-08",
            }), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(EMULO), "--card", "--out", str(out), "--no-open"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("PROOF-FIRST BUILDER", result.stdout)
            self.assertIn("18/20", result.stdout)
            self.assertIn("1,656 sessions", result.stdout)
            self.assertIn("9 months", result.stdout)
            html = (out / "card.html").read_text(encoding="utf-8")
            self.assertIn("Proof-First Builder", html)
            self.assertIn("18/20", html)
            self.assertIn("3.0M", html)
            self.assertIn("&rarr;", html)
            self.assertNotIn("�", html)

    def test_card_without_card_json_fails_with_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "emulo-out"
            out.mkdir()
            result = subprocess.run(
                [sys.executable, str(EMULO), "--card", "--out", str(out), "--no-open"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no card found", result.stdout)
            # The hint must match the flow that exists: RUN_ME.md writes you.md
            # and no card; the plugin pipeline is what writes card.json.
            self.assertNotIn("MINING_PROMPT", result.stdout)
            self.assertIn("RUN_ME.md", result.stdout)
            self.assertIn("emulo plugin status", result.stdout)
            self.assertIn("emulo --card <card_path>", result.stdout)

    def test_card_hint_names_a_command_that_prints_the_card_path(self):
        # The hint sends the user to `emulo plugin status`; that command must
        # exist and answer with a status even when no profile is active.
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(EMULO), "plugin", "status", "--emulo-home", str(Path(tmp) / "emulo-home")],
                capture_output=True, text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("missing", json.loads(result.stdout)["status"])

    def test_zero_valid_sessions_fails_without_writing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            logs.mkdir()
            (logs / "bad.jsonl").write_text("{}\nnot-json\n", encoding="utf-8")
            out = root / "out"
            result = subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no valid user sessions", result.stderr)
            self.assertFalse(out.exists())

    def test_install_rejects_substring_frontmatter_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "bad.md"
            profile.write_text(
                "---\nnotname: you\nnotdescription: wrong\n---\nbody\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "codex",
                    "--home",
                    str(root / "home"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exact name and description", result.stderr)

    def test_smaller_rerun_removes_stale_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            for i in range(12):
                write_jsonl(logs / f"session-{i}.jsonl", [{
                    "timestamp": f"2026-07-{i + 1:02d}T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "x" * 1000 + str(i)}],
                    },
                }])
            out = root / "out"
            subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out), "--chunks", "6"],
                check=True,
            )
            subprocess.run(
                [sys.executable, str(EMULO), "--path", str(logs), "--out", str(out), "--chunks", "1"],
                check=True,
            )
            self.assertEqual(["chunk-01.txt"], sorted(p.name for p in (out / "chunks").iterdir()))

    def test_partial_marked_block_fails_without_modifying_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            agents = repo / "AGENTS.md"
            original = "# rules\n\n<!-- emulo profile:start -->\nbroken\n"
            agents.write_text(original, encoding="utf-8")
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test\n---\nbody\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "agents",
                    "--repo",
                    str(repo),
                    "--yes",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(original, agents.read_text(encoding="utf-8"))

    def test_agents_install_preserves_existing_crlf_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            agents = repo / "AGENTS.md"
            agents.write_bytes(b"# keep\r\n\r\n")
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test\n---\nbody\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "agents",
                    "--repo",
                    str(repo),
                ],
                check=True,
            )
            installed = agents.read_bytes()
            self.assertNotIn(b"\n", installed.replace(b"\r\n", b""))

    def test_hebrew_install_path_survives_cp1252_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test\n---\nbody\n",
                encoding="utf-8",
            )
            home = root / "שלום"
            env = dict(os.environ, PYTHONIOENCODING="cp1252")
            result = subprocess.run(
                [
                    sys.executable,
                    str(EMULO),
                    "--install",
                    str(profile),
                    "--target",
                    "codex",
                    "--home",
                    str(home),
                    "--yes",
                ],
                capture_output=True,
                env=env,
            )
            self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", errors="replace"))
            self.assertIn("שלום", result.stdout.decode("utf-8"))
            self.assertTrue((home / ".codex" / "skills" / "you" / "SKILL.md").exists())


def isolated_home_env(home):
    """Point HOME (every OS) and the log roots at one directory."""
    env = dict(os.environ)
    for name in ("HOME", "USERPROFILE", "CODEX_HOME", "XDG_DATA_HOME"):
        env[name] = str(home)
    env.pop("HOMEDRIVE", None)
    env.pop("HOMEPATH", None)
    return env


# A you.md written the way RUN_ME.md asks for it: domains, instruction,
# implication, a dated verbatim quote. RUN_ME.md never mentions frontmatter,
# so an agent following it writes none.
RUN_ME_PROFILE = """# You

## work

- **Prove it ran before calling it done.**
  Implication: run the change and read the output before reporting success.
  Receipt (2026-07-08): "done means live proof, not code existing"

## write

- **No filler in replies.**
  Implication: answer first, cut the preamble. Aimed at: the agent.
  Receipt (2026-07-09): "skip the intro and give me the answer"
"""


class RunMeInstallPathTest(unittest.TestCase):
    def _mine(self, work, home):
        logs = work / "logs"
        write_jsonl(logs / "codex.jsonl", [
            {
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {"type": "message", "role": "user",
                            "content": [{"text": "done means live proof, not code existing"}]},
            },
            {
                "timestamp": "2026-07-09T10:00:00Z",
                "payload": {"type": "message", "role": "user",
                            "content": [{"text": "skip the intro and give me the answer"}]},
            },
        ])
        subprocess.run(
            [sys.executable, str(EMULO), "--path", str(logs), "--chunks", "1"],
            check=True, capture_output=True, text=True, cwd=work, env=isolated_home_env(home),
        )
        return (work / "emulo-out" / "RUN_ME.md").read_text(encoding="utf-8")

    def test_you_md_written_as_run_me_says_installs_with_every_printed_command(self):
        import shlex
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            home = Path(tmp) / "home"
            work.mkdir()
            home.mkdir()
            run_me = self._mine(work, home)

            self.assertIn("emulo-out/you.md", run_me)
            self.assertNotIn("frontmatter", run_me)
            (work / "emulo-out" / "you.md").write_text(RUN_ME_PROFILE, encoding="utf-8")

            printed = [line.strip() for line in run_me.splitlines()
                       if line.strip().startswith("emulo --install ")]
            self.assertEqual(3, len(printed), run_me)
            # RUN_ME.md also lists every target by name; each must work the same way.
            listed = [line for line in run_me.splitlines() if line.startswith("Targets: ")]
            self.assertEqual(1, len(listed))
            targets = [t.strip() for t in listed[0][len("Targets: "):].rstrip(".").split(",")]
            self.assertEqual(["claude", "codex", "cursor", "agents", "gemini", "opencode"], targets)
            commands = list(printed)
            for target in targets:
                if not any(f"--target {target}" in c for c in printed):
                    commands.append(f"emulo --install emulo-out/you.md --target {target} --repo .")

            for command in commands:
                argv = shlex.split(command)
                self.assertEqual("emulo", argv[0])
                proc = subprocess.run(
                    [sys.executable, str(EMULO), *argv[1:]],
                    capture_output=True, text=True, cwd=work, env=isolated_home_env(home),
                )
                self.assertEqual(0, proc.returncode, f"{command}\n{proc.stdout}{proc.stderr}")
                self.assertIn("installed:", proc.stdout, command)

            body = RUN_ME_PROFILE.strip()
            for skill in (home / ".claude" / "skills" / "you" / "SKILL.md",
                          home / ".codex" / "skills" / "you" / "SKILL.md"):
                installed = skill.read_text(encoding="utf-8")
                self.assertTrue(installed.startswith("---\nname: you\ndescription: "), installed[:80])
                self.assertIn(body, installed)
            for block_file in (work / "AGENTS.md", work / "GEMINI.md",
                               home / ".config" / "opencode" / "AGENTS.md"):
                self.assertIn(body, block_file.read_text(encoding="utf-8"))
            self.assertIn(body, (work / ".cursor" / "rules" / "you.mdc").read_text(encoding="utf-8"))
            # the user's own file is never rewritten
            self.assertEqual(RUN_ME_PROFILE, (work / "emulo-out" / "you.md").read_text(encoding="utf-8"))

    def test_run_me_leads_with_the_install_routes_a_host_was_seen_to_load(self):
        # A host-by-host load test on 2026-09-25 found AGENTS.md reaches the model in
        # Codex and OpenCode, while the Claude Code skill is not reliably opened on its
        # own and has to be called with /you. RUN_ME.md used to lead with the claude
        # skill and promise the agent "behaves like someone who already knows them".
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            home = Path(tmp) / "home"
            work.mkdir()
            home.mkdir()
            run_me = self._mine(work, home)
            printed = [line.strip() for line in run_me.splitlines()
                       if line.strip().startswith("emulo --install ")]
            self.assertEqual("emulo --install emulo-out/you.md --target agents --repo .", printed[0])
            # backticked, so emulo-out/you.md cannot satisfy it
            self.assertIn("type `/you`", run_me)
            self.assertNotIn("already knows them", run_me)
            self.assertNotIn("confidently wrong", run_me)

    def test_run_me_asks_before_installing_and_warns_that_agents_md_is_shared(self):
        # The agent runs these installs itself, so the person may never see them.
        # --target agents --repo . appends the whole profile, verbatim dated quotes
        # included, to AGENTS.md in whatever folder the agent is in, and AGENTS.md is
        # usually committed. Nothing may be installed before the person says which
        # agents they use, and the agents target needs the folder confirmed first.
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            home = Path(tmp) / "home"
            work.mkdir()
            home.mkdir()
            # collapse the template's line wrapping so a phrase is found wherever it breaks
            run_me = " ".join(self._mine(work, home).split())
            first_command = run_me.index("emulo --install ")
            ask = run_me.find("Ask the person which coding agents they use")
            self.assertNotEqual(-1, ask, run_me)
            self.assertLess(ask, first_command)
            self.assertIn("Run only the installs for those agents", run_me)
            self.assertIn("never all of them", run_me)
            confirm = run_me.find("get their yes before you run it")
            self.assertNotEqual(-1, confirm, run_me)
            self.assertLess(confirm, first_command)
            warning = run_me.find("usually committed and shared")
            self.assertNotEqual(-1, warning, run_me)
            self.assertLess(warning, first_command)
            self.assertIn("quotes from their own sessions", run_me)
            self.assertIn("out of version control", run_me)
            # the old line presented every command as something to run
            self.assertNotIn("then install it into the agents this person actually uses:", run_me)

    def test_skill_install_without_frontmatter_says_it_added_one(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("emulo", EMULO)
        emulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(emulo)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "you.md"
            profile.write_text(RUN_ME_PROFILE, encoding="utf-8")
            for target in ("claude", "codex"):
                proc = subprocess.run(
                    [sys.executable, str(EMULO), "--install", str(profile), "--target", target,
                     "--home", str(root / "home")],
                    capture_output=True, text=True,
                )
                self.assertEqual(0, proc.returncode, proc.stderr)
                self.assertIn("no frontmatter", proc.stdout)
                self.assertIn("name: you", proc.stdout)
            installed = (root / "home" / ".claude" / "skills" / "you" / "SKILL.md").read_text(encoding="utf-8")
            fields = emulo.parse_frontmatter(installed)
            self.assertEqual("you", fields["name"])
            self.assertTrue(emulo.has_skill_frontmatter(installed, expected_name="you"))

    def test_frontmatter_after_blank_lines_or_indent_is_used_not_stacked(self):
        # The check used to run on the raw text: a blank first line, or an
        # indented marker, made a real block read as "no frontmatter", so the
        # default was stacked on top and the user's own block left in the body.
        own = "---\nname: ohad\ndescription: my desc\n---\n# body\n"
        cases = {
            "blank first line": "\n" + own,
            "whitespace-only first lines": "  \n\t\r\n" + own,
            "indented marker": "  " + own,
        }
        for label, text in cases.items():
            for target in ("claude", "codex"):
                with self.subTest(case=label, target=target), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    profile = root / "you.md"
                    profile.write_bytes(text.encode("utf-8"))
                    proc = subprocess.run(
                        [sys.executable, str(EMULO), "--install", str(profile), "--target", target,
                         "--home", str(root / "home")],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(0, proc.returncode, proc.stderr)
                    self.assertNotIn("no frontmatter", proc.stdout)
                    installed = (root / "home" / f".{target}" / "skills" / "you" / "SKILL.md").read_text(encoding="utf-8")
                    self.assertEqual(own, installed)

    def test_frontmatter_after_blank_lines_is_stripped_from_block_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "you.md"
            profile.write_text("\n  ---\nname: ohad\ndescription: my desc\n---\n# body\n", encoding="utf-8")
            subprocess.run(
                [sys.executable, str(EMULO), "--install", str(profile), "--target", "agents", "--repo", str(root)],
                check=True, capture_output=True, text=True,
            )
            installed = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("# body", installed)
            self.assertNotIn("name: ohad", installed)
            self.assertNotIn("---", installed)

    def test_existing_frontmatter_with_utf8_bom_is_kept_not_doubled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "you.md"
            text = "---\nname: you\ndescription: my own words\n---\n\n# profile\n"
            profile.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
            proc = subprocess.run(
                [sys.executable, str(EMULO), "--install", str(profile), "--target", "claude",
                 "--home", str(root / "home")],
                capture_output=True, text=True,
            )
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertNotIn("no frontmatter", proc.stdout)
            installed = (root / "home" / ".claude" / "skills" / "you" / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual(text, installed)


class EmptyEnvVarTest(unittest.TestCase):
    def test_empty_codex_home_and_xdg_data_home_mean_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            work = Path(tmp) / "work"
            home.mkdir()
            env = isolated_home_env(home)
            env["CODEX_HOME"] = ""
            env["XDG_DATA_HOME"] = ""
            proc = subprocess.run(
                [sys.executable, "-c",
                 "import importlib.util, json, sys;"
                 "spec = importlib.util.spec_from_file_location('emulo', sys.argv[1]);"
                 "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m);"
                 "print(json.dumps({'codex': m.SOURCES['codex'], 'opencode': m.SOURCES['opencode']}))",
                 str(EMULO)],
                capture_output=True, text=True, env=env, check=True,
            )
            roots = json.loads(proc.stdout)
            self.assertEqual(
                [os.path.join(str(home), ".codex", "sessions"),
                 os.path.join(str(home), ".codex", "archived_sessions")],
                roots["codex"],
            )
            self.assertEqual([os.path.join(str(home), ".local", "share", "opencode")], roots["opencode"])

            # the real CLI must not mine folders that happen to sit in the working directory
            for decoy in ("sessions", "archived_sessions"):
                write_jsonl(work / decoy / "decoy.jsonl", [{
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {"type": "message", "role": "user",
                                "content": [{"text": "a message from the working directory"}]},
                }])
            (work / "opencode").mkdir()
            dry = subprocess.run(
                [sys.executable, str(EMULO), "--source", "codex", "--dry-run"],
                capture_output=True, text=True, env=env, cwd=work,
            )
            self.assertEqual(1, dry.returncode, dry.stdout + dry.stderr)
            self.assertIn("no session logs found", dry.stdout)
            self.assertIn(os.path.join(str(home), ".codex", "sessions"), dry.stdout)


if __name__ == "__main__":
    unittest.main()
