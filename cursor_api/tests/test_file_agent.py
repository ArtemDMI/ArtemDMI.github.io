"""Минимальные проверки file_agent без реального API."""

from __future__ import annotations

import io
import contextlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from file_agent import cli, normalization, pipeline, runner, split, validation
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

    def test_subtitle_metadata_is_removed_before_sentence_split(self) -> None:
        raw = (
            "1414\n"
            "01:23:41,360 --> 01:23:43,000\n"
            "This subtitle line has enough words to stand alone.\n\n"
            "1415\n"
            "01:23:43,100 --> 01:23:44,020\n"
            "Another subtitle line also has enough words here.\n"
        )

        result = normalization.normalize_text(raw)

        self.assertEqual(
            result,
            "This subtitle line has enough words to stand alone.\n"
            "Another subtitle line also has enough words here.",
        )
        self.assertNotIn("1414", result)
        self.assertNotIn("-->", result)

    def test_numeric_content_is_preserved_for_non_subtitle_text(self) -> None:
        raw = (
            "Version 2 of this plain text line has enough words to stay."
        )

        result = normalization.normalize_text(raw)

        self.assertIn("Version 2", result)

    def test_short_sentences_are_filtered_after_normalization(self) -> None:
        raw = (
            "This first sentence has enough meaningful words to stay.\n"
            "Yes.\n"
            "This second sentence also has enough meaningful words."
        )

        result = normalization.normalize_text(raw)

        self.assertEqual(
            result,
            "This first sentence has enough meaningful words to stay.\n"
            "This second sentence also has enough meaningful words.",
        )
        self.assertNotIn("Yes.", result)

    def test_reddit_metadata_is_removed_before_translation_split(self) -> None:
        raw = (
            "Аватар u/TestUser\n"
            "TestUser\n"
            "•\n"
            "4 дн. назад\n"
            "This comment has enough meaningful words to stay.\n"
            "Нравится\n"
            "42\n"
            "Ответить\n"
        )

        result = normalization.normalize_text(raw)

        self.assertEqual(result, "This comment has enough meaningful words to stay.")
        self.assertNotIn("Аватар", result)
        self.assertNotIn("Нравится", result)


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
        sentences = [f"Sentence number {i} is here today." for i in range(400)]
        parts = split.split_normalized("\n".join(sentences))
        self.assertGreaterEqual(len(parts), 2)
        for part in parts:
            lines = [line for line in part.splitlines() if line.strip()]
            self.assertLessEqual(len(lines), 300)
            if len(lines) > 1:
                self.assertLessEqual(len(part), 10000)

    def test_oversized_single_sentence_is_own_part(self) -> None:
        long_sentence = "X" * 11000
        parts = split.split_normalized(f"Short.\n{long_sentence}\nTail.")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[1]), 11000)

    def test_no_punctuation_uses_12000_char_budget(self) -> None:
        lines = [f"word{i:04d}" for i in range(2400)]
        text = "\n".join(lines)

        parts = split.split_normalized(text)

        self.assertGreaterEqual(len(parts), 2)
        for part in parts:
            self.assertLessEqual(len(part), 12000)

        rebuilt = " ".join(part.strip() for part in parts)
        self.assertEqual(rebuilt, " ".join(lines))

    def test_no_punctuation_does_not_split_only_by_line_count(self) -> None:
        lines = [f"word{i:04d}" for i in range(200)]
        text = "\n".join(lines)

        parts = split.split_normalized(text)

        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0], " ".join(lines))

    def test_few_giant_lines_fall_back_to_12000_char_budget(self) -> None:
        giant = ("word " * 3000).strip() + "."
        medium = ("word " * 400).strip() + "."
        text = "\n".join([giant, medium, "tail."])

        parts = split.split_normalized(text)

        self.assertGreaterEqual(len(parts), 2)
        for part in parts:
            self.assertLessEqual(len(part), 12000)


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
        source.write_text(
            "First sentence is definitely long enough to stay separate.",
            encoding="utf-8",
        )
        (self.root / "testS001.txt").write_text(
            "Second sentence is definitely long enough to stay separate too.",
            encoding="utf-8",
        )
        (self.root / "testS002.txt").write_text(
            "Third sentence is definitely long enough to stay separate as well.",
            encoding="utf-8",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            code = pipeline.run_merge(source)

        self.assertEqual(code, 0)
        self.assertEqual(
            source.read_text(encoding="utf-8"),
            "First sentence is definitely long enough to stay separate.\n"
            "Second sentence is definitely long enough to stay separate too.\n"
            "Third sentence is definitely long enough to stay separate as well.",
        )
        self.assertFalse((self.root / "testS001.txt").is_file())
        self.assertFalse((self.root / "testS002.txt").is_file())

    def test_merge_groups_up_to_four_short_sentences_per_line(self) -> None:
        source = self.root / "short.txt"
        source.write_text("Да.", encoding="utf-8")
        (self.root / "shortS001.txt").write_text("Нет.", encoding="utf-8")
        (self.root / "shortS002.txt").write_text("Ну.", encoding="utf-8")
        (self.root / "shortS003.txt").write_text("Ладно.", encoding="utf-8")
        (self.root / "shortS004.txt").write_text("Потом.", encoding="utf-8")

        with contextlib.redirect_stdout(io.StringIO()):
            code = pipeline.run_merge(source)

        self.assertEqual(code, 0)
        self.assertEqual(
            source.read_text(encoding="utf-8"),
            "Да. Нет. Ну. Ладно.\nПотом.",
        )

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
        self._original_cleanup = pipeline.cleanup_stale_bridges_fn
        self._original_registered_cleanup = pipeline.cleanup_registered_bridges_fn
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(setattr, pipeline, "run_part_fn", self._original_runner)
        self.addCleanup(
            setattr,
            pipeline,
            "cleanup_stale_bridges_fn",
            self._original_cleanup,
        )
        self.addCleanup(
            setattr,
            pipeline,
            "cleanup_registered_bridges_fn",
            self._original_registered_cleanup,
        )
        self.root = Path(self.temp_dir.name)

    def test_partial_failure_keeps_successful_parts_nonzero_exit(self) -> None:
        lines = [f"Sentence number {i} is here today." for i in range(400)]
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
        lines = [f"Sentence number {i} is here today." for i in range(400)]
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

    def test_translation_prints_estimate_and_done_progress(self) -> None:
        source = self.root / "progress.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")

        def fake_run_part(
            part_path: Path, *, system_prompt: str, timeout: float = 60
        ) -> None:
            text = part_path.read_text(encoding="utf-8")
            part_path.write_text(text, encoding="utf-8")

        pipeline.run_part_fn = fake_run_part

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("Оценка до старта:", output)
        self.assertIn("Частей: 1", output)
        self.assertIn("1 - done.", output)
        self.assertIn("Фактически:", output)

    def test_translation_prints_fail_progress(self) -> None:
        source = self.root / "fail.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")

        def fake_run_part(
            part_path: Path, *, system_prompt: str, timeout: float = 60
        ) -> None:
            raise RuntimeError("boom")

        pipeline.run_part_fn = fake_run_part

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 1)
        output = stdout.getvalue()
        self.assertIn("1 - fail (attempt 3: boom).", output)
        self.assertIn("Ошибки: 1", output)

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

    def test_cleanup_stale_bridges_runs_before_translation(self) -> None:
        source = self.root / "test.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")
        events: list[str] = []

        def fake_cleanup() -> int:
            events.append("cleanup")
            return 2

        def fake_run_part(
            part_path: Path, *, system_prompt: str, timeout: float = 60
        ) -> None:
            events.append("run")
            text = part_path.read_text(encoding="utf-8")
            part_path.write_text(text, encoding="utf-8")

        pipeline.cleanup_stale_bridges_fn = fake_cleanup
        pipeline.run_part_fn = fake_run_part

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 0)
        self.assertEqual(events, ["cleanup", "run"])
        self.assertIn(
            "Остановлено cursor-sdk-bridge перед стартом: 2",
            stdout.getvalue(),
        )

    def test_cleanup_registered_bridges_runs_after_translation(self) -> None:
        source = self.root / "test.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")
        events: list[str] = []

        def fake_cleanup() -> int:
            events.append("cleanup-stale")
            return 0

        def fake_registered_cleanup() -> int:
            events.append("cleanup-registered")
            return 0

        def fake_run_part(
            part_path: Path, *, system_prompt: str, timeout: float = 60
        ) -> None:
            events.append("run")
            text = part_path.read_text(encoding="utf-8")
            part_path.write_text(text, encoding="utf-8")

        pipeline.cleanup_stale_bridges_fn = fake_cleanup
        pipeline.cleanup_registered_bridges_fn = fake_registered_cleanup
        pipeline.run_part_fn = fake_run_part

        with contextlib.redirect_stdout(io.StringIO()):
            code = pipeline.run_translate(
                source,
                "This story is about Rachel, a woman traveling with Brad, a man.",
            )

        self.assertEqual(code, 0)
        self.assertEqual(events, ["cleanup-stale", "run", "cleanup-registered"])

    def test_cleanup_registered_bridges_runs_on_unhandled_failure(self) -> None:
        source = self.root / "test.txt"
        source.write_text("Sentence number one is here today.", encoding="utf-8")
        events: list[str] = []

        def fake_cleanup() -> int:
            events.append("cleanup-stale")
            return 0

        def fake_registered_cleanup() -> int:
            events.append("cleanup-registered")
            return 0

        def fake_run_part(
            part_path: Path, *, system_prompt: str, timeout: float = 60
        ) -> None:
            events.append("run")
            text = part_path.read_text(encoding="utf-8")
            part_path.write_text(text, encoding="utf-8")

        original_as_completed = pipeline.concurrent.futures.as_completed

        def fake_as_completed(futures):
            raise RuntimeError("future loop crashed")
            yield from futures

        pipeline.cleanup_stale_bridges_fn = fake_cleanup
        pipeline.cleanup_registered_bridges_fn = fake_registered_cleanup
        pipeline.run_part_fn = fake_run_part
        self.addCleanup(
            setattr,
            pipeline.concurrent.futures,
            "as_completed",
            original_as_completed,
        )
        pipeline.concurrent.futures.as_completed = fake_as_completed

        with self.assertRaises(RuntimeError) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                pipeline.run_translate(
                    source,
                    "This story is about Rachel, a woman traveling with Brad, a man.",
                )

        self.assertIn("future loop crashed", str(ctx.exception))
        self.assertEqual(events, ["cleanup-stale", "run", "cleanup-registered"])

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


class RunnerModelSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.part = self.root / "part.txt"
        self.part.write_text("Source text.", encoding="utf-8")

        self._original_launch_bridge_client = runner.launch_bridge_client
        self._original_load_api_key = runner.load_api_key
        self._original_wait_run = runner._wait_run
        self.addCleanup(
            setattr,
            runner,
            "launch_bridge_client",
            self._original_launch_bridge_client,
        )
        self.addCleanup(setattr, runner, "load_api_key", self._original_load_api_key)
        self.addCleanup(setattr, runner, "_wait_run", self._original_wait_run)

    def test_run_part_requests_non_fast_composer(self) -> None:
        captured: dict[str, object] = {}

        class FakeAgent:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def send(self, message: str):
                captured["message"] = message
                return SimpleNamespace(id="run-1")

        class FakeClient:
            def __init__(self) -> None:
                self.agents = self

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def create(self, *, model, api_key, local):
                captured["model"] = model
                captured["api_key"] = api_key
                captured["cwd"] = local.cwd
                return FakeAgent()

        def fake_launch_bridge_client(workspace: str, *, timeout: float = 60.0):
            captured["workspace"] = workspace
            captured["timeout"] = timeout
            return FakeClient()

        runner.launch_bridge_client = fake_launch_bridge_client
        runner.load_api_key = lambda: "secret"
        runner._wait_run = lambda run, timeout: SimpleNamespace(
            id=run.id,
            status="finished",
            result="OK",
            model=runner.MODEL_SELECTION,
        )

        runner.run_part(self.part, system_prompt="Translate this story.", timeout=12)

        model = captured["model"]
        self.assertEqual(model.id, "composer-2.5")
        self.assertEqual(len(model.params), 1)
        self.assertEqual(model.params[0].id, "fast")
        self.assertEqual(model.params[0].value, "false")
        self.assertEqual(captured["workspace"], str(self.root))
        self.assertEqual(captured["cwd"], str(self.root))
        self.assertIn("Обработай файл на диске", captured["message"])

    def test_run_part_rejects_fast_resolved_model(self) -> None:
        class FakeAgent:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def send(self, message: str):
                return SimpleNamespace(id="run-fast")

        class FakeClient:
            def __init__(self) -> None:
                self.agents = self

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def create(self, *, model, api_key, local):
                return FakeAgent()

        runner.launch_bridge_client = lambda workspace, timeout=60.0: FakeClient()
        runner.load_api_key = lambda: "secret"
        runner._wait_run = lambda run, timeout: SimpleNamespace(
            id=run.id,
            status="finished",
            result="OK",
            model=SimpleNamespace(
                id="composer-2.5",
                params=(SimpleNamespace(id="fast", value="true"),),
            ),
        )

        with self.assertRaises(RuntimeError) as ctx:
            runner.run_part(self.part, system_prompt="Translate this story.", timeout=12)

        self.assertIn("fast variant", str(ctx.exception))


class EstimateTests(unittest.TestCase):
    def test_build_translation_estimate_includes_start_pauses(self) -> None:
        estimate = pipeline._build_translation_estimate(4)

        self.assertEqual(estimate.part_count, 4)
        self.assertEqual(estimate.launch_pause_count, 3)
        self.assertAlmostEqual(
            estimate.launch_pause_seconds,
            3 * pipeline.REQUEST_PAUSE_SECONDS,
        )
        self.assertAlmostEqual(
            estimate.estimated_wall_seconds,
            pipeline.ESTIMATED_PART_SECONDS + 3 * pipeline.REQUEST_PAUSE_SECONDS,
        )


if __name__ == "__main__":
    unittest.main()
