from __future__ import annotations

import argparse
from pathlib import Path


def is_fence_line(line: str) -> bool:
    # Typical Markdown fence. We keep it simple: any line starting with ``` toggles.
    return line.lstrip().startswith("```")


def is_blank_line(line: str) -> bool:
    return line.strip() == ""


def split_md(
    *,
    input_path: Path,
    output_dir: Path,
    base_name: str,
    target_lines: int,
    overwrite: bool,
) -> list[Path]:
    text = input_path.read_text(encoding="utf-8", errors="strict")
    # Keep original newlines as much as possible.
    lines = text.splitlines(keepends=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    part = 1
    out_paths: list[Path] = []

    buf: list[str] = []
    line_count = 0
    in_fence = False

    def flush() -> None:
        nonlocal part, buf, line_count
        if not buf:
            return
        out_name = f"{base_name} Part {part:03d}.md"
        out_path = output_dir / out_name
        if out_path.exists() and not overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing file: {out_path}. "
                f"Re-run with --overwrite to replace."
            )
        out_path.write_text("".join(buf), encoding="utf-8", errors="strict")
        out_paths.append(out_path)
        part += 1
        buf = []
        line_count = 0

    for line in lines:
        buf.append(line)
        line_count += 1

        if is_fence_line(line):
            in_fence = not in_fence

        # Once we reached the target size, keep going until the next paragraph break,
        # but never split while inside a code fence.
        if line_count >= target_lines and (not in_fence) and is_blank_line(line):
            flush()

    # Flush any remaining content (even if last paragraph doesn't end with blank line).
    flush()

    return out_paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split a big Markdown file into parts of N lines, extending to the end of the paragraph."
    )
    parser.add_argument(
        "--input",
        default="Ascendance.md",
        help="Input markdown file path (default: Ascendance.md)",
    )
    parser.add_argument(
        "--output-dir",
        default="Ascendance_parts",
        help="Output directory (default: Ascendance_parts)",
    )
    parser.add_argument(
        "--target-lines",
        type=int,
        default=500,
        help="Target lines per part before extending to next blank line (default: 500)",
    )
    parser.add_argument(
        "--base-name",
        default=None,
        help="Base name for parts (default: input filename without extension)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing part files if they already exist",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_dir = Path(args.output_dir)
    base_name = args.base_name or input_path.stem

    out_paths = split_md(
        input_path=input_path,
        output_dir=output_dir,
        base_name=base_name,
        target_lines=args.target_lines,
        overwrite=args.overwrite,
    )

    print(f"[OK] Created {len(out_paths)} files in: {output_dir.resolve()}")
    if out_paths:
        print(f"[OK] First: {out_paths[0].name}")
        print(f"[OK] Last:  {out_paths[-1].name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


