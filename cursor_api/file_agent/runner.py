"""Запуск одного Cursor Agent (composer-2.5) на одну часть файла."""

from __future__ import annotations

import hashlib
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from cursor_sdk import (
    CursorAgentError,
    LocalAgentOptions,
    ModelParameterValue,
    ModelSelection,
    RunResult,
)

from file_agent import validation
from file_agent.bridge_launch import launch_bridge_session
from file_agent.keys import load_api_key

FILE_POLL_SECONDS = 20.0

# Cursor resolves bare composer-2.5 to the fast tier by default, so we pin
# fast=false explicitly and reject any resolved fast variant after the run.
MODEL_SELECTION = ModelSelection(
    id="composer-2.5",
    params=(ModelParameterValue(id="fast", value="false"),),
)


class SystemPromptNotSupportedError(RuntimeError):
    """cursor_sdk не умеет задавать system prompt корневому агенту."""


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    size: int
    mtime_ns: int
    sha256: str


def _build_user_message(part_path: Path, system_prompt: str) -> str:
    # SDK не принимает root system prompt — инструкция из prompt.md идёт в user message.
    return (
        f"{system_prompt.strip()}\n\n"
        "---\n"
        f"Обработай файл на диске: {part_path}\n"
        "Переведи его содержимое на русский и упрости согласно инструкции выше.\n"
        "Перезапиши этот же файл результатом."
    )


def _fingerprint_file(path: Path) -> FileFingerprint:
    stat = path.stat()
    return FileFingerprint(
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _file_changed(path: Path, initial: FileFingerprint) -> bool:
    try:
        current = _fingerprint_file(path)
    except OSError:
        return False
    return current != initial


def _cancel_run(run) -> None:
    try:
        run.cancel()
    except Exception:
        pass


def _translated_file_is_ready(
    path: Path,
    *,
    initial_fingerprint: FileFingerprint,
    source_text: str,
) -> bool:
    if not _file_changed(path, initial_fingerprint):
        return False
    try:
        translated = path.read_text(encoding="utf-8")
        result = validation.validate_translation(source_text, translated, file=path)
    except Exception:
        return False
    return result.ok


def _wait_run(
    run,
    timeout: float,
    *,
    part_path: Path,
    initial_fingerprint: FileFingerprint,
    source_text: str,
    poll_interval: float = FILE_POLL_SECONDS,
) -> RunResult | None:
    results: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

    def wait_for_run() -> None:
        try:
            results.put(("result", run.wait()))
        except Exception as err:
            results.put(("error", err))

    # run.wait() can hang after the agent has already written the file. A daemon
    # thread lets the file watcher release the part without blocking shutdown.
    threading.Thread(target=wait_for_run, daemon=True).start()
    deadline = time.monotonic() + timeout

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _cancel_run(run)
            raise TimeoutError(
                f"Agent run exceeded {timeout}s timeout for run {run.id}"
            )

        wait_seconds = min(max(poll_interval, 0.1), remaining)
        try:
            status, value = results.get(timeout=wait_seconds)
        except queue.Empty:
            if _translated_file_is_ready(
                part_path,
                initial_fingerprint=initial_fingerprint,
                source_text=source_text,
            ):
                _cancel_run(run)
                return None
            continue

        if status == "error":
            if not isinstance(value, BaseException):
                raise RuntimeError(f"Agent wait failed with non-exception: {value}")
            raise value
        return value


def _is_fast_variant(model: object | None) -> bool:
    if model is None:
        return False

    model_id = getattr(model, "id", "")
    if isinstance(model_id, str) and model_id.endswith("-fast"):
        return True

    params = getattr(model, "params", ()) or ()
    for param in params:
        if getattr(param, "id", "") != "fast":
            continue
        return str(getattr(param, "value", "")).strip().lower() == "true"
    return False


def _assert_non_fast_model(result: RunResult) -> None:
    if not _is_fast_variant(result.model):
        return

    resolved_id = getattr(result.model, "id", "unknown")
    raise RuntimeError(
        "Resolved model unexpectedly used fast variant: "
        f"{resolved_id}. Request must stay on composer-2.5 with fast=false."
    )


def run_part(part_path: Path, *, system_prompt: str, timeout: float = 180) -> None:
    """Запускает одного агента для одной части; ошибка — исключение, без fallback."""
    path = Path(part_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Part file not found: {path}")
    if not system_prompt.strip():
        raise ValueError("system_prompt must not be empty")

    workspace = path.parent
    api_key = load_api_key()
    source_text = path.read_text(encoding="utf-8")
    initial_fingerprint = _fingerprint_file(path)
    user_message = _build_user_message(path, system_prompt)

    try:
        with launch_bridge_session(str(workspace), timeout=timeout) as bridge:
            agent_context = bridge.client.agents.create(
                model=MODEL_SELECTION,
                api_key=api_key,
                local=LocalAgentOptions(cwd=str(workspace)),
            )
            agent = agent_context.__enter__()
            close_agent = True
            try:
                run = agent.send(user_message)
                result = _wait_run(
                    run,
                    timeout,
                    part_path=path,
                    initial_fingerprint=initial_fingerprint,
                    source_text=source_text,
                )
                if result is None:
                    close_agent = False
                    bridge.terminate()
                    return
            finally:
                if close_agent:
                    agent_context.__exit__(None, None, None)
    except CursorAgentError as err:
        raise RuntimeError(f"SDK error: {err.message}") from err

    if result.status == "error":
        raise RuntimeError(f"Agent run failed: {result.id}")

    _assert_non_fast_model(result)
