from textual.app import App, ComposeResult
from spotify_player.player import Player
from spotify_player.player_controls import PlayerControls
from tools.widgets import PlaybackMonitor, CurrentTrack, TrackProgress, AlbumCover
import logging
logging.getLogger("spotipy").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Spotuify(App):
    CSS_PATH = "css/playlist.tcss"

    def compose(self) -> ComposeResult:
        yield Player()
        yield PlayerControls()
        yield PlaybackMonitor()

    # The monitor's messages bubble up here; fan them out to the widgets and
    # the Player so there is a single playback poll feeding every consumer.
    def on_playback_monitor_playback_changed(
            self, message: PlaybackMonitor.PlaybackChanged) -> None:
        self.query_one(
            CurrentTrack).on_playback_monitor_playback_changed(message)
        self.query_one(
            TrackProgress).on_playback_monitor_playback_changed(message)
        self.query_one(
            AlbumCover).on_playback_monitor_playback_changed(message)

    def on_playback_monitor_playback_stopped(
            self, message: PlaybackMonitor.PlaybackStopped) -> None:
        self.query_one(
            CurrentTrack).on_playback_monitor_playback_stopped(message)
        self.query_one(
            TrackProgress).on_playback_monitor_playback_stopped(message)
        self.query_one(
            AlbumCover).on_playback_monitor_playback_stopped(message)

    def on_playback_monitor_track_ended(
            self, message: PlaybackMonitor.TrackEnded) -> None:
        self.query_one(Player).on_track_ended(message)


if __name__ == '__main__':
    app = Spotuify()
    app.run()
