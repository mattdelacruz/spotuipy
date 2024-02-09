import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from textual.app import App, ComposeResult
from player import Player
from player_controls import PlayerControls
from spotify_utils import load_user_playlists

class Spotuify(App):
    CSS_PATH = "playlist.tcss"

    def compose(self) -> ComposeResult:
        yield Player()
        yield PlayerControls()

if __name__ == '__main__':
    app = Spotuify()
    app.run()