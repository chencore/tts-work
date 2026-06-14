import pytest

from backend.text_splitter import split_text


def test_empty_text():
    assert split_text("") == []
    assert split_text("   ") == []


def test_short_text_unchanged():
    text = "你好世界。"
    assert split_text(text) == [text]


def test_split_by_sentence():
    text = "第一句。第二句！第三句？"
    chunks = split_text(text, max_chars=8)
    assert len(chunks) == 3
    assert chunks[0] == "第一句。"
    assert chunks[1] == "第二句！"
    assert chunks[2] == "第三句？"


def test_merge_short_sentences():
    text = "短。短。短。"
    chunks = split_text(text, max_chars=20)
    assert len(chunks) == 1
    assert chunks[0] == "短。短。短。"


def test_long_sentence_split_by_clause():
    text = "这是一句非常长的中文句子，包含了很多个分句，以便测试分割逻辑"
    chunks = split_text(text, max_chars=20)
    assert len(chunks) >= 2
    # Each chunk must be within limit.
    assert all(len(c) <= 20 for c in chunks)
    # Re-joined text should be roughly preserved (delimiters stay attached).
    joined = "".join(chunks)
    assert "这是一句非常长的中文句子" in joined


def test_hard_cut_for_very_long_clause():
    text = "a" * 200
    chunks = split_text(text, max_chars=30)
    assert all(len(c) <= 30 for c in chunks)
    assert "".join(chunks) == text
