"""Запуск cursor-sdk-bridge на Windows (обход WinError 10038 в SDK)."""

from __future__ import annotations

import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from cursor_sdk import CursorClient
from cursor_sdk._bridge import _terminate_process, parse_discovery_line
from cursor_sdk._vendor import resolve_bridge_path
from cursor_sdk.errors import CursorSDKError


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
def launch_bridge_client(workspace: str, *, timeout: float = 60.0) -> Iterator[CursorClient]:
    argv = [os.fspath(resolve_bridge_path()), "--workspace", os.fspath(workspace)]
    process = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        discovery = _read_discovery_blocking(process, timeout)
        url, auth_token = _endpoint_from_discovery(discovery)
        with CursorClient.connect(base_url=url, auth_token=auth_token) as client:
            yield client
    finally:
        _terminate_process(process)
