from textual import work
import time
from textual_image.widget import Image as AlbumImage
from PIL import Image as PILImage
from io import BytesIO
import requests
import logging
from textual.widgets import ListItem, Label, Static, ProgressBar
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.timer import Timer
from textual.message import Message
from textual.widget import Widget
from spotify_api.spotify_client import SpotifyClient
from tools.formatting import format_duration
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

        def __init__(self, track_name: str, track_artist: str,
                     progress_ms: int, duration_ms: int, track_uri: str, art_url: str,
                     device_name: str = None, trust_progress: bool = True) -> None:
            super().__init__()
            self.track_name = track_name
            self.track_artist = track_artist
            self.progress_ms = progress_ms
            self.duration_ms = duration_ms
            self.track_uri = track_uri
            self.art_url = art_url
            self.device_name = device_name
            self.trust_progress = True

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

        playing = bool(track and track.get('is_playing')
                       and track.get('item') and track.get('progress_ms', 0) > 0)

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

        item = track['item']
        curr_uri = item['uri']

        # Track changed. Only treat it as a natural end (auto-advance) if the
        # previous track was near completion; otherwise it was a manual skip
        # (n/p keybinding or track selection) and we must NOT advance again.
        if curr_uri != self._last_uri:
            if self._last_uri and self._ended_naturally():
                self.post_message(self.TrackEnded(self._last_uri))
            self._last_uri = curr_uri
        images = item['album']['images']
        art_url = images[0]['url'] if images else None
        device = track.get('device') or {}
        device_name = device.get('name')
        in_seek_guard = time.monotonic() < self._seek_guard_until
        self._last_playing = True
        self._last_progress_ms = track['progress_ms']
        self._last_duration_ms = item['duration_ms']
        self.post_message(self.PlaybackChanged(
            track_name=item['name'],
            track_artist=item['artists'][0]['name'],
            progress_ms=track['progress_ms'],
            duration_ms=item['duration_ms'],
            track_uri=curr_uri,
            art_url=art_url,
            device_name=device_name,
            trust_progress=not in_seek_guard,
        ))

    def notify_seek(self) -> None:
        """Called when the user seeks; suppresses position snap-back until the
        seek has had time to land on the device."""
        self._seek_guard_until = time.monotonic() + 2.0


class PlaylistLabel(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label)


class TrackProgress(Static):
    progress_timer: Timer

    def __init__(self):
        super().__init__()
        self.total_time_ms = 0
        self.progress_ms = 0
        self.is_finished = False
        self.is_active = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ProgressBar(id="track_progress")
            yield TrackProgressTimeLabel(label=format_duration(0), id="track_progress_time_label")
            yield Label("/", id="time_separator")
            yield TrackProgressTimeLabel(label=format_duration(0), id="track_progress_total_time_label")

    def on_mount(self) -> None:
        self.progress_timer = self.set_interval(
            1/10, self.make_progress, pause=True)

    def on_playback_monitor_playback_changed(self, message) -> None:
        if self.is_active:
            if message.trust_progress:
                self.update_progress_bar(
                    message.progress_ms, message.duration_ms)
                self.progress_ms = message.progress_ms
                self.total_time_ms = message.duration_ms
            # during seek guard: leave local progress_ms alone, keep ticking
        else:
            self.start_progress_bar(message.progress_ms, message.duration_ms)

    def on_playback_monitor_playback_stopped(self, message) -> None:
        self.reset_to_zero()

    def make_progress(self) -> None:
        if self.progress_ms >= self.total_time_ms:
            self.pause_progress_bar()
            self.is_finished = True
            self.is_active = False
            return

        self.progress_ms += 100
        self.query_one("#track_progress", ProgressBar).advance(100)
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(
            new_time_label=format_duration(self.progress_ms), duration_ms=self.progress_ms)

    def start_progress_bar(self, progress_ms: int, total_time_ms: int) -> None:
        self.query_one("#track_progress", ProgressBar).update(
            progress=progress_ms, total=total_time_ms)
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(
            new_time_label=format_duration(progress_ms), duration_ms=progress_ms)
        self.query_one("#track_progress_total_time_label", TrackProgressTimeLabel).update(
            new_time_label=format_duration(total_time_ms), duration_ms=total_time_ms)
        self.reset_progress_bar()
        self.resume_progress_bar()
        self.total_time_ms = total_time_ms
        self.progress_ms = progress_ms
        self.is_finished = False
        self.is_active = True

    def update_progress_bar(self, progress_ms: int, total_time_ms: int) -> None:
        self.query_one("#track_progress", ProgressBar).update(
            progress=progress_ms, total=total_time_ms)
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(
            new_time_label=format_duration(progress_ms), duration_ms=progress_ms)
        self.query_one("#track_progress_total_time_label", TrackProgressTimeLabel).update(
            new_time_label=format_duration(total_time_ms), duration_ms=total_time_ms)

    def pause_progress_bar(self) -> None:
        self.progress_timer.pause()

    def resume_progress_bar(self) -> None:
        self.progress_timer.resume()

    def reset_progress_bar(self) -> None:
        self.progress_timer.reset()
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(
            new_time_label=format_duration(0), duration_ms=0)

    def reset_to_zero(self) -> None:
        self.pause_progress_bar()
        self.is_active = False
        self.progress_ms = 0
        self.total_time_ms = 0
        self.query_one("#track_progress", ProgressBar).update(progress=0)
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(
            new_time_label=format_duration(0), duration_ms=0)


class TrackProgressTimeLabel(Label):
    def __init__(self, label: str, id: str) -> None:
        super().__init__(label, id=id)
        self.time_label = label
        self.duration_ms = 0

    def update(self, new_time_label: str, duration_ms: int) -> None:
        super().update(new_time_label)
        self.time_label = new_time_label
        self.duration_ms = duration_ms

    def get_curr_duration_ms(self) -> int:
        return self.duration_ms


class CurrentTrackLabel(Label):
    def __init__(self, label: str, id: str) -> None:
        super().__init__(label, id=id)


class CurrentTrack(Static):
    def __init__(self):
        super().__init__()
        self.track_name = None
        self.track_artist = None

    def compose(self) -> ComposeResult:
        yield CurrentTrackLabel(label="", id="track-title")
        yield CurrentTrackLabel(label="", id="track-artist")

    def on_playback_monitor_playback_changed(self, message) -> None:
        if self.should_update_track(message.track_name, message.track_artist):
            self.update_track_labels(message.track_name, message.track_artist)
        device_label = self.app.query_one("#track-device", CurrentTrackLabel)
        device_label.update(
            f"Playing from {message.device_name}" if message.device_name else "")
        device_label.refresh(layout=True)

    def on_playback_monitor_playback_stopped(self, message) -> None:
        self.display_no_current_track()

    def should_update_track(self, track_name, track_artist) -> bool:
        return self.track_name != track_name or self.track_artist != track_artist

    def update_track_labels(self, track_name, track_artist):
        title = self.app.query_one("#track-title", CurrentTrackLabel)
        artist = self.app.query_one("#track-artist", CurrentTrackLabel)
        title.update(track_name)
        artist.update(track_artist)
        title.refresh(layout=True)
        artist.refresh(layout=True)
        self.track_name = track_name
        self.track_artist = track_artist

    def display_no_current_track(self):
        self.query_one(
            "#track-title", CurrentTrackLabel).update("No track currently playing")
        self.query_one("#track-artist", CurrentTrackLabel).update("")
        self.app.query_one("#track-device", CurrentTrackLabel).update("")
        self.track_name = None
        self.track_artist = None


class AlbumCover(Static):
    def __init__(self):
        super().__init__()
        self._last_art = None

    def compose(self) -> ComposeResult:
        yield AlbumImage(id="cover")

    def on_playback_monitor_playback_changed(self, message) -> None:
        if not message.art_url:
            return
        self._last_art = message.art_url
        self.load_cover(message.art_url)

    @work(thread=True, exclusive=True)
    def load_cover(self, url: str) -> None:
        try:
            resp = requests.get(url, timeout=5)
            pil = PILImage.open(BytesIO(resp.content))
        except Exception:
            return
        # Setting the widget property must happen on the UI thread:
        self.app.call_from_thread(self._set_image, pil)

    def _set_image(self, pil) -> None:
        self.query_one("#cover", AlbumImage).image = pil

    def on_playback_monitor_playback_stopped(self, message) -> None:
        self._last_art = None
        self.query_one("#cover", AlbumImage).image = None
