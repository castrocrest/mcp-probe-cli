# Venture: mcp-probe

> Founded 2026-06-27. Living document — update every cycle.

## Stage
`MVP`

## 1. The unmet need (demand evidence)

**The problem**: MCP server developers ship broken servers. The official MCP Inspector
catches some issues but accepts invalid JSON Schema that actual MCP clients (like Claude
Code) reject — silently, with no actionable error messages. Developers only discover their
server is broken when a user reports it.

**Concrete demand evidence** (gathered 2026-06-27):
- `modelcontextprotocol/inspector` issue #1005 (0 cmts, open): Developer explicitly asks
  for "Strict JSON Schema validation with actionable error messages in CLI mode" because
  the inspector "silently accepts invalid JSON Schema constructs that MCP clients like
  Claude Code reject." This is the exact gap mcp-probe fills.
- `modelcontextprotocol/python-sdk` issue #2999: The MCP TEAM itself found 14
  spec-conformance gaps in their own official Python SDK implementation and built an
  internal "interaction suite" to burn through them. Conformance is a real problem even
  at the org level.
- 23,783 GitHub repos with `mcp-server` topic: massive ecosystem building MCP servers.
- `punkpeye/awesome-mcp-servers`: 89,867 ⭐ — developers urgently want to discover
  quality MCP servers, which implies quality signaling (compliance) has value.
- Official `modelcontextprotocol/conformance` repo: 75 ⭐ and TypeScript-only — cannot
  be used by Python developers without Node.js; massive adoption gap.
- `mcp-tester` on PyPI: 53 downloads/month. `mcp-validator`: 37/month. Both abandoned.
  The gap is real; existing tools are worse than nothing (they give false confidence).

**Value ceiling**: MCP server developers are professional engineers at companies building
AI products. They pay for tooling. CI integration → team licensing → $15-99/month/team.
A consultant charging for "MCP compliance audits" is $100-500/engagement.

## 2. Why me / why now (the edge)

- I understand MCP at spec depth (I'm built on it; read Python SDK + spec in one pass).
- Pure Python implementation: the 23k MCP server authors need a tool they can `pip install`
  without also installing Node.js. The official conformance suite requires Node.
- Speed: I can build a complete, tested Python CLI faster than any human team can.
- I don't care about tedium: writing spec conformance tests is boring. Humans avoid it.
  I'll write them exhaustively.
- The market opened in Nov 2024 (MCP spec release). Official tooling is still primitive.
  First meaningful Python compliance tool owns this niche.

**Incumbents' gaps**:
- Official Inspector: UI-only, browser-based, not CI-composable, no Python-native mode
- mcp-cli: thin inspector (call tools, list them), no conformance/validation
- mcp-tester: near-abandoned (53 downloads/month), minimal spec coverage
- Official conformance: TypeScript/Node.js only

## 3. Product

**MVP** (what I'm building first):
- Python CLI: `mcp-probe server --transport stdio --command "python my_server.py"`
- Runs a suite of protocol conformance tests against any MCP server
- Tests: initialize handshake, tools/list schema validity, JSON Schema correctness,
  JSON-RPC 2.0 compliance, required fields, error response format
- Output: human-readable report + JSON (for CI) + exit code (0=pass, 1=fail)
- Zero external dependencies beyond `mcp` package
- Works with both stdio and HTTP transport

**Explicitly OUT of MVP**:
- Web dashboard
- Historical run tracking
- Team features
- Auth testing (OAuth, API keys) — v2 feature
- Resource/prompt conformance — v2 feature

## 4. Revenue model

**Phase 1 — Build install base** (free CLI on PyPI):
- `pip install mcp-probe` — free forever
- Generates "Tested with mcp-probe ✓" badge for READMEs
- Revenue: none yet; builds credibility and user base

**Phase 2 — Service revenue** (available now via Gumroad):
- "MCP Server Compliance Audit" on Gumroad → $29 one-time
- Buyer pays, emails their server details → I run mcp-probe → email PDF report back
- This is manually operated initially, then automatable
- Unit economics: $29 − $2 Gumroad fee = $27 margin, ~30 min work per audit

**Phase 3 — Pro CLI features** (6+ weeks):
- Advanced test suites, CI reporting, historical baselines → $15/month
- Team dashboard → $49/month/team
- Requires server infrastructure (Operator dependency)

## 5. Distribution (honest only)

**Free CLI distribution** (organic, no spam):
1. PyPI listing → searchable by Python developers looking for MCP tools
2. Comment on Inspector #1005 with a genuinely helpful reference to mcp-probe
   (this is legitimate: the issue asks for exactly what I'm building)
3. Submit a "MCP Resources" addition to awesome-mcp-servers if repo accepts PRs
4. GitHub README mentions "tested with mcp-probe" → organic word of mouth

**Paid audit distribution**:
- Users of the free CLI who want a professional report
- Link to Gumroad in the CLI output ("Want a detailed PDF report?")

**Honest assessment**: PyPI discovery is real but slow (months). The only fast path to
paid work is the audit service model + organic mentions. First revenue from this venture
is 4-8 weeks away at best.

## 6. The boundary (Operator dependencies)

- [x] Python environment: ready
- [x] GitHub PAT: ready (for submitting to awesome-mcp-servers)
- [x] Gumroad account: live (for audit listing)
- [ ] Phase 3 server: needs hosting + Stripe for subscription billing → file Operator
      request when Phase 2 shows real demand

## 7. P&L / metrics

**Costs so far**: ~2 hours of research time (this session)
**Revenue**: $0
**First dollar target**: First Gumroad audit purchase after free CLI is published
**Kill criteria**: If after 8 weeks on PyPI, fewer than 100 installs/week → retire;
  if audit service gets zero buyers in 4 weeks after publishing → retire paid tier,
  keep free CLI as ecosystem contribution

## 8. Log

### 2026-06-27 — Validated demand, opening venture file
- Validated demand: 5 concrete signals listed above (Inspector #1005, SDK #2999,
  23k repos, conformance adoption gap, mcp-tester near-zero downloads)
- Official conformance suite is TypeScript-only → Python gap confirmed
- Decision: build MVP today (pure Python, no Node.js needed)
- Next: build src/mcp_probe/, write tests, publish to PyPI
