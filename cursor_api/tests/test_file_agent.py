"""Минимальные проверки file_agent без реального API."""

from __future__ import annotations

import io
import contextlib
import tempfile
import unittest
from pathlib import Path

from file_agent import cli, normalization, pipeline, split, validation
from file_agent.runner import SystemPromptNotSupportedError


class NormalizationTests(unittest.TestCase):
    def test_short_english_with_blank_lines(self) -> None:
        raw = (
            "This first sentence has enough words to stay separate.\n\n\n"
            "This second sentence also has enough words here.\n\n   \n"
            "This third sentence has enough words as well."
        )
        result = normalization.normalize_text(raw)
        self.assertEqual(
            result,
            "This first sentence has enough words to stay separate.\n"
            "This second sentence also has enough words here.\n"
            "This third sentence has enough words as well.",
        )
        self.assertNotIn("\n\n", result)

    def test_empty_input_raises(self) -> None:
        with self.assertRaises(ValueError):
            normalization.normalize_text("   \n\n")


class SplitTests(unittest.TestCase):
    def test_part_paths(self) -> None:
        source = Path("sources/15/test.txt")
        self.assertEqual(
            split.part_paths(source, 2),
            [
                source,
                Path("sources/15/testS001.txt"),
                Path("sources/15/testS002.txt"),
            ],
        )
        self.assertEqual(split.part_paths(source, 0), [source])

    def test_limits_on_many_sentences(self) -> None:
        sentences = [f"Sentence number {i} is here today." for i in range(200)]
        parts = split.split_normalized("\n".join(sentences))
        self.assertGreaterEqual(len(parts), 2)
        for part in parts:
            lines = [line for line in part.splitlines() if line.strip()]
            self.assertLessEqual(len(lines), 150)
            if len(lines) > 1:
                self.assertLessEqual(len(part), 5000)

    def test_oversized_single_sentence_is_own_part(self) -> None:
        long_sentence = "X" * 6000
        parts = split.split_normalized(f"Short.\n{long_sentence}\nTail.")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[1]), 6000)


class SplitConflictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_check_split_conflicts_detects_orphan_suffix(self) -> None:
        source = self.root / "test.txt"
        source.write_text("a", encoding="utf-8")
        (self.root / "testS002.txt").write_text("orphan", encoding="utf-8")
        paths = split.part_paths(source, 1)

        with self.assertRaises(ValueError) as ctx:
            split.check_split_conflicts(source, paths)

        self.assertIn("Split conflicts", str(ctx.exception))
        self.assertIn("testS002.txt", str(ctx.exception))

    def test_write_parts_raises_on_split_conflict(self) -> None:
        source = self.root / "test.txt"
        (self.root / "testS002.txt").write_text("orphan", encoding="utf-8")
        parts = [
            "First sentence has enough words to stay separate.",
            "Second sentence also has enough words here today.",
        ]

        with self.assertRaises(ValueError) as ctx:
            split.write_parts(source, parts)

        self.assertIn("Split conflicts", str(ctx.exception))


class CliArgparseTests(unittest.TestCase):
    def test_run_without_mode_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["run", "file.txt"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_run_with_both_modes_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["run", "file.txt", "-t", "-merge"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_translate_without_story_context_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["run", "file.txt", "-t"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_run_with_extra_file_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["run", "file1.txt", "file2.txt", "-t"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_relative_file_resolves_from_repo_root(self) -> None:
        self.assertEqual(
            cli._resolve_source_path("sources/15/test.txt"),
            (cli.REPO_ROOT / "sources/15/test.txt").resolve(),
        )


class MergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_merge_order_and_join_format(self) -> None:
        source = self.root / "test.txt"
        source.write_text("part one", encoding="utf-8")
        (self.root / "testS001.txt").write_text("part two", encoding="utf-8")
        (self.root / "testS002.txt").write_text("part three", encoding="utf-8")

        with contextlib.redirect_stdout(io.StringIO()):
            code = pipeline.run_merge(source)

        self.assertEqual(code, 0)
        self.assertEqual(
            source.read_text(encoding="utf-8"),
            "part one\n\npart two\n\npart three",
        )
        self.assertFalse((self.root / "testS001.txt").is_file())
        self.assertFalse((self.root / "testS002.txt").is_file())

    def test_merge_gap_in_suffix_numbering_fails(self) -> None:
        source = self.root / "gap.txt"
        source.write_text("a", encoding="utf-8")
        (self.root / "gapS001.txt").write_text("b", encoding="utf-8")
        (self.root / "gapS003.txt").write_text("c", encoding="utf-8")

        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            stderr
        ):
            code = pipeline.run_merge(source)

        self.assertEqual(code, 1)
        self.assertIn("Gap in part numbering", stderr.getvalue())


class ValidationTests(unittest.TestCase):
    def test_ok_ratio_range(self) -> None:
        result = validation.validate_translation("abcdefghij", "abcdef")
        self.assertTrue(result.ok)
        self.assertEqual(result.status, "ok")

        exact_high = validation.validate_translation("abcdefghij", "abcdefghijabcd")
        self.assertTrue(exact_high.ok)

    def test_too_short_below_060(self) -> None:
        result = validation.validate_translation("hello world test", "xxxxxx")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "too_short")

    def test_too_long_above_140(self) -> None:
        result = validation.validate_translation("hello world test", "x" * 20)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "too_long")


class PipelinePartialFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_runner = pipeline.run_part_fn
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(setattr, pipeline, "run_part_fn", self._original_runner)
        self.root = Path(self.temp_dir.name)

    def test_partial_failure_keeps_successful_parts_nonzero_exit(self) -> None:
        lines = [f"Sentence number {i} is here today." for i in range(200)]
        source = self.root / "test.txt"
        source.write_text("\n".join(lines), encoding="utf-8")

        def fake_run_part(part_path: Path, *, system_prompt: str, timeout: float = 60) -> None:
            if "S001" in part_path.name:
                raise RuntimeError("simulated agent failure")
            text = part_path.read_text(encoding="utf-8")
            size = validation.count_non_whitespace(text)
            part_path.write_text("y" * size, encoding="utf-8")

        pipeline.run_part_fn = fake_run_part

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 1)
        self.assertTrue((self.root / "testS001.txt").is_file())
        self.assertNotEqual(source.read_text(encoding="utf-8"), "\n".join(lines))
        summary = stdout.getvalue()
        self.assertIn("Успешно: 1", summary)
        self.assertIn("Ошибки: 1", summary)

    def test_system_prompt_not_supported_fails_all_parts(self) -> None:
        lines = [f"Sentence number {i} is here today." for i in range(200)]
        source = self.root / "test.txt"
        source.write_text("\n".join(lines), encoding="utf-8")

        def fake_run_part(
            part_path: Path, *, system_prompt: str, timeout: float = 60
        ) -> None:
            raise SystemPromptNotSupportedError("system prompt unsupported")

        pipeline.run_part_fn = fake_run_part

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 1)
        summary = stdout.getvalue()
        self.assertIn("Успешно: 0", summary)
        self.assertIn("Ошибки: 2", summary)
        self.assertIn("system prompt unsupported", summary)

    def test_translation_blank_lines_are_removed(self) -> None:
        source = self.root / "test.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")

        def fake_run_part(part_path: Path, *, system_prompt: str, timeout: float = 60) -> None:
            part_path.write_text(
                "\nSentence number one is here today.\n\n\n",
                encoding="utf-8",
            )

        pipeline.run_part_fn = fake_run_part

        with contextlib.redirect_stdout(io.StringIO()):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 0)
        self.assertEqual(
            source.read_text(encoding="utf-8"),
            "Sentence number one is here today.",
        )

    def test_story_context_is_prepended_to_system_prompt(self) -> None:
        source = self.root / "test.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")
        seen_prompts: list[str] = []

        def fake_run_part(
            part_path: Path, *, system_prompt: str, timeout: float = 60
        ) -> None:
            seen_prompts.append(system_prompt)
            text = part_path.read_text(encoding="utf-8")
            part_path.write_text(text, encoding="utf-8")

        pipeline.run_part_fn = fake_run_part

        with contextlib.redirect_stdout(io.StringIO()):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 0)
        self.assertTrue(seen_prompts)
        self.assertIn("# Story Context", seen_prompts[0])
        self.assertIn("Rachel, a woman", seen_prompts[0])
        self.assertLess(
            seen_prompts[0].index("# Story Context"),
            seen_prompts[0].index("# Translation Instructions"),
        )

    def test_story_context_must_be_ascii(self) -> None:
        source = self.root / "test.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")

        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            stderr
        ):
            code = pipeline.run_translate(source, "Это русское описание")

        self.assertEqual(code, 1)
        self.assertIn("English ASCII", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
