import spotipy
from spotipy.oauth2 import SpotifyOAuth
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Container
from textual.widget import Widget
from textual.widgets import Button, Header, Footer, Static, Label, Tabs, ListView, ListItem, DataTable
from textual.message import Message
from textual import events, on
from dotenv import load_dotenv
import os
import re

class PlaylistLabel(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def compose( self ) -> ComposeResult:
        yield Label(self.label)

class PlaylistTabs(Static):
    BINDINGS = [
        ("ctrl+d", "scroll_down()", "Scroll Down"),
        ("ctrl+u", "scroll_up()", "Scroll Up")
    ]
    def __init__(self):
        super().__init__()
        self.tracks_cache = {}
        self.curr_displayed_tracks = {}
        self.prev_displayed_tracks = {}
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
            if playlist_name in self.tracks_cache:
                self.track_table.add_rows(self.tracks_cache[playlist_name])
            else:
                self.fetch_playlist_tracks(playlist_name)
                self.track_table.add_rows(self.tracks_cache[playlist_name])

    def fetch_playlist_tracks(self, playlist_name: str) -> None: 
        results = sp.playlist(playlist_ids[playlist_name], fields= "tracks, next,items")
        tracks = results['tracks']
        track_list = load_tracks(tracks, self.track_table)
        self.tracks_cache[playlist_name] = track_list
        self.curr_displayed_tracks[playlist_name] = tracks
        self.curr_displayed_playlist = playlist_name

    def fetch_next_playlist_tracks(self, playlist_name: str, tracks) -> None:
        track_list = load_tracks(tracks, self.track_table)
        self.tracks_cache[playlist_name] = track_list
        self.curr_displayed_tracks[playlist_name] = tracks
        self.curr_displayed_playlist = playlist_name

    @on(ListView.Selected, "#playlist-tabs")
    def playlist_selected(self, event: ListView.Selected) -> None:
        self.curr_displayed_playlist = str(event.item.label)
        self.load_playlist_content(str(event.item.label))

    def action_scroll_down(self) -> None:
        if self.curr_displayed_playlist is not None and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None:
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            next_tracks = sp.next(curr_tracks)
            if next_tracks is not None:
                if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                    self.prev_displayed_tracks[self.curr_displayed_playlist] = []
                self.prev_displayed_tracks[self.curr_displayed_playlist].append(curr_tracks)
                self.fetch_next_playlist_tracks(self.curr_displayed_playlist, next_tracks)
                self.track_table.clear()
                self.track_table.add_rows(self.tracks_cache[self.curr_displayed_playlist])
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
                    self.fetch_next_playlist_tracks(self.curr_displayed_playlist,prev_tracks)
                    self.track_table.clear()
                    self.track_table.add_rows(self.tracks_cache[self.curr_displayed_playlist])
        else:
            print("No previous tracks")

class Spotuify(App):
    CSS_PATH = "playlist.tcss"

    def compose(self) -> ComposeResult:
        yield PlaylistTabs()

def setup_spotify_auth() -> None:
    client_id = os.environ.get("SPOTIPY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")
    scope = 'playlist-read-private'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope))
    return sp

def truncate_track(text, max_width):
    if len(text) > max_width:
        return text[:max_width]
    return text

def format_artist_track(artist_name, track_name, album_name, max_width):
    return truncate_track(artist_name, max_width), truncate_track(track_name, max_width), truncate_track(album_name, max_width)

def load_tracks(tracks, track_table) -> list:
    list_items = []
    for item in tracks['items']:
        track = item['track']
        artist_name = track['artists'][0]['name']
        track_name = track['name']
        album_name = track['album']['name']
        duration = str(int((track['duration_ms'] / 1000) / 60)) + ':' + str(int((track['duration_ms'] / 1000) % 60)).zfill(2)
        artist_name_formatted, track_name_formatted, album_name_formatted = format_artist_track(artist_name, track_name, album_name, 50)
        list_items.append((track_name_formatted, artist_name_formatted, album_name_formatted, duration))
    return list_items
    
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
    max_widths = {'artist': 0, 'track': 0}
    load_user_playlists(playlist_names, playlist_ids, user_id)

    app = Spotuify()
    app.run()