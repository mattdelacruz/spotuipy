from textual.app import App, ComposeResult
from spotify_player.player import Player
from spotify_player.player_controls import PlayerControls
import logging
logging.getLogger("spotipy").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Spotuify(App):
    CSS_PATH = "css/playlist.tcss"

    def compose(self) -> ComposeResult:
        yield Player()
        yield PlayerControls()


if __name__ == '__main__':
    app = Spotuify()
    app.run()
