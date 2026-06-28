#!/usr/bin/env python3
"""Minimal JSON-RPC MCP server for integration testing. No external deps."""

import json
import sys

PROTOCOL_VERSION = "2025-03-26"

TOOLS = [
    {
        "name": "echo",
        "description": "Echoes the input back",
        "inputSchema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
]

request_id = None

for raw_line in sys.stdin:
    raw_line = raw_line.strip()
    if not raw_line:
        continue

    try:
        msg = json.loads(raw_line)
    except json.JSONDecodeError:
        continue

    # Notifications have no id
    if "id" not in msg:
        continue

    request_id = msg["id"]
    method = msg.get("method", "")

    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "MinimalTestServer", "version": "0.0.1"},
            },
        }
    elif method == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS},
        }
    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        if tool_name == "echo":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": args.get("message", "")}],
                    "isError": False,
                },
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }
    else:
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()
