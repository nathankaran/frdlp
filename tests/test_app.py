from pathlib import Path

import pytest

from frdlp.app import DownloadApp, _format_bytes, _format_duration
from frdlp.events import DownloadEvent, EventKind
from frdlp.presets import PRESETS


def test_metric_formatters() -> None:
    assert _format_bytes(1536) == "1.5 KiB"
    assert _format_duration(65) == "1:05"
    assert _format_duration(3661) == "1:01:01"


@pytest.mark.asyncio
async def test_dashboard_renders_progress_and_completion(tmp_path: Path) -> None:
    app = DownloadApp(
        tmp_path,
        "https://example.test/video",
        PRESETS["mp4"],
        auto_start=False,
    )
    async with app.run_test() as pilot:
        app.handle_download_event(
            DownloadEvent(
                EventKind.PROGRESS,
                title="Example title",
                stage="Downloading",
                filename="example.part",
                downloaded_bytes=50,
                total_bytes=100,
                speed=10,
                eta=5,
                playlist_index=1,
                playlist_count=2,
            )
        )
        app.handle_download_event(
            DownloadEvent(
                EventKind.COMPLETE,
                final_paths=(str(tmp_path / "example.mp4"),),
            )
        )
        await pilot.pause()
        assert app.finished is True
        assert app.exit_code == 0
        assert "Complete" in str(app.query_one("#stage").render())
        await pilot.press("enter")

