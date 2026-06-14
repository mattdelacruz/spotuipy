import time
import logging
from textual.message import Message
from textual.widget import Widget
from spotify_api.spotify_client import SpotifyClient

sp = SpotifyClient.get_instance()

logging.getLogger("spotipy").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class PlaybackMonitor(Widget):
    """Single source of truth for playback state.

    Polls Spotify once per second, diffs against the last seen state, and posts
    messages when something changes. It is the ONLY thing that calls the
    playback API on a timer; every other widget reacts to these messages instead
    of polling on its own. The widget renders nothing.
    """

    DEFAULT_CSS = "PlaybackMonitor { display: none; }"

    class PlaybackChanged(Message):
        """Posted every poll while a track is playing, with fresh ground truth."""

        def __init__(
            self,
            track_name: str,
            track_artist: str,
            progress_ms: int,
            duration_ms: int,
            track_uri: str,
            art_url: str,
            device_name: str = None,
            trust_progress: bool = True,
        ) -> None:
            super().__init__()
            self.track_name = track_name
            self.track_artist = track_artist
            self.progress_ms = progress_ms
            self.duration_ms = duration_ms
            self.track_uri = track_uri
            self.art_url = art_url
            self.device_name = device_name
            self.trust_progress = trust_progress

    class TrackEnded(Message):
        """Posted when the playing track changes (the previous one ended)."""

        def __init__(self, ended_uri: str) -> None:
            super().__init__()
            self.ended_uri = ended_uri

    class PlaybackStopped(Message):
        """Posted when nothing is playing anymore."""

    def on_mount(self) -> None:
        self._last_uri = None
        self._last_playing = False
        self._last_progress_ms = 0
        self._last_duration_ms = 0
        self._seek_guard_until = 0.0
        self.set_interval(1, self.poll)

    @property
    def is_playing(self) -> bool:
        """Last-known playing state from the most recent poll. Lets other
        widgets check play/pause status without making their own blocking
        API call."""
        return self._last_playing

    def _ended_naturally(self) -> bool:
        """True if the last-seen track was near its end (within 3s), meaning it
        finished on its own rather than being skipped mid-track by the user."""
        if self._last_duration_ms <= 0:
            return False
        return self._last_progress_ms >= self._last_duration_ms - 3000

    def poll(self) -> None:
        try:
            track = sp.current_playback()
        except Exception:
            # transient network/API error: keep last known state, try next tick
            return

        playing = bool(
            track
            and track.get("is_playing")
            and track.get("item")
            and track.get("progress_ms", 0) > 0
        )

        if not playing:
            # transition from playing -> stopped
            if self._last_playing:
                self._last_playing = False
                # Only auto-advance if the track actually ran to its end.
                if self._last_uri and self._ended_naturally():
                    self.post_message(self.TrackEnded(self._last_uri))
                self._last_uri = None
                self._last_progress_ms = 0
                self._last_duration_ms = 0
                self.post_message(self.PlaybackStopped())
            return

        item = track["item"]
        curr_uri = item["uri"]

        # Track changed. Only treat it as a natural end (auto-advance) if the
        # previous track was near completion; otherwise it was a manual skip
        # (n/p keybinding or track selection) and we must NOT advance again.
        if curr_uri != self._last_uri:
            if self._last_uri and self._ended_naturally():
                self.post_message(self.TrackEnded(self._last_uri))
            self._last_uri = curr_uri
        images = item["album"]["images"]
        art_url = images[0]["url"] if images else None
        device = track.get("device") or {}
        device_name = device.get("name")
        in_seek_guard = time.monotonic() < self._seek_guard_until
        self._last_playing = True
        self._last_progress_ms = track["progress_ms"]
        self._last_duration_ms = item["duration_ms"]
        self.post_message(
            self.PlaybackChanged(
                track_name=item["name"],
                track_artist=item["artists"][0]["name"],
                progress_ms=track["progress_ms"],
                duration_ms=item["duration_ms"],
                track_uri=curr_uri,
                art_url=art_url,
                device_name=device_name,
                trust_progress=not in_seek_guard,
            )
        )

    def notify_seek(self) -> None:
        """Called when the user seeks; suppresses position snap-back until the
        seek has had time to land on the device."""
        self._seek_guard_until = time.monotonic() + 2.0
