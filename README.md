# mcp-probe-cli

**MCP server conformance tester — zero external dependencies.**

Catch spec violations before your MCP server ships. `mcp-conform` runs a suite of
Model Context Protocol conformance checks and tells you exactly what's wrong and why.

```bash
pip install mcp-conform
mcp-conform server --transport stdio --command "python my_server.py"
```

---

## Why mcp-conform?

The official MCP Inspector accepts invalid JSON Schema that MCP clients (including
Claude Code) reject — silently, with no useful error messages. You discover the
problem when a real user reports it. `mcp-conform` catches it before push.

**What it checks:**

| Check | What it validates |
|-------|-------------------|
| JSON-RPC envelope | `jsonrpc: "2.0"`, matching id, exactly one of result/error |
| Initialize response | `protocolVersion`, `capabilities` object, `serverInfo.name/version` |
| tools/list structure | `tools` array, each tool's name/description/inputSchema |
| JSON Schema validity | Detects `true`/`false` boolean schemas rejected by Claude Code |
| Error responses | `code` (integer) + `message` (string) per spec |
| Method not found | Returns `-32601` for unknown methods |

---

## Usage

### stdio transport (most common)

```bash
mcp-conform server --transport stdio --command "python my_server.py"
mcp-conform server --transport stdio --command "node dist/server.js"
mcp-conform server --transport stdio --command "uv run python -m mypackage.server"
```

### HTTP transport

```bash
mcp-conform server --transport http --url http://localhost:8080
```

### CI / GitHub Actions

```bash
# Fails with exit code 1 if any check fails
mcp-conform server --transport stdio --command "python my_server.py" --format json | tee report.json
```

```yaml
# .github/workflows/mcp-conformance.yml
- name: Run MCP conformance checks
  run: |
    pip install mcp-conform
    mcp-conform server --transport stdio --command "python my_server.py"
```

---

## Output example

```
════════════════════════════════════════════════════════════
  mcp-conform report
  Server : python my_server.py
  Transport: stdio
  Duration : 312 ms
════════════════════════════════════════════════════════════

  ✓  jsonrpc_envelope
       JSON-RPC 2.0 envelope is valid
  ✓  protocol_version
       protocolVersion '2025-03-26' is valid
  ✓  capabilities
       capabilities is an object
  ✓  server_info_name
       serverInfo.name = 'MyServer'
  ✗  tool[0](search)_input_schema
       inputSchema invalid: JSON Schema 'true' literal is not accepted by Claude Code

────────────────────────────────────────────────────────────
  Result: FAIL  — 1/5 checks failed

  Failing checks:
    ✗  tool[0](search)_input_schema: inputSchema invalid: ...
════════════════════════════════════════════════════════════
```

---

## Zero dependencies

`mcp-conform` uses only Python stdlib (Python 3.10+). No `mcp` SDK, no `httpx`,
no `pydantic` — nothing to install, no version conflicts.

---

## License

MIT
