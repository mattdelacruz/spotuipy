from spotify_api.spotify_client import SpotifyClient
from tools.playback_monitor import PlaybackMonitor

SP = SpotifyClient.get_instance()


class SeekController:
    """Owns scrubbing/seeking for the player.

    Keeps the progress bar responsive by updating it locally on each keypress,
    debounces the actual Spotify seek so rapid presses collapse into one API
    call, and runs that call off the UI thread. Extracted from Player to keep
    seeking logic in one place.
    """

    SEEK_INTERVAL_MS = 10000  # 10 seconds per press

    def __init__(self, owner, track_progress) -> None:
        # owner is the Player widget, used for its timer/worker/app helpers.
        self._owner = owner
        self._track_progress = track_progress
        self._seek_timer = None
        self._pending_seek_ms = None

    def seek_forward(self) -> None:
        self._seek_relative(self.SEEK_INTERVAL_MS)

    def seek_backward(self) -> None:
        self._seek_relative(-self.SEEK_INTERVAL_MS)

    def _seek_relative(self, delta_ms: int) -> None:
        tp = self._track_progress
        duration_ms = tp.total_time_ms
        if duration_ms <= 0:
            return
        new_ms = max(0, min(tp.progress_ms + delta_ms, duration_ms - 1000))
        # Update the bar instantly; no network call on the keypress path.
        tp.progress_ms = new_ms
        tp.update_progress_bar(new_ms, duration_ms)
        # Suppress the monitor's snap-back while the seek lands.
        self._owner.app.query_one(PlaybackMonitor).notify_seek()
        self._pending_seek_ms = new_ms
        self._schedule_seek()

    def _schedule_seek(self) -> None:
        # Restart the debounce window; the real seek fires once presses settle.
        if self._seek_timer is not None:
            self._seek_timer.stop()
        self._seek_timer = self._owner.set_timer(0.25, self._commit_seek)

    def _commit_seek(self) -> None:
        self._seek_timer = None
        target = self._pending_seek_ms
        if target is None:
            return
        self._pending_seek_ms = None
        self._owner.run_worker(
            lambda: SP.seek_track(target), thread=True, exclusive=True
        )
