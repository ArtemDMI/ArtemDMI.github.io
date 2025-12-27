import os
import random
import string
import subprocess
import sys


def _project_root() -> str:
    # .../start/copy_from_winbuffer/copy_from_winbuffer.py -> project root is 2 levels up
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(script_dir))


def _get_clipboard_text() -> str:
    # Prefer stdlib-only tkinter (fast, no extra process). Fallback to PowerShell for edge cases.
    try:
        import tkinter  # type: ignore

        r = tkinter.Tk()
        r.withdraw()
        try:
            return r.clipboard_get()
        finally:
            r.destroy()
    except Exception:
        # PowerShell fallback (Windows)
        cp = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if cp.returncode != 0:
            stderr = (cp.stderr or "").strip()
            raise RuntimeError(f"Failed to read clipboard via PowerShell. {stderr}".strip())
        return cp.stdout


def _random_name(existing_lower: set[str], length: int = 6, prefix: str = "N") -> str:
    # Example: N7sd6D.md (prefix + (length-1) random chars)
    alphabet = string.ascii_letters + string.digits
    for _ in range(1000):
        name = prefix + "".join(random.choice(alphabet) for _ in range(max(1, length - 1)))
        filename = f"{name}.md"
        if filename.lower() not in existing_lower:
            return filename
    # Extremely unlikely fallback
    return f"{prefix}{os.urandom(4).hex()}.md"


def main() -> int:
    root = _project_root()
    out_dir = os.path.join(root, "sources", "new")
    os.makedirs(out_dir, exist_ok=True)

    existing = set()
    try:
        for fn in os.listdir(out_dir):
            existing.add(fn.lower())
    except OSError:
        pass

    text = _get_clipboard_text()

    filename = _random_name(existing_lower=existing, length=6, prefix="N")
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

    print(out_path)
    if not text:
        print("WARNING: Clipboard was empty (created empty file).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


