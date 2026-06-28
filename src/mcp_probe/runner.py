"""Probe runner: coordinates transport + checks, produces a Report."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .checks import (
    CheckResult,
    check_error_response,
    check_initialize_result,
    check_jsonrpc_envelope,
    check_tools_list,
)
from .transport import HttpTransport, StdioTransport, TransportError


MCP_CLIENT_INFO = {"name": "mcp-probe", "version": "0.1.0"}
MCP_CAPABILITIES: dict[str, Any] = {}


@dataclass
class ProbeReport:
    server_command: str
    transport_type: str
    start_time: float
    end_time: float = 0.0
    checks: list[CheckResult] = field(default_factory=list)
    fatal_error: str | None = None

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def ok(self) -> bool:
        return self.fatal_error is None and self.failed == 0

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


def _probe_with_transport(transport, report: ProbeReport) -> None:
    """Run the conformance suite against an already-started transport."""

    # --- Step 1: initialize ---
    try:
        resp = transport.send_request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "clientInfo": MCP_CLIENT_INFO,
                "capabilities": MCP_CAPABILITIES,
            },
        )
    except TransportError as e:
        report.fatal_error = f"initialize failed: {e}"
        return

    envelope_check = check_jsonrpc_envelope(resp, 1)
    report.checks.append(envelope_check)
    if not envelope_check.passed:
        report.fatal_error = f"Cannot continue: {envelope_check.message}"
        return

    if "error" in resp:
        report.checks.append(check_error_response(resp["error"]))
        report.fatal_error = "Server returned error for initialize"
        return

    result = resp.get("result", {})
    report.checks.extend(check_initialize_result(result))

    # --- Step 2: initialized notification ---
    try:
        transport.send_notification("notifications/initialized")
    except TransportError:
        pass  # not fatal; some servers accept without the notification

    # --- Step 3: tools/list (if server declares tools capability) ---
    caps = result.get("capabilities", {})
    if "tools" in caps:
        try:
            resp2 = transport.send_request("tools/list")
        except TransportError as e:
            report.checks.append(
                CheckResult("tools_list", False, f"tools/list request failed: {e}")
            )
        else:
            envelope2 = check_jsonrpc_envelope(resp2, 2)
            report.checks.append(envelope2)
            if envelope2.passed and "result" in resp2:
                report.checks.extend(check_tools_list(resp2["result"]))
            elif envelope2.passed and "error" in resp2:
                report.checks.append(check_error_response(resp2["error"]))
    else:
        report.checks.append(
            CheckResult(
                "tools_capability",
                True,
                "Server does not advertise 'tools' capability — tools/list skipped",
            )
        )

    # --- Step 4: invalid method (error handling) ---
    try:
        resp3 = transport.send_request("_probe/nonexistent_method_xyz")
    except TransportError:
        pass  # can't check
    else:
        envelope3 = check_jsonrpc_envelope(resp3, 3)
        report.checks.append(envelope3)
        if envelope3.passed and "error" in resp3:
            err_check = check_error_response(resp3["error"])
            code = resp3["error"].get("code")
            if code == -32601:  # JSON-RPC Method Not Found
                report.checks.append(CheckResult(
                    "method_not_found",
                    True,
                    "Server returns -32601 for unknown methods (JSON-RPC spec compliant)",
                ))
            else:
                report.checks.append(CheckResult(
                    "method_not_found",
                    False,
                    f"Server returned code {code} for unknown method; expected -32601",
                ))
        elif envelope3.passed and "result" in resp3:
            report.checks.append(CheckResult(
                "method_not_found",
                False,
                "Server returned a result for an unknown method instead of an error",
            ))


def probe_stdio(command: list[str], timeout: float = 10.0) -> ProbeReport:
    report = ProbeReport(
        server_command=" ".join(command),
        transport_type="stdio",
        start_time=time.monotonic(),
    )
    transport = StdioTransport(command, timeout=timeout)
    try:
        transport.start()
        time.sleep(0.2)  # give server a moment to initialise
        _probe_with_transport(transport, report)
    except Exception as e:
        report.fatal_error = f"Unexpected error: {e}"
    finally:
        transport.stop()
        report.end_time = time.monotonic()
    return report


def probe_http(url: str, timeout: float = 10.0) -> ProbeReport:
    report = ProbeReport(
        server_command=url,
        transport_type="http",
        start_time=time.monotonic(),
    )
    transport = HttpTransport(url, timeout=timeout)
    try:
        _probe_with_transport(transport, report)
    except Exception as e:
        report.fatal_error = f"Unexpected error: {e}"
    finally:
        report.end_time = time.monotonic()
    return report
