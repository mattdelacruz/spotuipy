import spotipy
from spotipy.oauth2 import SpotifyOAuth
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Container
from textual.widget import Widget
from textual.widgets import Button, Header, Footer, Static, Label, ListView, ListItem, Tabs
from textual.message import Message
from textual import events
from dotenv import load_dotenv
import os
import traceback
import re

class TrackLabel(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def compose( self ) -> ComposeResult:
        yield Label(self.label)

class PlaylistTabs(Static):
    # CSS = """
    #     Tab {
    #     dock: left;
    # }
    # """
    listView = None
    def __init__(self):
        super().__init__()
        self.tracks_cache = {}
        self.listView = None
        self.first_load = True

    def compose(self) -> ComposeResult:
        yield Tabs()
        yield ListView()

    def on_mount(self) -> None:
        tabs = self.query_one(Tabs)
        self.listView = self.query_one(ListView)
        for playlist_name in playlist_names:
            tabs.add_tab(playlist_name)

    def load_tab_content(self, playlist_name):
        if playlist_name:
            self.listView.visible = True
            if playlist_name in self.tracks_cache:
                print('found in cache', playlist_name)
                if not self.first_load:
                    self.listView.clear()
                self.listView.extend(self.tracks_cache[playlist_name])
                self.first_load = False
            else:
                print('fetching', playlist_name)
                if not self.first_load:
                    self.listView.clear()
                self.fetch_playlist(playlist_name)
                self.listView.extend(self.tracks_cache[playlist_name])

    def fetch_playlist(self, playlist_name): 
        results = sp.playlist(playlist_ids[playlist_name], fields="tracks,next,items")
        tracks = results['tracks']
        track_data = []
        max_widths = {'artist': 0, 'track': 0} 
        list_items = load_tracks(tracks, track_data, self.listView)
        # make a ctrl+d command to fetch the next tracks so I don't load really long playlists
        # tracks should be a linked list
        # change the tracks_cache to the currently displaying track list

        # while tracks['next']:
        #     tracks = sp.next(tracks)
        #     list_items.extend(load_tracks(tracks, track_data, listView))
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

def format_artist_track(artist_name, track_name, max_width):
    return truncate_track(artist_name, max_width), truncate_track(track_name, max_width)

def update_max_widths(artist_name, track_name, max_widths) -> None:
    max_widths['artist'] = max(max_widths['artist'], len(artist_name))
    max_widths['track'] = max(max_widths['track'], len(track_name))

def load_tracks(tracks, track_data, listView) -> list:
    list_items = []
    for item in tracks['items']:
        track = item['track']
        artist_name = track['artists'][0]['name']
        track_name = track['name']
        artist_name_formatted, track_name_formatted = format_artist_track(artist_name, track_name, 30)
        track_data.append((artist_name_formatted, track_name_formatted))
        row_format = "{:<30} {:<30}"
        formatted_string = row_format.format(artist_name_formatted, track_name_formatted)
        list_items.append(TrackLabel(formatted_string))
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