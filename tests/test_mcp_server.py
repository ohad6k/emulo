import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from emulo_autopilot import contracts
from emulo_autopilot.store import AutopilotStore
from tests.autopilot_helpers import candidate_fixture, decision_fixture


ROOT = Path(__file__).resolve().parents[1]
EMULO = ROOT / "emulo.py"
SPEC = importlib.util.spec_from_file_location("emulo_mcp", EMULO)
emulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulo)


def rpc(**kw):
    body = {"jsonrpc": "2.0"}
    body.update(kw)
    return body


class McpHandlerTest(unittest.TestCase):
    HOME = "/tmp/emulo-home-unused"

    @staticmethod
    def _approve(store, statement, domain="work"):
        candidate = candidate_fixture(statement=statement)
        candidate["domain"] = domain
        candidate["candidate_id"] = contracts.candidate_identity(candidate)
        store.put_candidate(candidate)
        store.append_decision(decision_fixture(candidate["candidate_id"]))
        return candidate

    @staticmethod
    def _fake_profile(home, domain="work"):
        work = Path(home) / "you.md"
        work.write_text("BASE WORK PROFILE", encoding="utf-8")
        paths = [str(work)]
        if domain != "work":
            selected = Path(home) / ("you-" + domain + ".md")
            selected.write_text("BASE " + domain.upper() + " PROFILE", encoding="utf-8")
            paths.append(str(selected))
        return {
            "status": "active",
            "domain": domain,
            "profile_version": "abcd1234abcd1234abcd",
            "paths": paths,
        }

    def test_initialize_echoes_a_supported_protocol_and_names_the_server(self):
        response = emulo.mcp_handle(
            rpc(id=1, method="initialize", params={"protocolVersion": "2025-03-26"}),
            self.HOME,
        )
        self.assertEqual("2025-03-26", response["result"]["protocolVersion"])
        self.assertEqual("emulo", response["result"]["serverInfo"]["name"])
        self.assertIn("tools", response["result"]["capabilities"])

    def test_initialize_falls_back_when_client_sends_no_version(self):
        response = emulo.mcp_handle(rpc(id=1, method="initialize", params={}), self.HOME)
        self.assertEqual(emulo.MCP_PROTOCOL_VERSION, response["result"]["protocolVersion"])

    def test_a_notification_is_never_answered(self):
        self.assertIsNone(emulo.mcp_handle(rpc(method="notifications/initialized"), self.HOME))

    def test_tools_list_exposes_exactly_the_profile_loader(self):
        response = emulo.mcp_handle(rpc(id=2, method="tools/list"), self.HOME)
        tools = response["result"]["tools"]
        self.assertEqual(["load_emulo_profile"], [tool["name"] for tool in tools])
        self.assertEqual(
            ["design", "video", "work", "write"],
            tools[0]["inputSchema"]["properties"]["domain"]["enum"],
        )

    def test_tool_description_names_every_domain_the_enum_accepts(self):
        # A model picks the domain from this sentence; a value it never reads
        # about is one it never asks for.
        tool = emulo.mcp_handle(rpc(id=2, method="tools/list"), self.HOME)["result"]["tools"][0]
        for domain in tool["inputSchema"]["properties"]["domain"]["enum"]:
            self.assertIn(f"'{domain}'", tool["description"], domain)

    def test_tool_description_says_what_it_returns_not_what_it_does_for_the_user(self):
        # Every MCP client shows this string to its model. It used to promise
        # "so you act like them instead of starting cold", which no published
        # test supports, so it now only says what the tool returns.
        tool = emulo.mcp_handle(rpc(id=2, method="tools/list"), self.HOME)["result"]["tools"][0]
        description = tool["description"].lower()
        for claim in ("act like", "starting cold", "cold start", "work like"):
            self.assertNotIn(claim, description)
        self.assertIn("mined emulo profile", description)

    def test_unknown_method_is_method_not_found(self):
        response = emulo.mcp_handle(rpc(id=3, method="does/notexist"), self.HOME)
        self.assertEqual(-32601, response["error"]["code"])

    def test_unknown_tool_is_invalid_params(self):
        response = emulo.mcp_handle(
            rpc(id=4, method="tools/call", params={"name": "nope", "arguments": {}}),
            self.HOME,
        )
        self.assertEqual(-32602, response["error"]["code"])

    def test_tools_call_returns_concatenated_profile_text_when_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "you.md"
            work.write_text("done means live proof", encoding="utf-8")
            design = Path(tmp) / "you-designer.md"
            design.write_text("flat black and white, no purple", encoding="utf-8")
            fake = {
                "status": "active",
                "domain": "design",
                "profile_version": "abcd1234abcd1234abcd",
                "paths": [str(work), str(design)],
            }
            with mock.patch.object(emulo, "resolve_profile_paths", return_value=fake):
                response = emulo.mcp_handle(
                    rpc(
                        id=5,
                        method="tools/call",
                        params={"name": "load_emulo_profile", "arguments": {"domain": "design"}},
                    ),
                    tmp,
                )
        self.assertFalse(response["result"]["isError"])
        text = response["result"]["content"][0]["text"]
        self.assertIn("done means live proof", text)
        self.assertIn("no purple", text)
        self.assertIn("abcd1234abcd1234abcd", text)

    def test_tools_call_without_a_profile_returns_the_recovery_instruction(self):
        with mock.patch.object(
            emulo,
            "resolve_profile_paths",
            side_effect=ValueError("no active Emulo profile; run emulo"),
        ):
            response = emulo.mcp_handle(
                rpc(id=6, method="tools/call", params={"name": "load_emulo_profile", "arguments": {}}),
                self.HOME,
            )
        self.assertTrue(response["result"]["isError"])
        self.assertIn("run emulo", response["result"]["content"][0]["text"])

    def test_tools_call_defaults_to_the_work_domain(self):
        captured = {}

        def fake_resolve(home, domain):
            captured["domain"] = domain
            raise ValueError("no active Emulo profile; run emulo")

        with mock.patch.object(emulo, "resolve_profile_paths", side_effect=fake_resolve):
            emulo.mcp_handle(
                rpc(id=7, method="tools/call", params={"name": "load_emulo_profile", "arguments": {}}),
                self.HOME,
            )
        self.assertEqual("work", captured["domain"])

    def test_absent_autopilot_head_preserves_profile_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = self._fake_profile(tmp)
            with mock.patch.object(emulo, "resolve_profile_paths", return_value=fake):
                self.assertEqual(
                    "# Emulo work profile (version abcd1234abcd1234abcd)\n\n"
                    "BASE WORK PROFILE",
                    emulo.mcp_load_profile_text(tmp, "work"),
                )

    def test_mcp_appends_only_the_selected_autopilot_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AutopilotStore(tmp)
            work = self._approve(store, "Use live proof for release claims.")
            design = self._approve(
                store, "Change visual structure before polish.", domain="design"
            )
            store.activate(
                [work["candidate_id"], design["candidate_id"]],
                "2026-07-16T13:00:00Z",
            )
            fake = self._fake_profile(tmp)
            with mock.patch.object(emulo, "resolve_profile_paths", return_value=fake):
                text = emulo.mcp_load_profile_text(tmp, "work")
        self.assertIn("BASE WORK PROFILE", text)
        self.assertIn("Use live proof for release claims.", text)
        self.assertNotIn("Change visual structure before polish.", text)
        self.assertGreater(
            text.index("Use live proof for release claims."),
            text.index("BASE WORK PROFILE"),
        )

    def test_mcp_reflects_append_only_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AutopilotStore(tmp)
            first_candidate = self._approve(store, "Keep the stable rule.")
            first = store.activate(
                [first_candidate["candidate_id"]], "2026-07-16T13:00:00Z"
            )
            second_candidate = self._approve(store, "Try the experimental rule.")
            store.activate(
                [second_candidate["candidate_id"]], "2026-07-16T13:01:00Z"
            )
            store.rollback(first["generation_id"], "2026-07-16T13:02:00Z")
            fake = self._fake_profile(tmp)
            with mock.patch.object(emulo, "resolve_profile_paths", return_value=fake):
                text = emulo.mcp_load_profile_text(tmp, "work")
        self.assertIn("Keep the stable rule.", text)
        self.assertNotIn("Try the experimental rule.", text)

    def test_corrupt_autopilot_state_returns_error_without_partial_profile(self):
        for corruption in ("head", "manifest", "artifact", "extra"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as tmp:
                store = AutopilotStore(tmp)
                candidate = self._approve(store, "Keep this reviewed rule.")
                generation = store.activate(
                    [candidate["candidate_id"]], "2026-07-16T13:00:00Z"
                )
                root = (
                    Path(tmp)
                    / "autopilot"
                    / "generations"
                    / generation["generation_id"]
                )
                if corruption == "head":
                    (Path(tmp) / "autopilot" / "head.json").write_text(
                        "{}\n", encoding="utf-8"
                    )
                elif corruption == "manifest":
                    (root / "generation.json").write_text("{}\n", encoding="utf-8")
                elif corruption == "artifact":
                    (root / "work.md").write_text("tampered\n", encoding="utf-8")
                else:
                    (root / "extra.txt").write_text("unexpected", encoding="utf-8")
                fake = self._fake_profile(tmp)
                with mock.patch.object(emulo, "resolve_profile_paths", return_value=fake):
                    response = emulo.mcp_handle(
                        rpc(
                            id=8,
                            method="tools/call",
                            params={
                                "name": "load_emulo_profile",
                                "arguments": {"domain": "work"},
                            },
                        ),
                        tmp,
                    )
                self.assertTrue(response["result"]["isError"])
                error = response["result"]["content"][0]["text"]
                self.assertIn("corrupt Autopilot overlay", error)
                self.assertNotIn("BASE WORK PROFILE", error)

    def test_one_file_overlay_reader_needs_no_autopilot_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            store = AutopilotStore(str(home))
            candidate = self._approve(store, "One-file MCP keeps this rule.")
            store.activate(
                [candidate["candidate_id"]], "2026-07-16T13:00:00Z"
            )
            isolated = Path(tmp) / "emulo.py"
            isolated.write_bytes(EMULO.read_bytes())
            script = (
                "import importlib.util;"
                "s=importlib.util.spec_from_file_location('isolated_emulo',r'{}');"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                "print(m.load_autopilot_overlay(r'{}','work'))"
            ).format(isolated, home)
            result = subprocess.run(
                [sys.executable, "-I", "-c", script],
                cwd=tmp,
                env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("One-file MCP keeps this rule.", result.stdout)


class McpStdioTest(unittest.TestCase):
    def run_server(self, messages, home):
        stdin = "".join(json.dumps(message) + "\n" for message in messages)
        result = subprocess.run(
            [sys.executable, str(EMULO), "mcp", "--emulo-home", home],
            input=stdin,
            capture_output=True,
            text=True,
            check=True,
        )
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

    def test_a_real_stdio_session_initializes_lists_and_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            responses = self.run_server(
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-06-18"}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                     "params": {"name": "load_emulo_profile", "arguments": {"domain": "work"}}},
                ],
                tmp,
            )
        # the notification produces no response, so exactly three replies come back
        self.assertEqual([1, 2, 3], [message["id"] for message in responses])
        self.assertEqual("emulo", responses[0]["result"]["serverInfo"]["name"])
        self.assertEqual("load_emulo_profile", responses[1]["result"]["tools"][0]["name"])
        self.assertTrue(responses[2]["result"]["isError"])
        self.assertIn("run emulo", responses[2]["result"]["content"][0]["text"])

    def test_a_malformed_line_is_reported_and_the_loop_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdin = "not json\n" + json.dumps({"jsonrpc": "2.0", "id": 9, "method": "ping"}) + "\n"
            result = subprocess.run(
                [sys.executable, str(EMULO), "mcp", "--emulo-home", tmp],
                input=stdin,
                capture_output=True,
                text=True,
                check=True,
            )
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(-32700, responses[0]["error"]["code"])
        self.assertEqual({}, responses[1]["result"])


if __name__ == "__main__":
    unittest.main()
