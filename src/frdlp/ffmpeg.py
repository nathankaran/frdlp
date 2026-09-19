"""Validate FFmpeg capabilities and explain how to install missing pieces."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Callable

from frdlp.presets import FormatPreset


ENCODERS_BY_PRESET: dict[str, frozenset[str]] = {
    "mp3": frozenset({"libmp3lame"}),
    "m4a": frozenset({"aac", "libfdk_aac"}),
    "wav": frozenset({"pcm_s16le"}),
    "flac": frozenset({"flac"}),
    "opus": frozenset({"libopus"}),
}
_ENCODER_LINE = re.compile(r"^\s*[A-Z.]{6}\s+(\S+)", re.MULTILINE)


def validate_ffmpeg(preset: FormatPreset) -> str | None:
    """Return a user-facing problem message, or ``None`` when FFmpeg is ready."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        missing = [
            name for name, path in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)) if not path
        ]
        names = " and ".join(missing)
        verb = "is" if len(missing) == 1 else "are"
        return _problem_message(f"{names} {verb} not available on PATH.", preset.name)

    required = ENCODERS_BY_PRESET.get(preset.name)
    if not required:
        return None

    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return _problem_message(f"could not inspect FFmpeg encoders: {error}", preset.name)

    if result.returncode:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown error"
        return _problem_message(f"could not inspect FFmpeg encoders: {detail}", preset.name)

    available = set(_ENCODER_LINE.findall(result.stdout))
    if available.intersection(required):
        return None

    wanted = " or ".join(sorted(required))
    return _problem_message(
        f"FFmpeg cannot encode {preset.name.upper()} (missing encoder: {wanted}).",
        preset.name,
    )


def installation_guidance(preset_name: str) -> str:
    """Return manual FFmpeg setup instructions for the current platform."""
    command = _platform_command(preset_name)
    if command:
        return f"Install or rebuild FFmpeg, then restart frdlp:\n{command}"
    return (
        "Install a full FFmpeg build with the required encoder, then restart frdlp.\n"
        "See https://ffmpeg.org/download.html"
    )


def _problem_message(problem: str, preset_name: str) -> str:
    return f"{problem}\n{installation_guidance(preset_name)}"


def _platform_command(
    preset_name: str, *, which: Callable[[str], str | None] = shutil.which, platform: str = sys.platform
) -> str | None:
    if platform.startswith("win"):
        return "winget install Gyan.FFmpeg"
    if platform == "darwin":
        return "brew install ffmpeg" if which("brew") else None
    if not platform.startswith("linux"):
        return None

    if which("emerge"):
        if preset_name == "mp3":
            return (
                "sudo install -d /etc/portage/package.use\n"
                'echo "media-video/ffmpeg lame" | sudo tee /etc/portage/package.use/ffmpeg\n'
                "sudo emerge --ask --changed-use media-video/ffmpeg"
            )
        return "sudo emerge --ask --changed-use media-video/ffmpeg"
    if which("apt"):
        return "sudo apt update && sudo apt install ffmpeg"
    if which("dnf"):
        return "sudo dnf install ffmpeg"
    if which("pacman"):
        return "sudo pacman -S ffmpeg"
    if which("zypper"):
        return "sudo zypper install ffmpeg"
    if which("brew"):
        return "brew install ffmpeg"
    return None
