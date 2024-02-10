from textual.app import ComposeResult
from textual.widgets import Static, Label, ListView, ListItem, DataTable
from textual.containers import Horizontal
from textual import events, on
from spotify_utils import load_tracks, load_user_playlists, start_playback_on_active_device
from widgets import PlaylistLabel, TrackProgress
from spotify_client import SpotifyClient

sp = SpotifyClient.get_instance()

class Player(Static):
    BINDINGS = [
        ("ctrl+d", "scroll_down", "Scroll Down"),
        ("ctrl+u", "scroll_up", "Scroll Up"),
    ]

    def __init__(self):
        super().__init__()
        self.curr_displayed_tracks = {}
        self.prev_displayed_tracks = {}
        self.curr_song = {}
        self.track_info = {}
        self.track_uris = {}
        self.track_queue = {}
        self.uri_list = {}
        self.curr_displayed_playlist = None
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
        added_playlist_names = set()

        for playlist_name in self.playlist_names:
            if playlist_name not in added_playlist_names:
                self.playlist_list.append(PlaylistLabel(playlist_name))
                added_playlist_names.add(playlist_name)
            else:
                print(f"Duplicate playlist name '{playlist_name}' skipped.")
        added_playlist_names = []

    def load_playlist_content(self, playlist_name) -> None:
        if playlist_name:
            self.track_table.visible = True
            self.track_table.clear()
            track_list, unformatted_track_list = self.fetch_playlist_tracks(playlist_name)
            
            for i, (track_list_item, unformatted_track_list_item) in enumerate(zip(track_list, unformatted_track_list)):
                unique_key = f"{unformatted_track_list_item[0]}_{i}"
                print(track_list_item, unique_key)
                try:
                    self.track_table.add_row(*track_list_item, key=unique_key)
                except Exception as e:
                    print(f"Error adding row with key {unique_key}: {e}")

    def fetch_playlist_tracks(self, playlist_name: str):
        self.curr_displayed_playlist = playlist_name 
        results = sp.playlist(self.playlist_ids[playlist_name], fields = "tracks, next, items")
        self.tracks = results['tracks']

        track_list, unformatted_track_list, self.track_info, self.track_uris, self.uri_list = load_tracks(self.tracks, self.track_table, self.curr_displayed_playlist)
        self.curr_displayed_tracks[playlist_name] = self.tracks
        return track_list, unformatted_track_list

    def fetch_next_playlist_tracks(self, playlist_name: str, tracks):
        self.curr_displayed_playlist = playlist_name

        track_list, unformatted_track_list, self.track_info, self.track_uris, self.uri_list = load_tracks(tracks, self.track_table, self.curr_displayed_playlist)
        
        self.curr_displayed_tracks[playlist_name] = tracks
        return track_list, unformatted_track_list

    def create_queue(self) -> None:
        curr_playing = sp.currently_playing()
        
        if not curr_playing or not curr_playing['is_playing']:
            return

        curr_track_name = self.curr_song
        playlist = self.curr_displayed_playlist
        playlist_info = self.track_info.get(playlist, {})
        curr_track_uri = playlist_info.get(curr_track_name, {}).get('uri')

        if curr_track_uri:
            self.track_queue.setdefault(playlist, [])
            try:
                curr_index = self.track_queue[playlist].index(curr_track_uri)
                self.track_queue[playlist] = self.track_queue[playlist][curr_index+1:]
            except ValueError:
                keys_list = list(self.uri_list.get(playlist, []))
                try:
                    curr_index = keys_list.index(curr_track_uri)
                    next_tracks = keys_list[curr_index + 1:]
                    self.clear_queue(playlist)

                    for next_track_uri in next_tracks:
                        self.enqueue_track(playlist, next_track_uri)
                        
                except ValueError:
                    self.clear_queue(playlist)
                    pass

    def enqueue_track(self, playlist_name: str, track_uri: str) -> None:
        if playlist_name not in self.track_queue:
            self.track_queue[playlist_name] = []            
        self.track_queue[playlist_name].append(track_uri)

    def dequeue_track(self, playlist_name: str) -> str:
        if playlist_name in self.track_queue and len(self.track_queue[playlist_name]) > 0:
            return self.track_queue[playlist_name].pop(0)
        return None 

    def clear_queue(self, playlist_name: str) -> None:
        if playlist_name in self.track_queue:
            self.track_queue[playlist_name] = []

    def update_queue(self, playlist_name: str, track_info: list) -> None:
        self.track_queue[playlist_name] = track_info

    def action_scroll_down(self) -> None:
        if self.curr_displayed_playlist is not None and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None:
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            next_tracks = sp.next(curr_tracks)
            if next_tracks:
                if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                    self.prev_displayed_tracks[self.curr_displayed_playlist] = []
                self.prev_displayed_tracks[self.curr_displayed_playlist].append(curr_tracks)
                self.format_next_track_list(next_tracks)
            else:
                print("No next tracks")

    def action_scroll_up(self) -> None:
        if self.curr_displayed_playlist is not None and self.curr_displayed_tracks.get(self.curr_displayed_playlist) is not None:
            if self.curr_displayed_playlist not in self.prev_displayed_tracks:
                return
            curr_tracks = self.curr_displayed_tracks[self.curr_displayed_playlist]
            if len(self.prev_displayed_tracks[self.curr_displayed_playlist]) > 0:
                self.prev_tracks = self.prev_displayed_tracks[self.curr_displayed_playlist].pop()
                if self.prev_tracks:
                    self.format_next_track_list(self.prev_tracks)
        else:
            print("No previous tracks")

    def format_next_track_list(self, tracks) -> None:
        track_list, unformatted_track_list = self.fetch_next_playlist_tracks(self.curr_displayed_playlist, tracks)
        self.track_table.clear()
        for track_list_item, unformatted_track_list_item in zip(track_list, unformatted_track_list):
            unique_key = unformatted_track_list_item[0]
            self.track_table.add_row(*track_list_item, key=unique_key)

    def key_space(self) -> None:
        currently_playing = sp.currently_playing()
        if currently_playing:
            if currently_playing['is_playing']:
                sp.pause_playback()
                self.track_progress.pause_progress_bar()
            else:
                sp.start_playback()
                self.track_progress.resume_progress_bar()
        else:
            print("No track currently playing!")
                
    @on(ListView.Selected, "#playlist-tabs")
    def playlist_selected(self, event: ListView.Selected) -> None:
        self.curr_displayed_playlist = str(event.item.label)
        self.load_playlist_content(str(event.item.label))
    
    @on(DataTable.RowSelected, "#playlist-table")
    def song_selected(self, event: DataTable.RowSelected) -> None:
        key_parts = event.row_key.value.split('_')
        original_song_title = '_'.join(key_parts[:-1])
        track_uri = self.track_info[self.curr_displayed_playlist][original_song_title]['uri']
        
        start_playback_on_active_device(track_uri)
        self.curr_song = self.track_uris[track_uri]
        self.create_queue()
