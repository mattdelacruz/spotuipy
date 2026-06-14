from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from tools.widgets import CurrentTrack, TrackProgress, AlbumCover, CurrentTrackLabel


class PlayerControls(Static):
    # spacebar: play/pause current song
    BINDINGS = []

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield AlbumCover()
            with Vertical():
                yield CurrentTrack()
                yield TrackProgress()
        yield CurrentTrackLabel(label="", id="track-device")
