import logging
from textual import on
from textual.app import ComposeResult
from textual.widgets import Static, ListView, DataTable
from textual.containers import Horizontal
from spotify_api.spotify_utils import (
    load_tracks,
    load_user_playlists,
    start_playback_on_active_device,
)
from collections import deque
from tools.widgets import PlaylistLabel, TrackProgress
from tools.track import Track
from spotify_player.seek_controller import SeekController
from tools.playback_monitor import PlaybackMonitor
from spotify_api.spotify_client import SpotifyClient

SP = SpotifyClient.get_instance()


class PlaylistTrackQueue:
    def __init__(self):
        self.queues = {}

    def add_tracks(self, playlist: str, track_uris):
        if playlist not in self.queues:
            self.queues[playlist] = deque()
        self.queues[playlist].extend(track_uris)

    def next_track(self, playlist: str):
        if playlist in self.queues and len(self.queues[playlist]) > 0:
            return self.queues[playlist].popleft()
        return None

    def current_track(self, playlist: str):
        if playlist in self.queues and len(self.queues[playlist]) > 0:
            return self.queues[playlist][0]
        return None

    def queue_length(self, playlist: str):
        if playlist in self.queues:
            return len(self.queues[playlist])
        return 0

    def clear_queue(self, playlist: str):
        if playlist in self.queues:
            self.queues[playlist].clear()

    def remove_queue_at_track_uri(self, playlist: str, curr_track_uri: str):
        while (
            len(self.queues[playlist]) > 0
            and self.queues[playlist][0] != curr_track_uri
        ):
            self.queues[playlist].popleft()


class Player(Static):
    BINDINGS = [
        ("ctrl+d", "scroll_down", "Scroll Down"),
        ("ctrl+u", "scroll_up", "Scroll Up"),
        ("n", "next_track", "Next Track"),
        ("p", "previous_track", "Previous Track"),
        ("right_square_bracket", "seek_forward", "Seek +10s"),
        ("left_square_bracket", "seek_backward", "Seek -10s"),
    ]

    def __init__(self):
        super().__init__()
        self.track_queue = PlaylistTrackQueue()
        self.curr_displayed_tracks = {}
        self.prev_displayed_tracks = {}
        self.curr_track = None
        self.playlist_tracks = {}
        self.curr_row_index = -1
        self.curr_displayed_playlist = None
        self.curr_playing_playlist = None
        self.curr_playing_playist_uri = None
        self.track_table = None
        self.tabs = None
        self.highlighted_track = None
        self.prev_tracks = None
        self.track_progress = None
        self.playlist_list = None
        self.track_table = None
        self.playlists = None
        self.playlist_names = None
        self.playlist_ids = None
        self.tracks = None
        self.seek_controller = None
        self._playback_timer = None
        self._pending_playback = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ListView(id="playlist-tabs")
            yield DataTable(id="playlist-table")

    def on_mount(self) -> None:
        self.playlist_list = self.query_one(ListView)
        self.track_table = self.query_one(DataTable)
        self.track_table.add_columns("Track", "Artist", "Album", "Length")
        self.track_table.cursor_type = "row"
        self.playlist_list.border_title = "Playlists"
        self.track_table.border_title = "Tracks"
        self.playlists = SP.current_user_playlists()
        self.playlist_names, self.playlist_ids = load_user_playlists(
            self.playlists)
        self.track_progress = self.app.query_one(TrackProgress)
        self.seek_controller = SeekController(self, self.track_progress)
        added_playlist_names = set()

        for playlist in self.playlist_names:
            if playlist not in added_playlist_names:
                self.playlist_list.append(PlaylistLabel(playlist))
                added_playlist_names.add(playlist)
            else:
                added_playlist_names = []

        # Sync to any already-playing track AFTER the UI has mounted, as a
        # background worker, so the initial render isn't blocked by the chain
        # of Spotify API calls (and the page-seeking loop) this performs.
        self.run_worker(self.check_if_track_playing,
                        thread=True, exclusive=True)

    def load_playlist_content(self, playlist_name) -> None:
        if playlist_name:
            self.track_table.visible = True
            self.track_table.clear()

            track_list, unformatted_track_list = self.fetch_playlist_tracks(
                playlist_name
            )

            for i, (track_list_item, unformatted_track_list_item) in enumerate(
                zip(track_list, unformatted_track_list)
            ):
                unique_key = f"{unformatted_track_list_item[0]}_{i}"
                try:
                    self.track_table.add_row(*track_list_item, key=unique_key)
                except Exception as e:
                    logging.warning(
                        f"Error adding row for track {track_list_item[0]}: {e}"
                    )
                self.curr_displayed_playlist = playlist_name

    def fetch_playlist_tracks(self, playlist_name: str):
        self.curr_displayed_playlist = playlist_name
        results = SP.playlist(
            self.playlist_ids[playlist_name], fields="tracks, next, items"
        )
        self.tracks = results["tracks"]

        track_list, unformatted_track_list = load_tracks(
            self.tracks,
            self.curr_displayed_playlist,
            self.playlist_tracks,
        )
        self.curr_displayed_tracks[playlist_name] = self.tracks
        return track_list, unformatted_track_list

    def fetch_next_playlist_tracks(self, playlist_name: str, tracks):
        self.curr_displayed_playlist = playlist_name

        track_list, unformatted_track_list = load_tracks(
            tracks,
            self.curr_displayed_playlist,
            self.playlist_tracks,
        )

        self.curr_displayed_tracks[playlist_name] = tracks
        return track_list, unformatted_track_list

    def on_track_ended(self, message) -> None:
        """Auto-advance when the monitor reports the playing track ended.

        Only advance our own queue when the track that ended is the one we
        believe we were playing; external (TV) changes that don't match our
        queue state are left alone.
        """
        if self.curr_playing_playlist is None:
            return
        self.play_next_track()

    def play_next_track(self) -> None:
        playlist = self.curr_playing_playlist
        pt = self.playlist_tracks.get(playlist)
        next_track_uri = self.track_queue.next_track(playlist)
        if next_track_uri is None:
            # Queue empty: try to load the next page of the playlist
            while self.action_scroll_down():
                pt = self.playlist_tracks.get(playlist)
                next_tracks = self.curr_displayed_tracks[playlist]
                next_track_uri = next_tracks["items"][0]["track"]["uri"]

                track = pt.by_uri(next_track_uri) if pt else None
                if track is None:
                    return
                self.curr_track = track
                self.curr_row_index = track.row_index
                self.track_table.move_cursor(row=self.curr_row_index)

                self.create_queue()
                self.curr_playing_playist_uri = str(
                    "spotify:playlist:" + self.playlist_ids[playlist]
                )
                self._start_playback_async(
                    next_track_uri, self.curr_playing_playist_uri
                )
                return
            # No more pages: nothing left to play
            return

        # Normal case: we have a next track in the queue — play it.
        track = pt.by_uri(next_track_uri) if pt else None
        if track is None:
            return
        self.curr_playing_playist_uri = str(
            "spotify:playlist:" + self.playlist_ids[playlist]
        )

        # Update cursor/state immediately, then play off the UI thread.
        self.curr_track = track
        self.curr_row_index = track.row_index
        self.track_table.move_cursor(row=self.curr_row_index)
        self._start_playback_async(
            next_track_uri, self.curr_playing_playist_uri)

    def action_next_track(self) -> None:
        """Skip to the next track (keybinding)."""
        if self.curr_playing_playlist is None:
            return
        self.play_next_track()

    def action_previous_track(self) -> None:
        """Skip to the previous track in the current playlist (keybinding)."""
        if self.curr_playing_playlist is None:
            return
        playlist = self.curr_playing_playlist
        pt = self.playlist_tracks.get(playlist)
        if pt is None or not isinstance(self.curr_track, Track):
            return

        curr_index = pt.index_of_uri(self.curr_track.uri)
        if curr_index is None or curr_index <= 0:
            # Unknown position, or already at the first track.
            return

        prev_track = pt.by_index(curr_index - 1)
        if prev_track is None:
            return

        self.curr_playing_playist_uri = str(
            "spotify:playlist:" + self.playlist_ids[playlist]
        )

        # Update local state and cursor immediately so the UI responds instantly,
        # then send the (blocking) playback command off the UI thread.
        self.curr_track = prev_track
        self.curr_row_index = prev_track.row_index
        self.track_table.move_cursor(row=self.curr_row_index)
        self.create_queue()
        self._start_playback_async(
            prev_track.uri, self.curr_playing_playist_uri)

    def _start_playback_async(self, track_uri: str, playlist_uri: str) -> None:
        """Debounced playback: rapid n/p presses each move the cursor, but the
        actual Spotify command only fires ~250ms after presses settle, to the
        final track — mirroring the seek scrubber's debounce."""
        self._pending_playback = (track_uri, playlist_uri)
        if self._playback_timer is not None:
            self._playback_timer.stop()
        self._playback_timer = self.set_timer(0.25, self._commit_playback)

    def _commit_playback(self) -> None:
        self._playback_timer = None
        pending = self._pending_playback
        if pending is None:
            return
        self._pending_playback = None
        track_uri, playlist_uri = pending
        self.run_worker(
            lambda: start_playback_on_active_device(track_uri, playlist_uri),
            thread=True,
            exclusive=True,
        )

    def check_if_track_playing(self) -> None:
        # NOTE: runs on a worker thread (see on_mount). The blocking SP.* reads
        # are fine here, but anything that touches widgets must be marshalled
        # back onto the UI thread via self.app.call_from_thread.
        # current_playback() carries context more reliably than
        # currently_playing(), especially for auto-continued playback.
        info = SP.current_playback()
        if not info or not info.get("item"):
            return

        context = info.get("context")
        if context and context.get("type") == "playlist":
            # Fast path: Spotify told us which playlist is playing.
            playlist_id = context["uri"].split(":")[-1]
            playlist_name = SP.playlist(playlist_id).get("name")
            self._sync_to_playlist(playlist_name, info["item"]["uri"])
            return

        # No playlist context (common when a track auto-continues). Fall back to
        # searching the user's playlists for the playing track's URI.
        self._sync_without_context(info["item"]["uri"])

    def _sync_to_playlist(self, playlist_name, track_uri) -> None:
        """Load a known playlist, page to the track, and highlight both panes."""
        if not playlist_name:
            return
        self.curr_playing_playlist = playlist_name

        self.app.call_from_thread(self.load_playlist_content, playlist_name)

        if playlist_name in self.playlist_names:
            playlist_index = self.playlist_names.index(playlist_name)
            self.app.call_from_thread(
                self._set_playlist_cursor, playlist_index)

        track = self._find_loaded_track(track_uri)
        while track is None and self.app.call_from_thread(self.action_scroll_down):
            track = self._find_loaded_track(track_uri)

        if track is not None:
            self.curr_track = track
            self.curr_row_index = track.row_index
            self.app.call_from_thread(
                self.track_table.move_cursor, row=self.curr_row_index)
            self.app.call_from_thread(self.track_table.focus)
            self.create_queue()

    def _sync_without_context(self, track_uri) -> None:
        """No playlist context from Spotify: search the user's playlists for the
        playing track and sync to the first one that contains it."""
        for playlist_name in self.playlist_names or []:
            playlist_id = self.playlist_ids[playlist_name]
            try:
                results = SP.playlist(
                    playlist_id, fields="tracks.items.track.uri")
            except Exception:
                continue
            uris = [
                item["track"]["uri"]
                for item in results.get("tracks", {}).get("items", [])
                if item.get("track")
            ]
            if track_uri in uris:
                self._sync_to_playlist(playlist_name, track_uri)
                return
        # Not found in any playlist's first page — leave UI as-is rather than
        # showing a stale highlight.

    def _find_loaded_track(self, uri):
        """Look up a track by URI in the currently loaded page, or None."""
        pt = self.playlist_tracks.get(self.curr_playing_playlist)
        return pt.by_uri(uri) if pt else None

    def _set_playlist_cursor(self, index: int) -> None:
        """Move the playlist-list highlight to the given index (UI thread)."""
        try:
            self.playlist_list.index = index
        except Exception:
            pass

    def create_queue(self) -> None:
        # Use the monitor's cached state instead of a blocking API read.
        monitor = self.app.query_one(PlaybackMonitor)
        if not monitor.is_playing:
            return

        if not isinstance(self.curr_track, Track):
            return
        playlist = self.curr_playing_playlist
        pt = self.playlist_tracks.get(playlist)
        if pt is None:
            return
        curr_track_uri = self.curr_track.uri
        if curr_track_uri in self.track_queue.queues.get(playlist, []):
            self.track_queue.remove_queue_at_track_uri(
                playlist, curr_track_uri)
        else:
            keys_list = pt.uris()
            try:
                curr_index = keys_list.index(curr_track_uri)
                next_tracks = keys_list[curr_index + 1:]
                self.track_queue.clear_queue(playlist)
                self.track_queue.add_tracks(playlist, next_tracks)
            except ValueError:
                self.track_queue.clear_queue(playlist)

    def action_scroll_down(self) -> bool:
        if (
            self.curr_displayed_playlist is not None
            and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None
        ):
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            next_tracks = SP.next(curr_tracks)

            if next_tracks:
                if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                    self.prev_displayed_tracks[self.curr_displayed_playlist] = [
                    ]

                self.prev_displayed_tracks[self.curr_displayed_playlist].append(
                    curr_tracks
                )
                self.format_next_track_list(next_tracks)
                return True
            else:
                return False

    def action_scroll_up(self) -> None:
        if (
            self.curr_displayed_playlist is not None
            and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None
        ):
            if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                return
            if len(self.prev_displayed_tracks[self.curr_displayed_playlist]) > 0:
                self.prev_tracks = self.prev_displayed_tracks[
                    self.curr_displayed_playlist
                ].pop(0)
                if self.prev_tracks:
                    self.format_next_track_list(self.prev_tracks)

    def format_next_track_list(self, tracks) -> None:
        track_list, unformatted_track_list = self.fetch_next_playlist_tracks(
            self.curr_displayed_playlist, tracks
        )
        self.track_table.clear()
        for i, (track_list_item, unformatted_track_list_item) in enumerate(
            zip(track_list, unformatted_track_list)
        ):
            unique_key = f"{unformatted_track_list_item[0]}_{i}"
            self.track_table.add_row(*track_list_item, key=unique_key)

    def key_space(self) -> None:
        # Read the monitor's last-known state instead of a blocking API call,
        # so play/pause is instant. The pause/start commands still go to Spotify.
        monitor = self.app.query_one(PlaybackMonitor)
        if monitor.is_playing:
            SP.pause_playback()
            self.track_progress.pause_progress_bar()
        else:
            SP.start_playback()
            self.track_progress.resume_progress_bar()

    @on(ListView.Selected, "#playlist-tabs")
    def playlist_selected(self, event: ListView.Selected) -> None:
        self.curr_displayed_playlist = str(event.item.label)
        self.load_playlist_content(str(event.item.label))

    @on(DataTable.RowSelected, "#playlist-table")
    def track_selected(self, event: DataTable.RowSelected) -> None:
        unique_track_name = event.row_key.value
        self.curr_playing_playlist = self.curr_displayed_playlist
        pt = self.playlist_tracks.get(self.curr_playing_playlist)
        track = pt.by_unique_name(unique_track_name) if pt else None
        if track is None:
            return
        track_uri = track.uri
        self.curr_playing_playist_uri = str(
            "spotify:playlist:" + self.playlist_ids[self.curr_playing_playlist]
        )

        start_playback_on_active_device(
            track_uri, self.curr_playing_playist_uri)

        self.curr_track = track
        self.curr_row_index = track.row_index

        self.create_queue()

        self.track_table.move_cursor(row=self.curr_row_index)

    def action_seek_forward(self) -> None:
        self.seek_controller.seek_forward()

    def action_seek_backward(self) -> None:
        self.seek_controller.seek_backward()
