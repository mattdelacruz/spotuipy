import spotipy 
import time
import threading 
from textual.widgets import ListItem, Label, Static, ProgressBar
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.timer import Timer
from spotify_api.spotify_client import SpotifyClient
from tools.formatting import format_duration

sp = SpotifyClient.get_instance()

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
        self.track_switch = False
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ProgressBar(id="track_progress")
            yield TrackProgressTimeLabel(label=format_duration(0),id="track_progress_time_label")
            yield Label("/", id="time_separator")
            yield TrackProgressTimeLabel(label=format_duration(0),id="track_progress_total_time_label")

    def on_mount(self) -> None:
        self.progress_timer = self.set_interval(1/10, self.make_progress, pause=True)
    
    def make_progress(self) -> None:
        if self.progress_ms >= self.total_time_ms:
            print('track is finished!')
            self.pause_progress_bar()
            self.is_finished = True
            self.is_active = False
            return

        self.progress_ms += 100
        self.query_one("#track_progress", ProgressBar).advance(100)
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(new_time_label=format_duration(self.progress_ms), duration_ms=self.progress_ms)

    def start_progress_bar(self, progress_ms: int, total_time_ms: int) -> None:
        self.query_one("#track_progress", ProgressBar).update(progress=progress_ms, total=total_time_ms)
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(new_time_label=format_duration(progress_ms), duration_ms=progress_ms)
        self.query_one("#track_progress_total_time_label", TrackProgressTimeLabel).update(new_time_label=format_duration(total_time_ms), duration_ms=total_time_ms)
        self.reset_progress_bar()
        self.resume_progress_bar()
        self.total_time_ms = total_time_ms 
        self.progress_ms = progress_ms
        self.is_finished = False
        self.is_active = True

    def update_progress_bar(self, progress_ms: int, total_time_ms: int) -> None:
        self.query_one("#track_progress", ProgressBar).update(progress=progress_ms, total=total_time_ms)
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(new_time_label=format_duration(progress_ms), duration_ms=progress_ms)
        self.query_one("#track_progress_total_time_label", TrackProgressTimeLabel).update(new_time_label=format_duration(total_time_ms), duration_ms=total_time_ms)

    def pause_progress_bar(self) -> None:
        self.progress_timer.pause()
    
    def resume_progress_bar(self) -> None:
        self.progress_timer.resume()

    def reset_progress_bar(self) -> None:
        self.progress_timer.reset()
        self.query_one("#track_progress_time_label", TrackProgressTimeLabel).update(new_time_label=format_duration(0), duration_ms=0)
    
    def get_is_finished(self) -> bool:
        self.track_switch = True
        return self.is_finished

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
    def __init__(self, label:str, id:str) -> None:
        super().__init__(label, id=id)
        self.label = label

    def update(self, new_label: str) -> None:
        super().update(new_label)
        self.label = new_label

class CurrentTrack(Static):
    def __init__(self):
        super().__init__()
        self.track_name = None
        self.track_artist = None

    def compose(self) -> ComposeResult:
        yield CurrentTrackLabel(label="", id="track-title")
        yield CurrentTrackLabel(label="", id="track-artist")

    def on_mount(self) -> None:
        self.set_interval(3, self.update_current_track)

    def update_current_track(self) -> None:
        track = sp.current_user_playing_track()
        if track and track.get('item') and track['progress_ms'] > 0:
            track_name = track['item']['name']
            track_artist = track['item']['artists'][0]['name']
            duration_ms = track['item']['duration_ms']
            progress_ms = track['progress_ms']
            is_playing = track['is_playing']

            # Update track details and progress bar only if the track is playing and data is consistent
            if is_playing:
                if self.should_update_track(track_name, track_artist):
                    self.update_track_labels(track_name, track_artist)
                
                self.start_or_update_progress_bar(progress_ms, duration_ms)
        else:
            self.display_no_current_track()

    def should_update_track(self, track_name, track_artist) -> bool:
        # Compare current labels with new values to determine if update is needed
        return (self.query_one("#track-title", CurrentTrackLabel).label != track_name or 
                self.query_one("#track-artist", CurrentTrackLabel).label != track_artist)

    def update_track_labels(self, track_name, track_artist):
        self.query_one("#track-title", CurrentTrackLabel).update(track_name)
        self.query_one("#track-artist", CurrentTrackLabel).update(track_artist)

    def start_or_update_progress_bar(self, progress_ms, duration_ms):
        track_progress: TrackProgress = self.app.query_one(TrackProgress)
        if track_progress.is_active:
            track_progress.update_progress_bar(progress_ms, duration_ms)
        else:
            track_progress.start_progress_bar(progress_ms, duration_ms)

    def display_no_current_track(self):
        self.query_one("#track-title", CurrentTrackLabel).update("No track currently playing")
        self.query_one("#track-artist", CurrentTrackLabel).update("")