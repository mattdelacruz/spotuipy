from textual.widgets import Static, ProgressBar
from textual.app import ComposeResult
from textual.timer import Timer
from widgets import CurrentSong

class PlayerControls(Static):
    # spacebar: play/pause current song
    BINDINGS = [
        ("a", "start", "Start"),
    ]

    progress_timer: Timer

    def __init__(self):
        super().__init__()
    
    def compose(self) -> ComposeResult:
        yield CurrentSong()
        yield ProgressBar()
    
    def on_mount(self) -> None:
        """Set up a timer to simulate progess happening."""
        self.progress_timer = self.set_interval(1, self.make_progress, pause=True)

    def make_progress(self) -> None:
        """Called automatically to advance the progress bar."""
        self.query_one(ProgressBar).advance(1)

    def action_start(self) -> None:
        """Start the progress tracking."""
        print('hello!')
        self.query_one(ProgressBar).update(total=100)
        self.progress_timer.resume()