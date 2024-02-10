import spotipy 
from textual.widgets import ListItem, Label, Static, ProgressBar
from textual.app import ComposeResult
from textual.timer import Timer
from spotify_client import SpotifyClient
from formatting import format_duration

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
    
    def compose(self) -> ComposeResult:
        yield ProgressBar(id="track_progress")

    def on_mount(self) -> None:
        self.progress_timer = self.set_interval(1/10, self.make_progress, pause=True)
    
    def make_progress(self) -> None:
        self.query_one("#track_progress", ProgressBar).advance(100)
    
    def start_progress_bar(self, progress_ms:int, total_time_ms:int) -> None:
        self.query_one("#track_progress", ProgressBar).update(progress=progress_ms, total=total_time_ms)
        self.progress_timer.reset()
        self.progress_timer.resume()

    def pause_progress_bar(self) -> None:
        self.progress_timer.pause()
    
    def resume_progress_bar(self) -> None:
        self.progress_timer.resume()

    def reset_progress_bar(self) -> None:
        self.progress_timer.reset()

class CurrentSongLabel(Label):
    def __init__(self, label:str, id:str) -> None:
        super().__init__(label, id=id)
        self.label = label

    def update(self, new_label: str) -> None:
        super().update(new_label)
        self.label = new_label

class CurrentSong(Static):
    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield CurrentSongLabel(label="", id="track-title")
        yield CurrentSongLabel(label="", id="track-artist")

    def on_mount(self) -> None:
        self.set_interval(3, self.update_current_song)

    def update_current_song(self) -> None:
        track = sp.current_user_playing_track()
        if track and track.get('item'):
            track_name = track['item']['name']
            track_artist = track['item']['artists'][0]['name']
            duration_ms = track['item']['duration_ms']
            progress_ms = track['progress_ms']
            is_playing = track['is_playing']
            track_progress: TrackProgress = self.app.query_one(TrackProgress)

            if self.query_one("#track-title", CurrentSongLabel).label != track_name:
                self.query_one("#track-title", CurrentSongLabel).update(track_name)
                self.query_one("#track-artist", CurrentSongLabel).update(track_artist)
                if(is_playing):
                    track_progress.start_progress_bar(progress_ms, duration_ms)
        else:
            self.query_one("#track-title", CurrentSongLabel).update("No track currently playing")
            self.query_one("#track-artist", CurrentSongLabel).update("")