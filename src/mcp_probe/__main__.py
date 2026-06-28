"""mcp-probe CLI entry point."""

from __future__ import annotations

import argparse
import sys

from .report import format_json, format_text
from .runner import probe_http, probe_stdio


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mcp-probe",
        description="MCP server conformance tester — zero external dependencies",
    )
    parser.add_argument("subcommand", choices=["server"], help="What to probe")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport to use (default: stdio)",
    )
    parser.add_argument(
        "--command",
        help="Server command for stdio transport (e.g. 'python my_server.py')",
    )
    parser.add_argument(
        "--url",
        help="Server URL for http transport (e.g. http://localhost:8080)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        if not args.command:
            print("Error: --command is required for stdio transport", file=sys.stderr)
            return 2
        import shlex
        cmd = shlex.split(args.command)
        report = probe_stdio(cmd, timeout=args.timeout)
    else:
        if not args.url:
            print("Error: --url is required for http transport", file=sys.stderr)
            return 2
        report = probe_http(args.url, timeout=args.timeout)

    if args.format == "json":
        print(format_json(report))
    else:
        print(format_text(report))

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
