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
SPEC = importlib.util.spec_from_file_location("ditto_mcp", DITTO)
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


def rpc(**kw):
    body = {"jsonrpc": "2.0"}
    body.update(kw)
    return body


class McpHandlerTest(unittest.TestCase):
    HOME = "/tmp/ditto-home-unused"

    def test_initialize_echoes_a_supported_protocol_and_names_the_server(self):
        response = ditto.mcp_handle(
            rpc(id=1, method="initialize", params={"protocolVersion": "2025-03-26"}),
            self.HOME,
        )
        self.assertEqual("2025-03-26", response["result"]["protocolVersion"])
        self.assertEqual("ditto", response["result"]["serverInfo"]["name"])
        self.assertIn("tools", response["result"]["capabilities"])

    def test_initialize_falls_back_when_client_sends_no_version(self):
        response = ditto.mcp_handle(rpc(id=1, method="initialize", params={}), self.HOME)
        self.assertEqual(ditto.MCP_PROTOCOL_VERSION, response["result"]["protocolVersion"])

    def test_a_notification_is_never_answered(self):
        self.assertIsNone(ditto.mcp_handle(rpc(method="notifications/initialized"), self.HOME))

    def test_tools_list_exposes_exactly_the_profile_loader(self):
        response = ditto.mcp_handle(rpc(id=2, method="tools/list"), self.HOME)
        tools = response["result"]["tools"]
        self.assertEqual(["load_ditto_profile"], [tool["name"] for tool in tools])
        self.assertEqual(
            ["design", "video", "work", "write"],
            tools[0]["inputSchema"]["properties"]["domain"]["enum"],
        )

    def test_unknown_method_is_method_not_found(self):
        response = ditto.mcp_handle(rpc(id=3, method="does/notexist"), self.HOME)
        self.assertEqual(-32601, response["error"]["code"])

    def test_unknown_tool_is_invalid_params(self):
        response = ditto.mcp_handle(
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
            with mock.patch.object(ditto, "resolve_profile_paths", return_value=fake):
                response = ditto.mcp_handle(
                    rpc(
                        id=5,
                        method="tools/call",
                        params={"name": "load_ditto_profile", "arguments": {"domain": "design"}},
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
            ditto,
            "resolve_profile_paths",
            side_effect=ValueError("no active Ditto profile; run ditto"),
        ):
            response = ditto.mcp_handle(
                rpc(id=6, method="tools/call", params={"name": "load_ditto_profile", "arguments": {}}),
                self.HOME,
            )
        self.assertTrue(response["result"]["isError"])
        self.assertIn("run ditto", response["result"]["content"][0]["text"])

    def test_tools_call_defaults_to_the_work_domain(self):
        captured = {}

        def fake_resolve(home, domain):
            captured["domain"] = domain
            raise ValueError("no active Ditto profile; run ditto")

        with mock.patch.object(ditto, "resolve_profile_paths", side_effect=fake_resolve):
            ditto.mcp_handle(
                rpc(id=7, method="tools/call", params={"name": "load_ditto_profile", "arguments": {}}),
                self.HOME,
            )
        self.assertEqual("work", captured["domain"])


class McpStdioTest(unittest.TestCase):
    def run_server(self, messages, home):
        stdin = "".join(json.dumps(message) + "\n" for message in messages)
        result = subprocess.run(
            [sys.executable, str(DITTO), "mcp", "--ditto-home", home],
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
                     "params": {"name": "load_ditto_profile", "arguments": {"domain": "work"}}},
                ],
                tmp,
            )
        # the notification produces no response, so exactly three replies come back
        self.assertEqual([1, 2, 3], [message["id"] for message in responses])
        self.assertEqual("ditto", responses[0]["result"]["serverInfo"]["name"])
        self.assertEqual("load_ditto_profile", responses[1]["result"]["tools"][0]["name"])
        self.assertTrue(responses[2]["result"]["isError"])
        self.assertIn("run ditto", responses[2]["result"]["content"][0]["text"])

    def test_a_malformed_line_is_reported_and_the_loop_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdin = "not json\n" + json.dumps({"jsonrpc": "2.0", "id": 9, "method": "ping"}) + "\n"
            result = subprocess.run(
                [sys.executable, str(DITTO), "mcp", "--ditto-home", tmp],
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
