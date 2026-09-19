"""Textual download dashboard."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from threading import Event, Thread

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, ProgressBar, RichLog, Static

from frdlp.downloader import YtDlpRunner
from frdlp.events import DownloadEvent, EventKind
from frdlp.presets import FormatPreset


RunnerFactory = Callable[..., YtDlpRunner]


class CancelScreen(ModalScreen[bool]):
    """Confirm cancellation without abruptly killing the worker thread."""

    CSS = """
    CancelScreen {
        align: center middle;
        background: $background 65%;
    }
    #cancel-dialog {
        width: 58;
        height: auto;
        padding: 1 2;
        border: round $warning;
        background: $surface;
    }
    #cancel-question {
        width: 100%;
        margin-bottom: 1;
        text-align: center;
    }
    #cancel-buttons {
        width: 100%;
        height: auto;
        align-horizontal: center;
    }
    #cancel-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="cancel-dialog"):
            yield Static(
                "Cancel this download? Partial files will be kept for resuming.",
                id="cancel-question",
            )
            with Horizontal(id="cancel-buttons"):
                yield Button("Keep downloading", id="keep", variant="primary")
                yield Button("Cancel download", id="cancel", variant="warning")

    @on(Button.Pressed, "#keep")
    def keep_downloading(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#cancel")
    def cancel_download(self) -> None:
        self.dismiss(True)


class DownloadApp(App[int]):
    """Live dashboard for one frdlp invocation."""

    TITLE = "frdlp"
    SUB_TITLE = "yt-dlp download dashboard"
    CSS = """
    Screen {
        background: $background;
    }
    #body {
        padding: 1 2;
    }
    #heading {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    .detail {
        width: 100%;
        height: auto;
        color: $text-muted;
    }
    #stage {
        width: 100%;
        height: auto;
        margin-top: 1;
        text-style: bold;
    }
    #progress {
        margin-top: 1;
        width: 100%;
    }
    #metrics {
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    #log-title {
        width: 100%;
        height: auto;
        margin-top: 1;
        text-style: bold;
    }
    #log {
        height: 1fr;
        min-height: 6;
        border: round $primary-background;
        background: $surface;
    }
    #hint {
        width: 100%;
        height: auto;
        margin-top: 1;
        color: $text-muted;
    }
    """
    BINDINGS = [
        Binding("q", "request_exit", "Quit"),
        Binding("ctrl+c", "request_exit", "Cancel", show=False, priority=True),
        Binding("enter", "accept", "Close", show=False),
    ]

    def __init__(
        self,
        destination: Path,
        url: str,
        preset: FormatPreset,
        runner_factory: RunnerFactory = YtDlpRunner,
        auto_start: bool = True,
    ) -> None:
        super().__init__()
        self.destination = destination
        self.url = url
        self.preset = preset
        self.runner_factory = runner_factory
        self.auto_start = auto_start
        self.cancel_event = Event()
        self.finished = False
        self.exit_code = 1
        self._cancel_dialog_open = False
        self._worker: Thread | None = None
        self._outputs: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="body"):
            yield Static("Preparing download", id="heading", markup=False)
            yield Static(f"URL: {self.url}", classes="detail", markup=False)
            yield Static(
                f"Destination: {self.destination}", classes="detail", markup=False
            )
            yield Static(f"Filetype: {self.preset.name}", classes="detail", markup=False)
            yield Static("Stage: Waiting", id="stage", markup=False)
            yield Static("File: —", id="filename", classes="detail", markup=False)
            yield ProgressBar(total=100, show_eta=False, id="progress")
            yield Static("Waiting for download data…", id="metrics", markup=False)
            yield Static("Recent activity", id="log-title")
            yield RichLog(id="log", wrap=True, highlight=False, markup=False)
            yield Static(
                "Press q or Ctrl+C to cancel.", id="hint", markup=False
            )
        yield Footer()

    def on_mount(self) -> None:
        if self.auto_start:
            self._worker = Thread(target=self._run_download, daemon=True)
            self._worker.start()

    def _run_download(self) -> None:
        runner = self.runner_factory(
            destination=self.destination,
            url=self.url,
            preset=self.preset,
            cancel_event=self.cancel_event,
            emit=self._emit_from_worker,
        )
        runner.run()

    def _emit_from_worker(self, event: DownloadEvent) -> None:
        with suppress(RuntimeError):
            self.call_from_thread(self.handle_download_event, event)

    def handle_download_event(self, event: DownloadEvent) -> None:
        if event.title:
            self.query_one("#heading", Static).update(event.title)
        if event.filename:
            self.query_one("#filename", Static).update(f"File: {event.filename}")
        if event.stage:
            self.query_one("#stage", Static).update(f"Stage: {event.stage}")

        if event.kind is EventKind.PROGRESS:
            self._update_progress(event)
        elif event.kind is EventKind.LOG:
            self.query_one("#log", RichLog).write(event.message)
        elif event.kind is EventKind.OUTPUT:
            if event.filename and event.filename not in self._outputs:
                self._outputs.append(event.filename)
        elif event.kind is EventKind.COMPLETE:
            self._finish_success(event)
        elif event.kind is EventKind.ERROR:
            self._finish_error(event.message)
        elif event.kind is EventKind.CANCELLED:
            self._finish_cancelled(event.message)

    def _update_progress(self, event: DownloadEvent) -> None:
        bar = self.query_one("#progress", ProgressBar)
        downloaded = event.downloaded_bytes or 0
        total = event.total_bytes
        if total and total > 0:
            bar.update(total=100, progress=min(100, downloaded / total * 100))
            size_text = f"{_format_bytes(downloaded)} / {_format_bytes(total)}"
        else:
            bar.update(total=100, progress=0)
            size_text = f"{_format_bytes(downloaded)} / unknown"

        parts = [size_text]
        if event.speed:
            parts.append(f"{_format_bytes(event.speed)}/s")
        if event.eta is not None:
            parts.append(f"ETA {_format_duration(event.eta)}")
        if event.playlist_index is not None:
            count = str(event.playlist_count) if event.playlist_count else "?"
            parts.append(f"item {event.playlist_index}/{count}")
        self.query_one("#metrics", Static).update("  •  ".join(parts))

    def _finish_success(self, event: DownloadEvent) -> None:
        self.finished = True
        self.exit_code = 0
        for path in event.final_paths:
            if path not in self._outputs:
                self._outputs.append(path)
        self.query_one("#stage", Static).update("Stage: Complete")
        self.query_one("#progress", ProgressBar).update(total=100, progress=100)
        if self._outputs:
            self.query_one("#filename", Static).update(
                "Saved: " + (self._outputs[-1] if len(self._outputs) == 1 else f"{len(self._outputs)} files")
            )
            log = self.query_one("#log", RichLog)
            for output in self._outputs:
                log.write(f"Saved: {output}")
        self.query_one("#hint", Static).update("Press Enter or q to exit.")

    def _finish_error(self, message: str) -> None:
        self.finished = True
        self.exit_code = 1
        self.query_one("#stage", Static).update("Stage: Failed")
        self.query_one("#log", RichLog).write(f"Error: {message}")
        self.query_one("#hint", Static).update("Press Enter or q to exit.")

    def _finish_cancelled(self, message: str) -> None:
        self.finished = True
        self.exit_code = 130
        self.query_one("#stage", Static).update("Stage: Cancelled")
        self.query_one("#log", RichLog).write(message)
        self.query_one("#hint", Static).update("Press Enter or q to exit.")

    def action_accept(self) -> None:
        if self.finished:
            self.exit(self.exit_code)

    def action_request_exit(self) -> None:
        if self.finished:
            self.exit(self.exit_code)
        elif not self._cancel_dialog_open:
            self._cancel_dialog_open = True
            self.push_screen(CancelScreen(), self._handle_cancel_choice)

    def _handle_cancel_choice(self, should_cancel: bool | None) -> None:
        self._cancel_dialog_open = False
        if should_cancel:
            self.cancel_event.set()
            self.query_one("#stage", Static).update("Stage: Cancelling…")
            self.query_one("#hint", Static).update(
                "Waiting for yt-dlp to reach a safe stopping point…"
            )


def _format_bytes(value: float | int) -> str:
    amount = float(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if abs(amount) < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{amount:.0f} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"


def _format_duration(seconds: float) -> str:
    remaining = max(0, int(seconds))
    hours, remaining = divmod(remaining, 3600)
    minutes, secs = divmod(remaining, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:d}:{secs:02d}"
