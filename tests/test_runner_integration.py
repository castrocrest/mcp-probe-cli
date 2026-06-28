"""Integration tests: probe_stdio against minimal_server.py."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from mcp_probe.runner import probe_stdio

MINIMAL_SERVER = [sys.executable, str(pathlib.Path(__file__).parent / "minimal_server.py")]
BAD_CMD = [sys.executable, "-c", "import sys; sys.exit(1)"]


class TestProbeStdioIntegration:
    def test_minimal_server_passes_all_checks(self):
        report = probe_stdio(MINIMAL_SERVER, timeout=5.0)
        assert report.fatal_error is None, f"Fatal: {report.fatal_error}"
        failures = [c for c in report.checks if not c.passed]
        assert failures == [], f"Failing checks: {failures}"
        assert report.ok

    def test_minimal_server_has_expected_checks(self):
        report = probe_stdio(MINIMAL_SERVER, timeout=5.0)
        names = {c.name for c in report.checks}
        # Core checks must be present
        assert "jsonrpc_envelope" in names
        assert "protocol_version" in names
        assert "capabilities" in names
        assert "server_info_name" in names
        assert "tools_list" in names

    def test_minimal_server_returns_correct_tool_count(self):
        report = probe_stdio(MINIMAL_SERVER, timeout=5.0)
        tl = next(c for c in report.checks if c.name == "tools_list")
        assert "1 tool" in tl.message

    def test_bad_command_returns_fatal_error(self):
        report = probe_stdio(BAD_CMD, timeout=5.0)
        assert report.fatal_error is not None

    def test_nonexistent_command_returns_fatal_error(self):
        report = probe_stdio(["_nonexistent_binary_xyz_"], timeout=2.0)
        assert report.fatal_error is not None

    def test_report_has_duration(self):
        report = probe_stdio(MINIMAL_SERVER, timeout=5.0)
        assert report.duration_ms > 0

    def test_report_ok_property(self):
        report = probe_stdio(MINIMAL_SERVER, timeout=5.0)
        assert report.ok is True

    def test_passed_failed_total_counts(self):
        report = probe_stdio(MINIMAL_SERVER, timeout=5.0)
        assert report.total == report.passed + report.failed
        assert report.failed == 0


class TestBrokenServer:
    """Probe a server that returns invalid responses."""

    def _make_server(self, code: str) -> list:
        return [sys.executable, "-c", code]

    def test_server_returning_wrong_jsonrpc_version(self):
        code = """
import json, sys
for line in sys.stdin:
    msg = json.loads(line)
    if 'id' not in msg: continue
    resp = {"jsonrpc": "1.0", "id": msg["id"], "result": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "serverInfo": {"name": "Bad", "version": "0.0.1"}
    }}
    sys.stdout.write(json.dumps(resp)+"\\n"); sys.stdout.flush()
"""
        report = probe_stdio(self._make_server(code), timeout=5.0)
        env_check = next((c for c in report.checks if c.name == "jsonrpc_envelope"), None)
        assert env_check is not None
        assert not env_check.passed

    def test_server_with_boolean_schema_fails(self):
        code = """
import json, sys
for line in sys.stdin:
    msg = json.loads(line)
    if 'id' not in msg: continue
    method = msg.get("method","")
    rid = msg["id"]
    if method == "initialize":
        resp = {"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"Bad","version":"1.0"}}}
    elif method == "tools/list":
        resp = {"jsonrpc":"2.0","id":rid,"result":{"tools":[{"name":"bad","description":"broken","inputSchema": True}]}}
    else:
        resp = {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"nope"}}
    sys.stdout.write(json.dumps(resp)+"\\n"); sys.stdout.flush()
"""
        report = probe_stdio(self._make_server(code), timeout=5.0)
        schema_checks = [c for c in report.checks if "input_schema" in c.name]
        assert schema_checks, "No input_schema checks found"
        assert any(not c.passed for c in schema_checks)
        assert not report.ok
