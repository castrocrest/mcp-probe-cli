"""Report formatter: human-readable text and JSON output."""

from __future__ import annotations

import json

from .runner import ProbeReport


PASS = "✓"
FAIL = "✗"
WARN = "⚠"


def format_text(report: ProbeReport) -> str:
    lines = [
        "═" * 60,
        f"  mcp-probe report",
        f"  Server : {report.server_command}",
        f"  Transport: {report.transport_type}",
        f"  Duration : {report.duration_ms:.0f} ms",
        "═" * 60,
    ]

    if report.fatal_error:
        lines.append(f"\n{FAIL}  FATAL: {report.fatal_error}")
    else:
        lines.append("")
        for check in report.checks:
            icon = PASS if check.passed else FAIL
            lines.append(f"  {icon}  {check.name}")
            lines.append(f"       {check.message}")
        lines.append("")

    lines.append("─" * 60)
    if report.fatal_error:
        lines.append(f"  Result: FATAL ERROR — conformance suite could not complete")
    elif report.failed == 0:
        lines.append(f"  Result: PASS  — {report.passed}/{report.total} checks passed")
    else:
        lines.append(f"  Result: FAIL  — {report.failed}/{report.total} checks failed")

    if report.failed > 0:
        lines.append("")
        lines.append("  Failing checks:")
        for check in report.checks:
            if not check.passed:
                lines.append(f"    {FAIL}  {check.name}: {check.message}")

    lines.append("═" * 60)

    if not report.ok:
        lines.append("")
        lines.append("  Need a detailed remediation report? → https://castrocrest.gumroad.com")

    return "\n".join(lines)


def format_json(report: ProbeReport) -> str:
    data = {
        "ok": report.ok,
        "server": report.server_command,
        "transport": report.transport_type,
        "duration_ms": round(report.duration_ms, 1),
        "passed": report.passed,
        "failed": report.failed,
        "total": report.total,
        "fatal_error": report.fatal_error,
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "message": c.message,
            }
            for c in report.checks
        ],
    }
    return json.dumps(data, indent=2)
