"""Split long Chinese/English target text into synthesis chunks.

The dots.tts base model can run out of VRAM when the target text is long.
Splitting at sentence boundaries and synthesizing each segment separately
keeps peak memory low while still using the same reference prompt.
"""

from __future__ import annotations

import re

DEFAULT_MAX_CHUNK_CHARS = 80

# Primary split points: sentence endings.
_SENTENCE_DELIMS = re.compile(r"([。！？；.!?;])")
# Secondary split points: clauses / list items.
_CLAUSE_DELIMS = re.compile(r"([，、,])")


def split_text(text: str, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[str]:
    """Split *text* into chunks no longer than *max_chars* characters.

    The algorithm prefers splitting at sentence boundaries, then clauses,
    and finally hard-cuts any remaining over-long fragment.

    Args:
        text: Target text to synthesize.
        max_chars: Maximum characters per chunk.

    Returns:
        List of non-empty chunks.
    """
    if not text.strip():
        return []

    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""

    # Split by sentence delimiters, keeping the delimiter attached to the
    # preceding sentence so prosody is preserved.
    sentences = [s for s in _SENTENCE_DELIMS.split(text) if s]

    # _SENTENCE_DELIMS.split keeps delimiters as separate items when the
    # pattern has a capture group. Re-assemble (sentence + delimiter) pairs.
    parts: list[str] = []
    i = 0
    while i < len(sentences):
        part = sentences[i]
        if i + 1 < len(sentences) and _SENTENCE_DELIMS.fullmatch(sentences[i + 1]):
            part += sentences[i + 1]
            i += 2
        else:
            i += 1
        parts.append(part)

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue

        if len(stripped) <= max_chars:
            if current and len(current) + len(stripped) + 1 > max_chars:
                chunks.append(current.strip())
                current = stripped
            else:
                current = f"{current}\n{stripped}".strip() if current else stripped
        else:
            # Sentence itself too long: split by clause delimiters.
            if current:
                chunks.append(current.strip())
                current = ""
            current = _split_long_sentence(stripped, max_chars, chunks, current)

    if current:
        chunks.append(current.strip())

    return [c for c in chunks if c]


def _split_long_sentence(
    sentence: str,
    max_chars: int,
    chunks: list[str],
    current: str,
) -> str:
    """Split a sentence that exceeds *max_chars* at clause boundaries."""
    clauses = [s for s in _CLAUSE_DELIMS.split(sentence) if s]

    # Re-assemble (clause + delimiter) pairs.
    parts: list[str] = []
    i = 0
    while i < len(clauses):
        part = clauses[i]
        if i + 1 < len(clauses) and _CLAUSE_DELIMS.fullmatch(clauses[i + 1]):
            part += clauses[i + 1]
            i += 2
        else:
            i += 1
        parts.append(part)

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue

        if len(stripped) <= max_chars:
            if current and len(current) + len(stripped) + 1 > max_chars:
                chunks.append(current.strip())
                current = stripped
            else:
                current = f"{current}{stripped}".strip() if current else stripped
        else:
            # Clause still too long: hard cut.
            if current:
                chunks.append(current.strip())
                current = ""
            current = _hard_cut(stripped, max_chars, chunks, current)

    return current


def _hard_cut(
    text: str,
    max_chars: int,
    chunks: list[str],
    current: str,
) -> str:
    """Force-split *text* into *max_chars* pieces."""
    while text:
        if current and len(current) + 1 + len(text) <= max_chars:
            current = f"{current} {text}".strip()
            break

        available = max_chars - len(current) - 1 if current else max_chars
        if available <= 0:
            chunks.append(current.strip())
            current = ""
            available = max_chars

        take = text[:available]
        text = text[available:].lstrip()
        if current:
            chunks.append(f"{current} {take}".strip())
            current = ""
        else:
            chunks.append(take)

    return current
