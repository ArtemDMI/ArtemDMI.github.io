#!/usr/bin/env python3
"""Нормализация текста: одно предложение на строку."""

from __future__ import annotations

import re


SUBTITLE_TIMING_RE = re.compile(
    r"^\s*(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3}\s*-->\s*"
    r"(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3}(?:\s+.*)?$"
)
SUBTITLE_INDEX_RE = re.compile(r"^\s*\d+\s*$")

SENTENCE_STARTS = (
    "I",
    "We",
    "You",
    "He",
    "She",
    "It",
    "They",
    "This",
    "That",
    "There",
    "Here",
    "The",
    "A",
    "An",
    "But",
    "And",
    "So",
    "Then",
    "Still",
    "Hell",
    "Yeah",
)


def is_subtitle_timing_line(line: str) -> bool:
    return bool(SUBTITLE_TIMING_RE.fullmatch(line))


def is_subtitle_index_line(line: str) -> bool:
    return bool(SUBTITLE_INDEX_RE.fullmatch(line))


def looks_like_subtitle(text: str) -> bool:
    return any(is_subtitle_timing_line(line) for line in text.splitlines())


def strip_subtitle_metadata(text: str) -> str:
    cleaned: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if is_subtitle_index_line(line) or is_subtitle_timing_line(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_subtitle_text_if_needed(text: str) -> str:
    if not looks_like_subtitle(text):
        return text
    return strip_subtitle_metadata(text)


def normalize_wrapped_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"(?:\.\s*){2,}", ". ", text)
    text = re.sub(r"\.\s+(?=[a-z])", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_without_punctuation(text: str) -> list[str]:
    starts = "|".join(re.escape(start) for start in SENTENCE_STARTS)
    pattern = rf"\s+(?=(?:{starts})\b)"
    return [part.strip() for part in re.split(pattern, text) if part.strip()]


def split_sentences(text: str) -> list[str]:
    text = normalize_wrapped_text(text)
    if not text:
        return []

    if not re.search(r"[.!?…]", text):
        return merge_short_sentences(clean_sentences(split_without_punctuation(text)))

    pattern = r".+?(?:[.!?…]+[\"'”’)]*|$)(?=\s+(?:[\"'“‘(]*[A-ZА-ЯЁ0-9])|$)"
    sentences = [match.group(0).strip() for match in re.finditer(pattern, text)]
    return merge_short_sentences(clean_sentences(sentences))


def clean_sentences(sentences: list[str]) -> list[str]:
    cleaned: list[str] = []
    for sentence in sentences:
        sentence = re.sub(r"\s+", " ", sentence).strip()
        sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
        sentence = re.sub(r"(?:\.\s*){2,}", ".", sentence)
        if not sentence or re.fullmatch(r"[.!?…]+", sentence):
            continue
        cleaned.append(sentence)
    return cleaned


def word_count(text: str) -> int:
    return len(re.findall(r"[\w’']+", text, flags=re.UNICODE))


def merge_short_sentences(
    sentences: list[str], min_words: int = 8, max_sentences_per_line: int = 4
) -> list[str]:
    merged: list[str] = []
    buffer: list[str] = []
    buffer_words = 0

    for sentence in sentences:
        current_words = word_count(sentence)
        if buffer:
            buffer.append(sentence)
            buffer_words += current_words
            # Very short fragments are easier to review in small groups than as
            # single-word lines, but we still cap the group to avoid fat rows.
            if buffer_words >= min_words or len(buffer) >= max_sentences_per_line:
                merged.append(" ".join(buffer))
                buffer = []
                buffer_words = 0
            continue

        if current_words < min_words:
            buffer = [sentence]
            buffer_words = current_words
        else:
            merged.append(sentence)

    if buffer:
        merged.append(" ".join(buffer))

    return merged


def normalize_text(text: str) -> str:
    """Схлопнуть переносы и вернуть текст: одно предложение на строку, без пустых строк."""
    if not text.strip():
        raise ValueError("Input text is empty")

    text = normalize_subtitle_text_if_needed(text)
    sentences = split_sentences(text)
    if not sentences:
        raise ValueError("No sentences found in input text")

    return "\n".join(sentences)
