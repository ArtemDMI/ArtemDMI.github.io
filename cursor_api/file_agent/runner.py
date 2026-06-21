"""Запуск одного Cursor Agent (composer-2.5) на одну часть файла."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

from cursor_sdk import CursorAgentError, LocalAgentOptions, RunResult

from file_agent.bridge_launch import launch_bridge_client
from file_agent.keys import load_api_key

MODEL_ID = "composer-2.5"


class SystemPromptNotSupportedError(RuntimeError):
    """cursor_sdk не умеет задавать system prompt корневому агенту."""


def _build_user_message(part_path: Path, system_prompt: str) -> str:
    # SDK не принимает root system prompt — инструкция из prompt.md идёт в user message.
    return (
        f"{system_prompt.strip()}\n\n"
        "---\n"
        f"Обработай файл на диске: {part_path}\n"
        "Переведи его содержимое на русский и упрости согласно инструкции выше.\n"
        "Перезапиши этот же файл результатом."
    )


def _wait_run(run, timeout: float) -> RunResult:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run.wait)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as err:
            try:
                run.cancel()
            except Exception:
                pass
            raise TimeoutError(
                f"Agent run exceeded {timeout}s timeout for run {run.id}"
            ) from err


def run_part(part_path: Path, *, system_prompt: str, timeout: float = 90) -> None:
    """Запускает одного агента для одной части; ошибка — исключение, без fallback."""
    path = Path(part_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Part file not found: {path}")
    if not system_prompt.strip():
        raise ValueError("system_prompt must not be empty")

    workspace = path.parent
    api_key = load_api_key()
    user_message = _build_user_message(path, system_prompt)

    try:
        with launch_bridge_client(str(workspace), timeout=timeout) as client:
            with client.agents.create(
                model=MODEL_ID,
                api_key=api_key,
                local=LocalAgentOptions(cwd=str(workspace)),
            ) as agent:
                run = agent.send(user_message)
                result = _wait_run(run, timeout)
    except CursorAgentError as err:
        raise RuntimeError(f"SDK error: {err.message}") from err

    if result.status == "error":
        raise RuntimeError(f"Agent run failed: {result.id}")
