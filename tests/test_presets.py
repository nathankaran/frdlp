import pytest

from frdlp.presets import PRESETS, parse_preset


def test_all_documented_presets_exist() -> None:
    assert set(PRESETS) == {
        "best",
        "audio",
        "mp4",
        "webm",
        "mkv",
        "mov",
        "aac",
        "mp3",
        "m4a",
        "wav",
        "flac",
        "opus",
    }


def test_preset_names_are_case_insensitive() -> None:
    assert parse_preset("MP4") is PRESETS["mp4"]


def test_video_preset_guarantees_requested_format() -> None:
    options = PRESETS["webm"].ydl_options()
    assert options["merge_output_format"] == "webm"
    assert options["postprocessors"] == [
        {"key": "FFmpegVideoConvertor", "preferedformat": "webm"}
    ]


def test_audio_preset_guarantees_requested_codec() -> None:
    options = PRESETS["flac"].ydl_options()
    assert options["format"] == "ba/b"
    assert options["postprocessors"][0]["preferredcodec"] == "flac"


def test_unknown_preset_has_useful_error() -> None:
    with pytest.raises(ValueError, match="unsupported filetype"):
        parse_preset("avi")
