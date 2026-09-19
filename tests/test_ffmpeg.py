from __future__ import annotations

from subprocess import CompletedProcess

import pytest

from frdlp import ffmpeg
from frdlp.presets import PRESETS


def test_validate_ffmpeg_reports_missing_executables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda executable: None)

    message = ffmpeg.validate_ffmpeg(PRESETS["mp3"])

    assert message is not None
    assert "ffmpeg and ffprobe are not available on PATH" in message


def test_validate_ffmpeg_accepts_required_encoder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(
        ffmpeg.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, " A....D libmp3lame\n", ""),
    )

    assert ffmpeg.validate_ffmpeg(PRESETS["mp3"]) is None


def test_validate_ffmpeg_reports_missing_requested_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(
        ffmpeg.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, " A....D aac\n", ""),
    )

    message = ffmpeg.validate_ffmpeg(PRESETS["mp3"])

    assert message is not None
    assert "missing encoder: libmp3lame" in message


@pytest.mark.parametrize(
    ("preset", "encoders"),
    [
        ("m4a", "aac"),
        ("m4a", "libfdk_aac"),
        ("wav", "pcm_s16le"),
        ("flac", "flac"),
        ("opus", "libopus"),
    ],
)
def test_validate_ffmpeg_supports_each_audio_preset(
    monkeypatch: pytest.MonkeyPatch, preset: str, encoders: str
) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(
        ffmpeg.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, f" A....D {encoders}\n", ""),
    )

    assert ffmpeg.validate_ffmpeg(PRESETS[preset]) is None


def test_validate_ffmpeg_skips_native_and_video_presets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(ffmpeg.subprocess, "run", lambda *args, **kwargs: pytest.fail("ran"))

    assert ffmpeg.validate_ffmpeg(PRESETS["best"]) is None
    assert ffmpeg.validate_ffmpeg(PRESETS["webm"]) is None


@pytest.mark.parametrize(
    ("platform", "available", "expected"),
    [
        ("win32", set(), "winget install Gyan.FFmpeg"),
        ("darwin", {"brew"}, "brew install ffmpeg"),
        ("linux", {"apt"}, "sudo apt update && sudo apt install ffmpeg"),
        ("linux", {"dnf"}, "sudo dnf install ffmpeg"),
        ("linux", {"pacman"}, "sudo pacman -S ffmpeg"),
        ("linux", {"zypper"}, "sudo zypper install ffmpeg"),
    ],
)
def test_platform_commands(platform: str, available: set[str], expected: str) -> None:
    assert ffmpeg._platform_command("mp3", which=lambda name: "/bin/x" if name in available else None, platform=platform) == expected


def test_portage_mp3_command_enables_lame() -> None:
    command = ffmpeg._platform_command("mp3", which=lambda name: "/bin/emerge" if name == "emerge" else None, platform="linux")

    assert command is not None
    assert "media-video/ffmpeg lame" in command
    assert "emerge --ask --changed-use media-video/ffmpeg" in command


def test_unknown_platform_has_download_page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ffmpeg, "_platform_command", lambda preset_name: None)

    assert "https://ffmpeg.org/download.html" in ffmpeg.installation_guidance("mp3")
