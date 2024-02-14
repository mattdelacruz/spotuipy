from textual.widgets import Static, ProgressBar
from textual.app import ComposeResult
from textual.timer import Timer
from tools.widgets import CurrentTrack, TrackProgress

class PlayerControls(Static):
    # spacebar: play/pause current song
    BINDINGS = [
        ("a", "start", "Start"),
    ]

    progress_timer: Timer

    def __init__(self):
        super().__init__()
    
    def compose(self) -> ComposeResult:
        yield CurrentTrack()
        yield TrackProgress()