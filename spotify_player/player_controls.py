from textual.widgets import Static, ProgressBar
from textual.app import ComposeResult
from textual.timer import Timer
from textual.containers import Horizontal, Vertical
from tools.widgets import CurrentTrack, TrackProgress, AlbumCover, CurrentTrackLabel
from textual_image.widget import Image as AlbumImage


class PlayerControls(Static):
    # spacebar: play/pause current song
    BINDINGS = [
    ]

    progress_timer: Timer

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield AlbumCover()
            with Vertical():
                yield CurrentTrack()
                yield TrackProgress()
        yield CurrentTrackLabel(label="", id="track-device")
