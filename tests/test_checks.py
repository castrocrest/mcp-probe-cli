"""Unit tests for mcp_probe.checks — all pure logic, no subprocess needed."""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from mcp_probe.checks import (
    check_jsonrpc_envelope,
    check_initialize_result,
    check_tools_list,
    check_error_response,
    _is_valid_json_schema,
)


# ── check_jsonrpc_envelope ──────────────────────────────────────────────────

class TestJsonRpcEnvelope:
    def test_valid_result_response(self):
        resp = {"jsonrpc": "2.0", "id": 1, "result": {"foo": "bar"}}
        r = check_jsonrpc_envelope(resp, 1)
        assert r.passed

    def test_valid_error_response(self):
        resp = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Not found"}}
        r = check_jsonrpc_envelope(resp, 1)
        assert r.passed

    def test_wrong_jsonrpc_version(self):
        resp = {"jsonrpc": "1.0", "id": 1, "result": {}}
        r = check_jsonrpc_envelope(resp, 1)
        assert not r.passed
        assert "2.0" in r.message

    def test_missing_jsonrpc(self):
        resp = {"id": 1, "result": {}}
        r = check_jsonrpc_envelope(resp, 1)
        assert not r.passed

    def test_mismatched_id(self):
        resp = {"jsonrpc": "2.0", "id": 99, "result": {}}
        r = check_jsonrpc_envelope(resp, 1)
        assert not r.passed
        assert "99" in r.message

    def test_both_result_and_error(self):
        resp = {"jsonrpc": "2.0", "id": 1, "result": {}, "error": {}}
        r = check_jsonrpc_envelope(resp, 1)
        assert not r.passed

    def test_neither_result_nor_error(self):
        resp = {"jsonrpc": "2.0", "id": 1}
        r = check_jsonrpc_envelope(resp, 1)
        assert not r.passed

    def test_not_a_dict(self):
        r = check_jsonrpc_envelope("not a dict", 1)
        assert not r.passed


# ── check_initialize_result ──────────────────────────────────────────────────

class TestInitializeResult:
    def _minimal(self) -> dict:
        return {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "TestServer", "version": "1.0.0"},
        }

    def test_valid_result(self):
        results = check_initialize_result(self._minimal())
        assert all(r.passed for r in results), [r for r in results if not r.passed]

    def test_missing_protocol_version(self):
        d = self._minimal()
        del d["protocolVersion"]
        results = check_initialize_result(d)
        pv = next(r for r in results if "protocol_version" in r.name)
        assert not pv.passed

    def test_unknown_protocol_version_warns_but_passes(self):
        d = self._minimal()
        d["protocolVersion"] = "2099-01-01"
        results = check_initialize_result(d)
        pv = next(r for r in results if "protocol_version" in r.name)
        assert pv.passed  # future version → warn but allow

    def test_missing_capabilities(self):
        d = self._minimal()
        del d["capabilities"]
        results = check_initialize_result(d)
        cap = next(r for r in results if "capabilities" == r.name)
        assert not cap.passed

    def test_capabilities_not_object(self):
        d = self._minimal()
        d["capabilities"] = []
        results = check_initialize_result(d)
        cap = next(r for r in results if "capabilities" == r.name)
        assert not cap.passed

    def test_missing_server_info(self):
        d = self._minimal()
        del d["serverInfo"]
        results = check_initialize_result(d)
        si = next(r for r in results if "server_info" == r.name)
        assert not si.passed

    def test_empty_server_name(self):
        d = self._minimal()
        d["serverInfo"]["name"] = ""
        results = check_initialize_result(d)
        si_name = next(r for r in results if "server_info_name" == r.name)
        assert not si_name.passed

    def test_version_not_string(self):
        d = self._minimal()
        d["serverInfo"]["version"] = 42
        results = check_initialize_result(d)
        si_ver = next(r for r in results if "server_info_version" == r.name)
        assert not si_ver.passed


# ── _is_valid_json_schema ──────────────────────────────────────────────────

class TestIsValidJsonSchema:
    def test_empty_schema_ok(self):
        ok, _ = _is_valid_json_schema({})
        assert ok

    def test_object_schema(self):
        ok, _ = _is_valid_json_schema({"type": "object", "properties": {"name": {"type": "string"}}})
        assert ok

    def test_boolean_true_invalid(self):
        ok, msg = _is_valid_json_schema(True)
        assert not ok
        assert "Claude Code" in msg

    def test_boolean_false_invalid(self):
        ok, msg = _is_valid_json_schema(False)
        assert not ok

    def test_invalid_type_value(self):
        ok, msg = _is_valid_json_schema({"type": "float"})
        assert not ok
        assert "float" in msg

    def test_nested_invalid_property(self):
        ok, msg = _is_valid_json_schema({
            "type": "object",
            "properties": {"count": True}
        })
        assert not ok
        assert "count" in msg

    def test_items_must_be_valid(self):
        ok, msg = _is_valid_json_schema({"type": "array", "items": "string"})
        assert not ok

    def test_valid_array_schema(self):
        ok, _ = _is_valid_json_schema({"type": "array", "items": {"type": "string"}})
        assert ok

    def test_not_a_dict_or_bool(self):
        ok, msg = _is_valid_json_schema("string")
        assert not ok


# ── check_tools_list ──────────────────────────────────────────────────────

class TestCheckToolsList:
    def _tool(self, **overrides):
        t = {
            "name": "my_tool",
            "description": "Does something useful",
            "inputSchema": {"type": "object", "properties": {}},
        }
        t.update(overrides)
        return t

    def test_valid_single_tool(self):
        results = check_tools_list({"tools": [self._tool()]})
        assert all(r.passed for r in results), [r for r in results if not r.passed]

    def test_empty_tools_list(self):
        results = check_tools_list({"tools": []})
        assert all(r.passed for r in results)

    def test_tools_not_array(self):
        results = check_tools_list({"tools": {}})
        assert results[0].name == "tools_list"
        assert not results[0].passed

    def test_tool_missing_name(self):
        t = self._tool()
        del t["name"]
        results = check_tools_list({"tools": [t]})
        name_check = next(r for r in results if "name" in r.name)
        assert not name_check.passed

    def test_tool_missing_description(self):
        t = self._tool()
        del t["description"]
        results = check_tools_list({"tools": [t]})
        desc_check = next(r for r in results if "description" in r.name)
        assert not desc_check.passed

    def test_tool_empty_description(self):
        t = self._tool(description="   ")
        results = check_tools_list({"tools": [t]})
        desc_check = next(r for r in results if "description" in r.name)
        assert not desc_check.passed

    def test_tool_missing_input_schema(self):
        t = self._tool()
        del t["inputSchema"]
        results = check_tools_list({"tools": [t]})
        schema_check = next(r for r in results if "input_schema" in r.name)
        assert not schema_check.passed

    def test_tool_boolean_schema_fails(self):
        t = self._tool(inputSchema=True)
        results = check_tools_list({"tools": [t]})
        schema_check = next(r for r in results if "input_schema" in r.name)
        assert not schema_check.passed
        assert "Claude Code" in schema_check.message


# ── check_error_response ──────────────────────────────────────────────────

class TestCheckErrorResponse:
    def test_valid_error(self):
        r = check_error_response({"code": -32601, "message": "Method not found"})
        assert r.passed

    def test_missing_code(self):
        r = check_error_response({"message": "oops"})
        assert not r.passed

    def test_non_integer_code(self):
        r = check_error_response({"code": "err", "message": "oops"})
        assert not r.passed

    def test_missing_message(self):
        r = check_error_response({"code": -32601})
        assert not r.passed

    def test_not_a_dict(self):
        r = check_error_response("error string")
        assert not r.passed
