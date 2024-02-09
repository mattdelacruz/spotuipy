from textual.widgets import ListItem, Label, Static
from textual.app import ComposeResult
import spotipy 
from spotify_client import SpotifyClient

sp = SpotifyClient.get_instance()

class PlaylistLabel(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label)


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
            if self.query_one("#track-title", CurrentSongLabel).label == track_name:
                return
            self.query_one("#track-title", CurrentSongLabel).update(track_name)
            self.query_one("#track-artist", CurrentSongLabel).update(track_artist)
        else:
            self.query_one("#track-title", CurrentSongLabel).update("No track currently playing")
            self.query_one("#track-artist", CurrentSongLabel).update("")