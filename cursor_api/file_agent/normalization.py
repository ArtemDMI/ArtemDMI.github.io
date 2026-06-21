#!/usr/bin/env python3
"""Нормализация текста: одно предложение на строку."""

from __future__ import annotations

import re


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

    pattern = r".+?(?:[.!?…]+[\"'”’)]*|$)(?=\s+(?:[\"'“‘(]*[A-Z0-9])|$)"
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


def merge_short_sentences(sentences: list[str], min_words: int = 8) -> list[str]:
    merged: list[str] = []
    buffer: list[str] = []
    buffer_words = 0

    for sentence in sentences:
        current_words = word_count(sentence)
        if buffer:
            buffer.append(sentence)
            buffer_words += current_words
            if buffer_words >= min_words:
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
        if merged:
            merged[-1] = f"{merged[-1]} {' '.join(buffer)}"
        else:
            merged.append(" ".join(buffer))

    return merged


def normalize_text(text: str) -> str:
    """Схлопнуть переносы и вернуть текст: одно предложение на строку, без пустых строк."""
    if not text.strip():
        raise ValueError("Input text is empty")

    sentences = split_sentences(text)
    if not sentences:
        raise ValueError("No sentences found in input text")

    return "\n".join(sentences)
