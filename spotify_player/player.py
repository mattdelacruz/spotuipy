from textual import events, on
from textual.app import ComposeResult
from textual.widgets import Static, Label, ListView, ListItem, DataTable
from textual.containers import Horizontal
from textual.timer import Timer
from spotify_api.spotify_utils import load_tracks, load_user_playlists, start_playback_on_active_device
from collections import deque
from tools.widgets import PlaylistLabel, TrackProgress
from spotify_api.spotify_client import SpotifyClient

sp = SpotifyClient.get_instance()
finish_timer: Timer

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
       while len(self.queues[playlist]) > 0 and self.queues[playlist][0] != curr_track_uri:
            self.queues[playlist].popleft()

class Player(Static):
    BINDINGS = [
        ("ctrl+d", "scroll_down", "Scroll Down"),
        ("ctrl+u", "scroll_up", "Scroll Up"),
    ]

    def __init__(self):
        super().__init__()
        self.track_queue = PlaylistTrackQueue()
        self.curr_displayed_tracks = {}
        self.prev_displayed_tracks = {}
        self.curr_track = {}
        self.track_info = {}
        self.track_uris = {}
        self.uri_list = {}
        self.curr_row_index = -1
        self.curr_displayed_playlist = None
        self.curr_playing_playlist = None
        self.curr_playing_playist_uri = None
        self.track_table = None
        self.tabs = None
        self.highlighted_track = None
        self.prev_tracks = None
        self.track_progress = None

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
        self.playlists = sp.current_user_playlists()
        self.playlist_names, self.playlist_ids = load_user_playlists(self.playlists)
        self.track_progress = self.app.query_one(TrackProgress)
        self.finish_timer = self.set_interval(10, self.is_track_finished, pause=False)
        added_playlist_names = set()

        self.check_if_track_playing()

        for playlist in self.playlist_names:
            if playlist not in added_playlist_names:
                self.playlist_list.append(PlaylistLabel(playlist))
                added_playlist_names.add(playlist)
            else:
                print(f"Duplicate playlist name '{playlist}' skipped.")

        added_playlist_names = []

    def load_playlist_content(self, playlist_name) -> None:
        if playlist_name:
            self.track_table.visible = True
            self.track_table.clear()

            track_list, unformatted_track_list = self.fetch_playlist_tracks(playlist_name)
            
            for i, (track_list_item, unformatted_track_list_item) in enumerate(zip(track_list, unformatted_track_list)):
                unique_key = f"{unformatted_track_list_item[0]}_{i}"
                try:
                    self.track_table.add_row(*track_list_item, key=unique_key)
                except Exception as e:
                    print(f"Error adding row with key {unique_key}: {e}")

            self.curr_displayed_playlist = playlist_name

    def fetch_playlist_tracks(self, playlist_name: str):
        self.curr_displayed_playlist = playlist_name 
        results = sp.playlist(self.playlist_ids[playlist_name], fields = "tracks, next, items")
        self.tracks = results['tracks']

        track_list, unformatted_track_list = load_tracks(self.tracks, self.track_table, self.curr_displayed_playlist, self.track_info, self.track_uris, self.uri_list)
        self.curr_displayed_tracks[playlist_name] = self.tracks
        return track_list, unformatted_track_list

    def fetch_next_playlist_tracks(self, playlist_name: str, tracks):
        self.curr_displayed_playlist = playlist_name

        track_list, unformatted_track_list = load_tracks(tracks, self.track_table, self.curr_displayed_playlist, self.track_info, self.track_uris, self.uri_list)
        
        self.curr_displayed_tracks[playlist_name] = tracks
        return track_list, unformatted_track_list

    def is_track_finished(self) -> None:
        if self.track_progress.get_is_finished() and self.track_progress.track_switch:
            self.track_progress.track_switch = False
            self.play_next_track()

    def play_next_track(self) -> None:
        print('playing next track...')
        next_track_uri = self.track_queue.next_track(self.curr_playing_playlist)
        print(next_track_uri)
        if next_track_uri is None:
            # check for next page
            print('next track uri is none!')
            return
            while self.action_scroll_down():
                next_tracks = self.curr_displayed_tracks[self.curr_playing_playlist] #get the track of the first item in the list
                next_track_uri = next_tracks['items'][0]['track']['uri']
                next_track_artist = next_tracks['items'][0]['track']['artists'][0]['name']
                
                self.curr_track = self.track_uris[next_track_uri][next_track_artist]
                self.curr_row_index = self.track_info[self.curr_playing_playlist][self.curr_track]['row_index']
                self.track_table.move_cursor(row=self.curr_row_index)
                
                self.create_queue()
                self.curr_playing_playist_uri = str("spotify:playlist:" + self.playlist_ids[self.curr_playing_playlist])
                start_playback_on_active_device(next_track_uri, self.curr_playing_playist_uri)
                self.finish_timer.resume()
                return
            else:
                print('No more tracks to play!')
                self.finish_timer.pause()
                return

        next_track_artist = self.track_info[self.curr_playing_playlist][next_track_uri]['artist']
        self.curr_playing_playist_uri = str("spotify:playlist:" + self.playlist_ids[self.curr_playing_playlist])
        start_playback_on_active_device(next_track_uri, self.curr_playing_playist_uri)
        
        self.curr_track = self.track_uris[next_track_uri][next_track_artist]
        self.curr_row_index = self.track_info[self.curr_playing_playlist][self.curr_track]['row_index']
        self.track_table.move_cursor(row=self.curr_row_index)
        self.finish_timer.resume()

    def check_if_track_playing(self) -> None:
        print('Checking if track is playing...')
        curr_playing_info = sp.currently_playing()
        print(curr_playing_info)
        if curr_playing_info and curr_playing_info['context']:
            print('Context: ', curr_playing_info['context'])
            match curr_playing_info['context']['type']:
                case 'playlist':
                    playlist_uri = curr_playing_info['context']['uri']  
                    playlist_id = playlist_uri.split(':')[-1]
                    self.curr_playing_playlist = sp.playlist(playlist_id).get('name')

                    self.load_playlist_content(self.curr_playing_playlist)

                    curr_track_uri = curr_playing_info['item']['uri']
                    curr_track_artist = curr_playing_info['item']['artists'][0]['name']

                    self.curr_track = self.track_uris[curr_track_uri][curr_track_artist]
                    self.curr_row_index = self.track_info[self.curr_playing_playlist][self.curr_track]['row_index']
                    self.track_table.move_cursor(row=self.curr_row_index)

                    self.create_queue()
                    self.finish_timer.resume()
                case _:
                    print("No track is currently playing...")

    def create_queue(self) -> None:
        curr_playing = sp.currently_playing()

        if not curr_playing or not curr_playing['is_playing']:
            print("nothing is being played..")
            return

        playlist = self.curr_playing_playlist
        curr_track_uri = self.track_info[self.curr_playing_playlist][self.curr_track]['uri']
        if curr_track_uri in self.track_queue.queues.get(playlist, []):
            self.track_queue.remove_queue_at_track_uri(playlist, curr_track_uri)
        else:
            keys_list = list(self.uri_list[playlist])
            try:
                curr_index = keys_list.index(curr_track_uri)
                next_tracks = keys_list[curr_index + 1:]
                self.track_queue.clear_queue(playlist)
                self.track_queue.add_tracks(playlist, next_tracks)
            except ValueError:
                self.track_queue.clear_queue(playlist)

    def action_scroll_down(self) -> bool:
        if self.curr_displayed_playlist is not None and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None:
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            next_tracks = sp.next(curr_tracks)

            if next_tracks:
                if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                    self.prev_displayed_tracks[self.curr_displayed_playlist] = []

                self.prev_displayed_tracks[self.curr_displayed_playlist].append(curr_tracks)
                self.format_next_track_list(next_tracks)
                return True
            else:
                print("No next tracks")
                return False

    def action_scroll_up(self) -> None:
        if self.curr_displayed_playlist is not None and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None:
            if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                return
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            if len(self.prev_displayed_tracks[self.curr_displayed_playlist]) > 0:
                self.prev_tracks = self.prev_displayed_tracks[self.curr_displayed_playlist].pop(0)
                if self.prev_tracks:
                    self.format_next_track_list(self.prev_tracks)
        else:
            print("No previous tracks")

    def format_next_track_list(self, tracks) -> None:
        track_list, unformatted_track_list = self.fetch_next_playlist_tracks(self.curr_displayed_playlist, tracks)
        self.track_table.clear()
        for i, (track_list_item, unformatted_track_list_item) in enumerate(zip(track_list, unformatted_track_list)):
            unique_key = f"{unformatted_track_list_item[0]}_{i}"
            self.track_table.add_row(*track_list_item, key=unique_key)

    def key_space(self) -> None:
        currently_playing = sp.currently_playing()
        if currently_playing:
            if currently_playing['is_playing']:
                sp.pause_playback()
                self.finish_timer.pause()
                self.track_progress.pause_progress_bar()
            else:
                sp.start_playback()
                self.finish_timer.resume()
                self.track_progress.resume_progress_bar()
        else:
            print("No track currently playing!")
                
    @on(ListView.Selected, "#playlist-tabs")
    def playlist_selected(self, event: ListView.Selected) -> None:
        self.curr_displayed_playlist = str(event.item.label)
        self.load_playlist_content(str(event.item.label))
    
    @on(DataTable.RowSelected, "#playlist-table")
    def track_selected(self, event: DataTable.RowSelected) -> None:
        unique_track_name = event.row_key.value
        self.curr_playing_playlist = self.curr_displayed_playlist
        track_uri = self.track_info[self.curr_playing_playlist][unique_track_name]['uri']
        artist_name = self.track_info[self.curr_playing_playlist][unique_track_name]['artist']
        print("playing track", unique_track_name)
        self.curr_playing_playist_uri = str("spotify:playlist:" + self.playlist_ids[self.curr_playing_playlist])

        print('playlist_uri: ', self.curr_playing_playist_uri)
        start_playback_on_active_device(track_uri, self.curr_playing_playist_uri)
        
        self.curr_track = unique_track_name
        self.curr_row_index = self.track_info[self.curr_playing_playlist][unique_track_name]['row_index']

        self.create_queue()
        self.finish_timer.resume()

        self.track_table.move_cursor(row=self.curr_row_index)