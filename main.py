import spotipy
from spotipy.oauth2 import SpotifyOAuth
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Container
from textual.widget import Widget
from textual.widgets import Button, Header, Footer, Static, Label, Tabs, DataTable
from textual.message import Message
from textual import events
from dotenv import load_dotenv
import os
import traceback
import re

class PlaylistTabs(Static):
    CSS = """
        Tab {
        dock: left;
    }
    """
    def __init__(self):
        super().__init__()
        self.tracks_cache = {}
        self.trackTable = None
        self.tabs = None

    def compose(self) -> ComposeResult:
        yield Tabs()
        yield DataTable()

    def on_mount(self) -> None:
        self.tabs = self.query_one(Tabs)
        self.trackTable = self.query_one(DataTable)
        self.trackTable.add_columns("Track", "Artist", "Album", "Length")
        self.trackTable.cursor_type = "row"
        for playlist_name in playlist_names:
            self.tabs.add_tab(playlist_name)

    def load_tab_content(self, playlist_name):
        if playlist_name:
            self.trackTable.visible = True
            self.trackTable.clear()
            if playlist_name in self.tracks_cache:
                print('found in cache', playlist_name)
                self.trackTable.add_rows(self.tracks_cache[playlist_name])
            else:
                print('fetching', playlist_name)
                self.fetch_playlist(playlist_name)
                self.trackTable.add_rows(self.tracks_cache[playlist_name])

    def fetch_playlist(self, playlist_name): 
        results = sp.playlist(playlist_ids[playlist_name], fields= "tracks, next,items")
        tracks = results['tracks']
        track_data = []
        list_items = load_tracks(tracks, track_data, self.trackTable)
        # make a ctrl+d command to fetch the next tracks so I don't load really long playlists
        # tracks should be a linked list
        # change the tracks_cache to the currently displaying track list

        # while tracks['next']:
        #     tracks = sp.next(tracks)
        #     list_items.extend(load_tracks(tracks, track_data, trackTable))
        self.tracks_cache[playlist_name] = list_items

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        print('tab is activated')
        traceback.print_stack()
        self.load_tab_content(str(event.tab.label))

class Spotuify(App):
    def compose(self) -> ComposeResult:
        yield PlaylistTabs()
        yield Footer()

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

def load_tracks(tracks, track_data, trackTable) -> list:
    list_items = []
    for item in tracks['items']:
        track = item['track']
        artist_name = track['artists'][0]['name']
        track_name = track['name']
        album_name = track['album']['name']
        duration = str(int((track['duration_ms'] / 1000) / 60)) + ':' + str(int((track['duration_ms'] / 1000) % 60)).zfill(2)
        artist_name_formatted, track_name_formatted, album_name_formatted = format_artist_track(artist_name, track_name, album_name, 30)
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