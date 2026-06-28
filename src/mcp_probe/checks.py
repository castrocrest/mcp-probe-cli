"""MCP spec conformance checks. Each check returns a CheckResult."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def check_jsonrpc_envelope(response: dict, request_id: int) -> CheckResult:
    """JSON-RPC 2.0: response must have jsonrpc='2.0', matching id, result or error."""
    if not isinstance(response, dict):
        return CheckResult("jsonrpc_envelope", False, "Response is not a JSON object")

    if response.get("jsonrpc") != "2.0":
        return CheckResult(
            "jsonrpc_envelope",
            False,
            f"jsonrpc field must be '2.0', got: {response.get('jsonrpc')!r}",
        )

    if response.get("id") != request_id:
        return CheckResult(
            "jsonrpc_envelope",
            False,
            f"Response id {response.get('id')!r} does not match request id {request_id}",
        )

    has_result = "result" in response
    has_error = "error" in response
    if has_result == has_error:  # both present or both absent
        return CheckResult(
            "jsonrpc_envelope",
            False,
            "Response must have exactly one of 'result' or 'error'",
        )

    return CheckResult("jsonrpc_envelope", True, "JSON-RPC 2.0 envelope is valid")


def check_initialize_result(result: dict) -> list[CheckResult]:
    """MCP initialize result must have protocolVersion, capabilities, serverInfo."""
    checks = []

    # protocolVersion
    pv = result.get("protocolVersion")
    if not isinstance(pv, str):
        checks.append(CheckResult("protocol_version", False, f"protocolVersion must be a string, got {type(pv).__name__}"))
    elif pv not in {"2024-11-05", "2025-03-26", "2025-06-18"}:
        # Known versions — warn but don't fail (future versions are valid)
        checks.append(CheckResult(
            "protocol_version",
            True,
            f"protocolVersion '{pv}' is not a known stable version (may be draft/future)",
        ))
    else:
        checks.append(CheckResult("protocol_version", True, f"protocolVersion '{pv}' is valid"))

    # capabilities
    caps = result.get("capabilities")
    if not isinstance(caps, dict):
        checks.append(CheckResult("capabilities", False, f"capabilities must be an object, got {type(caps).__name__}"))
    else:
        checks.append(CheckResult("capabilities", True, "capabilities is an object"))

    # serverInfo
    info = result.get("serverInfo")
    if not isinstance(info, dict):
        checks.append(CheckResult("server_info", False, f"serverInfo must be an object, got {type(info).__name__}"))
    else:
        name = info.get("name")
        version = info.get("version")
        if not isinstance(name, str) or not name:
            checks.append(CheckResult("server_info_name", False, "serverInfo.name must be a non-empty string"))
        else:
            checks.append(CheckResult("server_info_name", True, f"serverInfo.name = '{name}'"))
        if not isinstance(version, str):
            checks.append(CheckResult("server_info_version", False, "serverInfo.version must be a string"))
        else:
            checks.append(CheckResult("server_info_version", True, f"serverInfo.version = '{version}'"))

    return checks


def _is_valid_json_schema(schema: Any) -> tuple[bool, str]:
    """Validate a JSON Schema object (basic checks, not full spec)."""
    # JSON Schema booleans are valid schemas (true/false)
    if isinstance(schema, bool):
        return False, f"JSON Schema 'true' or 'false' literal is not accepted by Claude Code; use an explicit object schema"

    if not isinstance(schema, dict):
        return False, f"Schema must be a JSON object, got {type(schema).__name__}"

    schema_type = schema.get("type")
    if schema_type is not None:
        valid_types = {"string", "number", "integer", "boolean", "array", "object", "null"}
        if isinstance(schema_type, str) and schema_type not in valid_types:
            return False, f"Invalid type value '{schema_type}'; must be one of {sorted(valid_types)}"
        if not isinstance(schema_type, (str, list)):
            return False, f"'type' must be a string or array, got {type(schema_type).__name__}"

    # Recurse into properties
    props = schema.get("properties", {})
    if props and not isinstance(props, dict):
        return False, "'properties' must be an object"
    for prop_name, prop_schema in (props or {}).items():
        ok, msg = _is_valid_json_schema(prop_schema)
        if not ok:
            return False, f"property '{prop_name}': {msg}"

    # Recurse into items
    items = schema.get("items")
    if items is not None:
        ok, msg = _is_valid_json_schema(items)
        if not ok:
            return False, f"'items': {msg}"

    return True, "ok"


def check_tools_list(result: dict) -> list[CheckResult]:
    """tools/list result: must have 'tools' array; each tool must have name, description, inputSchema."""
    checks = []

    tools = result.get("tools")
    if not isinstance(tools, list):
        return [CheckResult("tools_list", False, f"tools/list result must have 'tools' array, got {type(tools).__name__}")]

    checks.append(CheckResult("tools_list", True, f"tools/list returned {len(tools)} tool(s)"))

    for i, tool in enumerate(tools):
        tag = f"tool[{i}]({tool.get('name', '?')})"
        if not isinstance(tool, dict):
            checks.append(CheckResult(f"{tag}_structure", False, "Tool must be a JSON object"))
            continue

        # name
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            checks.append(CheckResult(f"{tag}_name", False, "Tool 'name' must be a non-empty string"))
        else:
            checks.append(CheckResult(f"{tag}_name", True, f"name = '{name}'"))

        # description
        desc = tool.get("description")
        if not isinstance(desc, str):
            checks.append(CheckResult(f"{tag}_description", False, "Tool 'description' must be a string"))
        elif not desc.strip():
            checks.append(CheckResult(f"{tag}_description", False, "Tool 'description' is empty — clients won't know what this tool does"))
        else:
            checks.append(CheckResult(f"{tag}_description", True, f"description present ({len(desc)} chars)"))

        # inputSchema
        schema = tool.get("inputSchema")
        if schema is None:
            checks.append(CheckResult(f"{tag}_input_schema", False, "Tool is missing 'inputSchema' — required by MCP spec"))
        else:
            ok, msg = _is_valid_json_schema(schema)
            if ok:
                checks.append(CheckResult(f"{tag}_input_schema", True, "inputSchema is valid JSON Schema"))
            else:
                checks.append(CheckResult(f"{tag}_input_schema", False, f"inputSchema invalid: {msg}"))

    return checks


def check_error_response(error: dict) -> CheckResult:
    """JSON-RPC 2.0 error object must have 'code' (int) and 'message' (string)."""
    if not isinstance(error, dict):
        return CheckResult("error_object", False, f"error must be an object, got {type(error).__name__}")

    code = error.get("code")
    if not isinstance(code, int):
        return CheckResult("error_code", False, f"error.code must be an integer, got {type(code).__name__}")

    msg = error.get("message")
    if not isinstance(msg, str):
        return CheckResult("error_message", False, f"error.message must be a string, got {type(msg).__name__}")

    return CheckResult("error_object", True, f"Error response valid (code={code}, message='{msg}')")
