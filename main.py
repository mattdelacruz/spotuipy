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

    def compose(self) -> ComposeResult:
        yield Tabs()
        yield ListView()

    def on_mount(self) -> None:
        tabs = self.query_one(Tabs)
        for name in playlist_names:
            tabs.add_tab(name)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        listView = self.query_one(ListView)
        listView.clear()

        if event.tab is None:
            listView.visible = False
        else:
            listView.visible = True
            playlist_name = str(event.tab.label)

            if playlist_name in self.tracks_cache:
                track_data = self.tracks_cache[playlist_name]            max_widths = {'artist': 0, 'track': 0}  # Initialize max_widths
                for artist_name, track_name in track_data:
                    max_widths = update_max_widths(artist_name, track_name, max_widths)
                    row_format = "{:<{artist_width}} {:{track_width}}"  # Adjust the numbers as needed
                    formatted_string = row_format.format(artist_name, track_name, artist_width=artist_width, track_width=track_width)
                    listView.append(ListItem(Label(formatted_string)))
            else:
                results = sp.playlist(playlist_ids[playlist_name], fields="tracks,next,items")
                tracks = results['tracks']
                track_data = []
                list_items = []
                load_tracks(tracks, track_data, list_items)
                while tracks['next']:
                    tracks = sp.next(tracks)
                    load_tracks(tracks, track_data, list_items)
                listView.clear()
                listView.extend(list_items)
                self.tracks_cache[playlist_name] = track_data
     
class Spotuify(App):
    def compose(self) -> ComposeResult:
        yield PlaylistTabs()
        yield Footer()

    def load_new_data(self):
        new_data = "New data loaded!"
        self.list_view.update(new_data)

def setup_spotify_auth() -> None:
    client_id = os.environ.get("SPOTIPY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")
    scope = 'playlist-read-private'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope))
    return sp

# def load_tracks(tracks, track_data, list_items) -> None:
#     for item in tracks['items']:
#         track = item['track']
#         track_data.append((track['artists'][0]['name'], track['name']))
#         list_items.append(ListItem(Label("%32.32s %s" % (track['artists'][0]['name'], track['name']))))   
def update_max_widths(artist_name, track_name, max_widths):
    # Update the maximum widths based on the length of the new artist_name and track_name
    max_widths['artist'] = max(max_widths['artist'], len(artist_name))
    max_widths['track'] = max(max_widths['track'], len(track_name))
    return max_widths

def load_tracks(tracks, track_data, list_items) -> None:    
    # Create the format string with dynamic widths
    
    for item in tracks['items']:
        track = item['track']
        artist_name = track['artists'][0]['name']
        track_name = track['name']

        max_widths = update_max_widths(artist_name, track_name, max_widths)
        
        # Append the data tuple to track_data
        track_data.append((artist_name, track_name))
        row_format = "{:<{artist_width}} {:{track_width}}"  # Adjust the numbers as needed

        # Use the format string to format and append the ListItem
        formatted_string = row_format.format(artist_name, track_name, artist_width=artist_width, track_width=track_width)
        list_items.append(ListItem(Label(formatted_string)))   


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