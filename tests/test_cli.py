from pathlib import Path

import pytest

from frdlp.cli import build_parser, main, prepare_destination
from frdlp.presets import PRESETS


def test_parser_accepts_requested_interface() -> None:
    args = build_parser().parse_args(["downloads", "https://example.test/v", "MP3"])
    assert args.destination == "downloads"
    assert args.url == "https://example.test/v"
    assert args.filetype is PRESETS["mp3"]


def test_parser_rejects_extra_options() -> None:
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(
            ["downloads", "https://example.test/v", "mp4", "--cookies", "x"]
        )
    assert error.value.code == 2


def test_prepare_destination_creates_and_resolves_path(tmp_path: Path) -> None:
    destination = prepare_destination(str(tmp_path / "new" / "downloads"))
    assert destination.is_dir()
    assert destination.is_absolute()


def test_prepare_destination_rejects_file(tmp_path: Path) -> None:
    target = tmp_path / "a-file"
    target.write_text("content")
    with pytest.raises(ValueError, match="cannot create destination|not a directory"):
        prepare_destination(str(target))


def test_non_interactive_terminal_returns_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("frdlp.cli.terminal_is_interactive", lambda: False)
    monkeypatch.setattr("frdlp.cli.validate_ffmpeg", lambda preset: None)
    result = main([str(tmp_path), "https://example.test/v", "best"])
    assert result == 2
    assert "interactive terminal is required" in capsys.readouterr().err


def test_missing_ffmpeg_returns_preflight_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("frdlp.cli.validate_ffmpeg", lambda preset: "ffmpeg is not available")
    result = main([str(tmp_path), "https://example.test/v", "best"])
    assert result == 2
    assert "ffmpeg is not available" in capsys.readouterr().err
