"""Friendly filetype presets and their yt-dlp configuration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class FormatPreset:
    name: str
    format_selector: str
    postprocessors: tuple[Mapping[str, Any], ...] = ()
    merge_output_format: str | None = None
    audio_codec: str | None = None

    def ydl_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {"format": self.format_selector}
        if self.postprocessors:
            options["postprocessors"] = [dict(item) for item in self.postprocessors]
        if self.merge_output_format:
            options["merge_output_format"] = self.merge_output_format
        if self.audio_codec:
            options["postprocessor_args"] = {
                "merger+ffmpeg_o": ["-c:a", self.audio_codec]
            }
        return options


def _video(name: str) -> FormatPreset:
    return FormatPreset(
        name=name,
        format_selector="bv*+ba/b",
        merge_output_format=name,
        postprocessors=(
            {"key": "FFmpegVideoConvertor", "preferedformat": name},
        ),
        audio_codec="aac",
    )


def _audio(name: str) -> FormatPreset:
    return FormatPreset(
        name=name,
        format_selector="ba/b",
        postprocessors=(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": name,
                "preferredquality": "0",
            },
        ),
    )


AUDIO_CODECS = ("aac", "mp3", "m4a", "wav", "flac", "opus")


PRESETS: Mapping[str, FormatPreset] = MappingProxyType(
    {
        "best": FormatPreset("best", "bv*+ba/b"),
        "audio": FormatPreset("audio", "ba/b"),
        **{name: _video(name) for name in ("mp4", "webm", "mkv", "mov")},
        **{name: _audio(name) for name in AUDIO_CODECS},
    }
)


def parse_preset(value: str) -> FormatPreset:
    """Return a preset from a case-insensitive CLI value."""
    try:
        return PRESETS[value.casefold()]
    except KeyError as error:
        choices = ", ".join(PRESETS)
        raise ValueError(f"unsupported filetype {value!r}; choose one of: {choices}") from error


def with_audio_codec(preset: FormatPreset, codec: FormatPreset) -> FormatPreset:
    """Apply an audio-codec override while preserving a video output type."""
    if preset.merge_output_format:
        return replace(preset, audio_codec=codec.name)
    return codec
