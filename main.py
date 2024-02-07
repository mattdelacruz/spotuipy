import spotipy
from spotipy.oauth2 import SpotifyOAuth
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Container
from textual.widget import Widget
from textual.widgets import Button, Header, Footer, Static, Label, ListView, ListItem, DataTable, ProgressBar
from textual.timer import Timer
from textual.message import Message
from textual import events, on
from dotenv import load_dotenv
import os
import re
from pprint import pprint

class PlaylistLabel(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label)

class Player(Static):
    BINDINGS = [
        ("ctrl+d", "scroll_down", "Scroll Down"),
        ("ctrl+u", "scroll_up", "Scroll Up"),
    ]

    def __init__(self):
        super().__init__()
        self.curr_displayed_tracks = {}
        self.prev_displayed_tracks = {}
        self.track_uris = {}
        self.curr_displayed_playlist = None
        self.track_table = None
        self.tabs = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ListView(id="playlist-tabs")
            yield DataTable(id="playlist-table")

    def on_mount(self) -> None:
        self.playlist_list = self.query_one(ListView)
        self.track_table = self.query_one(DataTable)
        self.track_table.add_columns("Track", "Artist", "Album", "Length")
        self.track_table.cursor_type = "row"
        added_playlist_names = set()
        for playlist_name in playlist_names:
            if playlist_name not in added_playlist_names:
                self.playlist_list.append(PlaylistLabel(playlist_name))
                added_playlist_names.add(playlist_name)
            else:
                print(f"Duplicate playlist name '{playlist_name}' skipped.")

    def load_playlist_content(self, playlist_name):
        if playlist_name:
            self.track_table.visible = True
            self.track_table.clear()
            track_list = self.fetch_playlist_tracks(playlist_name)
            for track_list_item in track_list:
                unique_key = str(track_list_item[0])
                self.track_table.add_row(*track_list_item, key=unique_key)

    def fetch_playlist_tracks(self, playlist_name: str):
        self.curr_displayed_playlist = playlist_name 
        results = sp.playlist(playlist_ids[playlist_name], fields= "tracks, next,items")
        tracks = results['tracks']
        track_list, self.track_uris = load_tracks(tracks, self.track_table, self.curr_displayed_playlist)
        self.curr_displayed_tracks[playlist_name] = tracks
        return track_list

    def fetch_next_playlist_tracks(self, playlist_name: str, tracks):
        self.curr_displayed_playlist = playlist_name
        track_list, self.track_uris = load_tracks(tracks, self.track_table, self.curr_displayed_playlist)
        self.curr_displayed_tracks[playlist_name] = tracks
        return track_list

    @on(ListView.Selected, "#playlist-tabs")
    def playlist_selected(self, event: ListView.Selected) -> None:
        self.curr_displayed_playlist = str(event.item.label)
        self.load_playlist_content(str(event.item.label))
    
    @on(DataTable.RowSelected, "#playlist-table")
    def data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        sp.start_playback(uris=[self.track_uris[self.curr_displayed_playlist][event.row_key.value]])

    def action_scroll_down(self) -> None:
        if self.curr_displayed_playlist is not None and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None:
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            next_tracks = sp.next(curr_tracks)
            if next_tracks is not None:
                if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                    self.prev_displayed_tracks[self.curr_displayed_playlist] = []
                self.prev_displayed_tracks[self.curr_displayed_playlist].append(curr_tracks)
                track_list = self.fetch_next_playlist_tracks(self.curr_displayed_playlist, next_tracks)
                self.track_table.clear()
                for track_list_item in track_list:
                    unique_key = track_list_item[0]
                    self.track_table.add_row(*track_list_item, key=unique_key)
            else:
                print("No next tracks")

    def action_scroll_up(self) -> None:
        if self.curr_displayed_playlist is not None and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None:
            if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                return
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            if len(self.prev_displayed_tracks[self.curr_displayed_playlist]) > 0:
                prev_tracks = self.prev_displayed_tracks[self.curr_displayed_playlist].pop()
                if prev_tracks:
                    track_list = self.fetch_next_playlist_tracks(self.curr_displayed_playlist,prev_tracks)
                    self.track_table.clear()
                    for track_list_item in track_list:
                        unique_key = track_list_item[0]
                        self.track_table.add_row(*track_list_item, key=unique_key)
        else:
            print("No previous tracks")

# select currently highlighted item with spacebar
# get track object
# from track object, get uri
# pass uri to sp.start_playback(uris=['spotify:track:6gdLoMygLsgktydTQ71b15'])
class CurrentSongLabel(Label):
    def __init__(self, label:str, id:str):
        super().__init__(label, id=id)
        self.label = label

    def update(self, new_label: str):
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

class Spotuify(App):
    CSS_PATH = "playlist.tcss"

    def compose(self) -> ComposeResult:
        yield Player()
        yield PlayerControls()
    
    def key_space(self) -> None:
        sp.pause_playback()

def setup_spotify_auth() -> None:
    client_id = os.environ.get("SPOTIPY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")
    scope = 'playlist-read-private, user-read-playback-state,user-modify-playback-state user-read-currently-playing'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope))
    return sp

def truncate_track(text, max_width):
    if len(text) > max_width:
        return text[:max_width]
    return text

def format_artist_track(artist_name, track_name, album_name, max_width):
    return truncate_track(artist_name, max_width), truncate_track(track_name, max_width), truncate_track(album_name, max_width)

def load_tracks(tracks, track_table, playlist) -> list:
    list_items = []
    track_uris = {}
    track_uris[playlist] = {}
    for item in tracks['items']:
        track = item['track']
        artist_name = track['artists'][0]['name']
        track_name = track['name']
        album_name = track['album']['name']
        duration = str(int((track['duration_ms'] / 1000) / 60)) + ':' + str(int((track['duration_ms'] / 1000) % 60)).zfill(2)
        artist_name_formatted, track_name_formatted, album_name_formatted = format_artist_track(artist_name, track_name, album_name, 20)
        list_items.append((track_name_formatted, artist_name_formatted, album_name_formatted, duration))
        track_uris[playlist][track_name_formatted] = track['uri']

    return list_items, track_uris
    
def load_user_playlists(playlist_names, playlist_ids, user_id) -> None:
    for playlist in playlists['items']:
        if playlist['owner']['id'] == user_id:
            playlist_names.append(playlist['name'])
            playlist_ids[playlist['name']] = playlist['id']

if __name__ == '__main__':
    load_dotenv()
    sp = setup_spotify_auth() 
    playlists = sp.current_user_playlists()
    user_id = sp.me()['id']
    playlist_names = []
    playlist_ids = {}
    load_user_playlists(playlist_names, playlist_ids, user_id)

    app = Spotuify()
    app.run()