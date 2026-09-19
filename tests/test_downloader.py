from pathlib import Path
from threading import Event
from typing import Any

from frdlp.downloader import OUTPUT_TEMPLATE, YtDlpRunner, build_ydl_options, EventLogger
from frdlp.events import DownloadEvent, EventKind
from frdlp.presets import PRESETS


class FakeYoutubeDL:
    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options

    def __enter__(self) -> "FakeYoutubeDL":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def download(self, urls: list[str]) -> int:
        assert urls == ["https://example.test/video"]
        info = {
            "title": "A video",
            "playlist_index": 2,
            "playlist_count": 3,
            "filepath": "/downloads/A playlist/A video [abc].webm",
        }
        self.options["logger"].info("Downloading metadata")
        self.options["progress_hooks"][0](
            {
                "status": "downloading",
                "downloaded_bytes": 50,
                "total_bytes": 100,
                "speed": 10,
                "eta": 5,
                "filename": info["filepath"],
                "info_dict": info,
            }
        )
        self.options["progress_hooks"][0](
            {"status": "finished", "filename": info["filepath"], "info_dict": info}
        )
        self.options["postprocessor_hooks"][0](
            {"status": "started", "postprocessor": "MoveFiles", "info_dict": info}
        )
        self.options["post_hooks"][0](info["filepath"])
        return 0


class FailingYoutubeDL(FakeYoutubeDL):
    def download(self, urls: list[str]) -> int:
        raise RuntimeError("network unavailable")


def test_output_template_only_adds_directory_for_playlists(tmp_path: Path) -> None:
    from yt_dlp import YoutubeDL

    ydl = YoutubeDL(
        {
            "paths": {"home": str(tmp_path)},
            "outtmpl": {"default": OUTPUT_TEMPLATE},
            "quiet": True,
        }
    )
    single = Path(
        ydl.prepare_filename({"title": "One", "id": "abc", "ext": "mp4"})
    )
    playlist = Path(
        ydl.prepare_filename(
            {
                "title": "Episode",
                "id": "def",
                "ext": "webm",
                "playlist": "My Playlist",
            }
        )
    )

    assert single.resolve().parent == tmp_path.resolve()
    assert playlist.parent.name == "My Playlist"
    assert playlist.parent.parent == tmp_path


def test_options_preserve_partial_and_completed_files(tmp_path: Path) -> None:
    options = build_ydl_options(
        tmp_path,
        PRESETS["mp4"],
        lambda data: None,
        lambda data: None,
        lambda path: None,
        EventLogger(lambda event: None),
    )
    assert options["paths"] == {"home": str(tmp_path)}
    assert options["continuedl"] is True
    assert options["nopart"] is False
    assert options["overwrites"] is False


def test_runner_translates_yt_dlp_callbacks(tmp_path: Path) -> None:
    events: list[DownloadEvent] = []
    runner = YtDlpRunner(
        tmp_path,
        "https://example.test/video",
        PRESETS["webm"],
        Event(),
        events.append,
        FakeYoutubeDL,
    )
    runner.run()

    kinds = [event.kind for event in events]
    assert EventKind.PROGRESS in kinds
    assert EventKind.LOG in kinds
    assert EventKind.OUTPUT in kinds
    assert kinds[-1] is EventKind.COMPLETE
    progress = next(event for event in events if event.kind is EventKind.PROGRESS)
    assert progress.playlist_index == 2
    assert progress.playlist_count == 3
    assert events[-1].final_paths == (
        "/downloads/A playlist/A video [abc].webm",
    )


def test_runner_reports_failures(tmp_path: Path) -> None:
    events: list[DownloadEvent] = []
    runner = YtDlpRunner(
        tmp_path,
        "https://example.test/video",
        PRESETS["best"],
        Event(),
        events.append,
        FailingYoutubeDL,
    )
    runner.run()
    assert events[-1] == DownloadEvent(EventKind.ERROR, message="network unavailable")


def test_runner_reports_cancellation_and_keeps_it_distinct(tmp_path: Path) -> None:
    events: list[DownloadEvent] = []
    cancelled = Event()
    cancelled.set()
    runner = YtDlpRunner(
        tmp_path,
        "https://example.test/video",
        PRESETS["best"],
        cancelled,
        events.append,
        FakeYoutubeDL,
    )
    runner.run()
    assert events[-1].kind is EventKind.CANCELLED
