import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from textual.app import App, ComposeResult
from spotify_player.player import Player
from spotify_player.player_controls import PlayerControls
from spotify_api.spotify_utils import load_user_playlists

class Spotuify(App):
    CSS_PATH = "css/playlist.tcss"

    def compose(self) -> ComposeResult:
        yield Player()
        yield PlayerControls()

if __name__ == '__main__':
    app = Spotuify()
    app.run()