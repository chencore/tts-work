"""Unit tests for backend.paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.paths import win_to_wsl2, validate_prompt_audio


def test_win_to_wsl2_simple():
    assert win_to_wsl2("D:\\audio\\ref.wav") == "/mnt/d/audio/ref.wav"


def test_win_to_wsl2_forward_slash():
    assert win_to_wsl2("C:/Users/ck/a.wav") == "/mnt/c/Users/ck/a.wav"


def test_win_to_wsl2_lowercase_drive():
    assert win_to_wsl2("d:\\foo.wav") == "/mnt/d/foo.wav"


def test_win_to_wsl2_rejects_unc():
    with pytest.raises(ValueError, match="不支持的路径格式"):
        win_to_wsl2("\\\\server\\share\\ref.wav")


def test_win_to_wsl2_rejects_relative():
    with pytest.raises(ValueError, match="不支持的路径格式"):
        win_to_wsl2("audio/ref.wav")


def test_validate_prompt_audio_missing_file(tmp_path):
    fake = "/mnt/d/definitely_does_not_exist_xxx.wav"
    with pytest.raises(FileNotFoundError):
        validate_prompt_audio(fake)


def test_validate_prompt_audio_wrong_extension(tmp_path, monkeypatch):
    # 创建临时 .txt 文件，绕过 /mnt/ 文件系统限制（monkeypatch Path）
    fake_wsl2 = tmp_path / "ref.txt"
    fake_wsl2.write_text("not audio")

    # 传入以 /mnt/ 开头的字符串以通过前缀校验；
    # monkeypatch Path 让实际文件解析落到 tmp_path 下的真实 .txt 文件上。
    monkeypatch.setattr("backend.paths.Path", lambda p: tmp_path / Path(p).name)
    with pytest.raises(ValueError, match="不支持的音频格式"):
        validate_prompt_audio("/mnt/d/ref.txt")
