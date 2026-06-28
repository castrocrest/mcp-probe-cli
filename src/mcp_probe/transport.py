"""MCP transport layer: stdio and HTTP. Zero external dependencies."""

import json
import subprocess
import threading
import time
import urllib.request
import urllib.error
from typing import Any


class TransportError(Exception):
    pass


class StdioTransport:
    """Manages a subprocess MCP server over stdio."""

    def __init__(self, command: list[str], timeout: float = 10.0):
        self._command = command
        self._timeout = timeout
        self._proc: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def stop(self) -> None:
        if self._proc:
            try:
                self._proc.stdin.close()
            except Exception:
                pass
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    def send_request(self, method: str, params: dict | None = None) -> dict:
        if not self._proc:
            raise TransportError("Transport not started")
        with self._lock:
            self._request_id += 1
            msg = {"jsonrpc": "2.0", "id": self._request_id, "method": method}
            if params is not None:
                msg["params"] = params
            payload = (json.dumps(msg) + "\n").encode()
            try:
                self._proc.stdin.write(payload)
                self._proc.stdin.flush()
            except BrokenPipeError as e:
                raise TransportError(f"Server closed stdin: {e}") from e
            return self._read_response()

    def send_notification(self, method: str, params: dict | None = None) -> None:
        if not self._proc:
            raise TransportError("Transport not started")
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        payload = (json.dumps(msg) + "\n").encode()
        try:
            self._proc.stdin.write(payload)
            self._proc.stdin.flush()
        except BrokenPipeError as e:
            raise TransportError(f"Server closed stdin: {e}") from e

    def _read_response(self) -> dict:
        deadline = time.monotonic() + self._timeout
        buf = b""
        while time.monotonic() < deadline:
            if self._proc.stdout.readable():
                chunk = self._proc.stdout.readline()
                if chunk:
                    buf += chunk
                    try:
                        return json.loads(buf.decode())
                    except json.JSONDecodeError:
                        continue
            time.sleep(0.01)
        raise TransportError(f"Timed out waiting for response after {self._timeout}s")


class HttpTransport:
    """MCP server over HTTP (Streamable HTTP transport)."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session_id: str | None = None
        self._request_id = 0

    def send_request(self, method: str, params: dict | None = None) -> dict:
        self._request_id += 1
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": self._request_id, "method": method}
        if params is not None:
            msg["params"] = params
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        payload = json.dumps(msg).encode()
        req = urllib.request.Request(
            self._base_url + "/mcp",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if "Mcp-Session-Id" in resp.headers and not self._session_id:
                    self._session_id = resp.headers["Mcp-Session-Id"]
                body = resp.read().decode()
                if body.startswith("data:"):
                    # SSE response — extract JSON from first data line
                    for line in body.splitlines():
                        if line.startswith("data:"):
                            return json.loads(line[5:].strip())
                    raise TransportError("SSE response had no data line")
                return json.loads(body)
        except urllib.error.URLError as e:
            raise TransportError(f"HTTP error: {e}") from e

    def send_notification(self, method: str, params: dict | None = None) -> None:
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        headers = {"Content-Type": "application/json"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        req = urllib.request.Request(
            self._base_url + "/mcp",
            data=json.dumps(msg).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout):
                pass
        except urllib.error.URLError:
            pass  # notifications are fire-and-forget
