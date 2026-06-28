"""Запуск cursor-sdk-bridge на Windows (обход WinError 10038 в SDK)."""

from __future__ import annotations

import atexit
import os
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from cursor_sdk import CursorClient
from cursor_sdk._bridge import _terminate_process, parse_discovery_line
from cursor_sdk._vendor import resolve_bridge_path
from cursor_sdk.errors import CursorSDKError

_launched_bridge_processes: dict[int, subprocess.Popen[str]] = {}
_launched_bridge_lock = threading.Lock()


@dataclass(slots=True)
class BridgeSession:
    client: CursorClient
    process: subprocess.Popen[str]
    terminated: bool = False

    def terminate(self) -> None:
        if self.terminated:
            return
        _terminate_process(self.process)
        _unregister_bridge_process(self.process)
        self.terminated = True


def cleanup_bridge_processes() -> int:
    """Best-effort cleanup for Windows bridge nodes left from previous runs."""
    if os.name != "nt":
        return 0

    command = (
        "$bridge = Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -eq 'node.exe' -and $_.CommandLine -match 'cursor-sdk-bridge\\.js' "
        "}; "
        "if (-not $bridge) { Write-Output 0; exit 0 }; "
        "$ids = @($bridge | ForEach-Object { [int]$_.ProcessId } | Sort-Object -Unique); "
        "if ($ids.Count -gt 0) { "
        "Stop-Process -Id $ids -Force -ErrorAction SilentlyContinue "
        "}; "
        "Write-Output $ids.Count"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        # Translation should still run even if the OS refuses process inspection.
        return 0

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        return 0

    try:
        return int(lines[-1])
    except ValueError:
        return 0


cleanup_orphan_bridge_processes = cleanup_bridge_processes


def _register_bridge_process(process: subprocess.Popen[str]) -> None:
    with _launched_bridge_lock:
        _launched_bridge_processes[process.pid] = process


def _unregister_bridge_process(process: subprocess.Popen[str]) -> None:
    with _launched_bridge_lock:
        _launched_bridge_processes.pop(process.pid, None)


def cleanup_registered_bridges() -> int:
    """Best-effort cleanup for bridges created by the current Python process."""
    with _launched_bridge_lock:
        processes = list(_launched_bridge_processes.values())
        _launched_bridge_processes.clear()

    cleaned = 0
    for process in processes:
        try:
            # We only track bridges started by this process, so final cleanup
            # can safely target them without touching other concurrent runs.
            _terminate_process(process)
            cleaned += 1
        except Exception:
            continue
    return cleaned


def _read_discovery_blocking(
    process: subprocess.Popen[str],
    timeout: float,
) -> dict:
    if process.stderr is None:
        raise CursorSDKError("Bridge process stderr is unavailable")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = process.stderr.readline()
        if line:
            discovery = parse_discovery_line(line)
            if discovery is not None:
                return dict(discovery)
        elif process.poll() is not None:
            break
        else:
            time.sleep(0.05)

    raise CursorSDKError("Timed out waiting for bridge discovery")


def _endpoint_from_discovery(discovery: dict) -> tuple[str, str]:
    url = str(discovery.get("url") or "")
    if not url:
        host = str(discovery.get("host") or "")
        port = discovery.get("port")
        if not host or port is None:
            raise CursorSDKError("Bridge discovery payload is missing a URL")
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        url = f"http://{host}:{port}"

    auth_token = str(discovery.get("authToken") or "")
    token_file = discovery.get("authTokenFile")
    if not auth_token and token_file:
        auth_token = Path(str(token_file)).read_text(encoding="utf-8").strip()
    if not auth_token:
        raise CursorSDKError("Bridge discovery payload is missing auth token")

    return url, auth_token


@contextmanager
def launch_bridge_session(
    workspace: str, *, timeout: float = 60.0
) -> Iterator[BridgeSession]:
    argv = [os.fspath(resolve_bridge_path()), "--workspace", os.fspath(workspace)]
    process = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    _register_bridge_process(process)
    client_context = None
    session: BridgeSession | None = None
    try:
        discovery = _read_discovery_blocking(process, timeout)
        url, auth_token = _endpoint_from_discovery(discovery)
        client_context = CursorClient.connect(base_url=url, auth_token=auth_token)
        client = client_context.__enter__()
        session = BridgeSession(client=client, process=process)
        yield session
    finally:
        if session is None or not session.terminated:
            try:
                if client_context is not None:
                    client_context.__exit__(None, None, None)
            finally:
                if session is not None:
                    session.terminate()
                else:
                    try:
                        _terminate_process(process)
                    finally:
                        _unregister_bridge_process(process)


@contextmanager
def launch_bridge_client(workspace: str, *, timeout: float = 60.0) -> Iterator[CursorClient]:
    with launch_bridge_session(workspace, timeout=timeout) as session:
        yield session.client


atexit.register(cleanup_registered_bridges)
