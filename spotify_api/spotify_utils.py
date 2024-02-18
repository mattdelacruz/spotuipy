import os
import spotipy
import time
from spotipy.oauth2 import SpotifyOAuth
from tools.formatting import format_duration, format_artist_track
from spotify_api.spotify_client import SpotifyClient

sp = SpotifyClient.get_instance()

def load_tracks(tracks, track_table, playlist, track_info, track_uris, uri_list) -> list:
    list_items = []
    unformatted_list_items = []
    uri_list[playlist] = []

    if playlist not in track_info:
        track_info[playlist] = {}

    for row_index, item in enumerate(tracks['items']):
        track = item['track']
        artist_name = track['artists'][0]['name']
        track_name = track['name']
        album_name = track['album']['name']
        duration_ms = track['duration_ms']
        duration = format_duration(duration_ms)
        uri = track['uri']
        unique_track_name = f"{track_name}_{row_index}"

        if track_name not in track_info[playlist]:
            track_info[playlist][track_name] = {}

        if uri not in track_uris:
            track_uris[uri] = {}

        if unique_track_name not in track_info[playlist]:
            track_info[playlist][unique_track_name] = {}
        
        if uri not in track_info[playlist]:
            track_info[playlist][uri] = {}

        artist_name_formatted, track_name_formatted, album_name_formatted = format_artist_track(artist_name, track_name, album_name, 20)

        list_items.append((track_name_formatted, artist_name_formatted, album_name_formatted, duration))
        unformatted_list_items.append((track_name, artist_name, album_name, duration))
        track_uris[uri][artist_name] = unique_track_name
        uri_list[playlist].append(uri)
        
        track_info[playlist][uri]['artist'] = artist_name
        track_info[playlist][unique_track_name]['track_name'] = track_name
        track_info[playlist][unique_track_name]['uri'] = uri
        track_info[playlist][unique_track_name]['artist'] = artist_name
        track_info[playlist][unique_track_name]['duration_ms'] = duration_ms
        track_info[playlist][unique_track_name]['row_index'] = row_index

    return list_items, unformatted_list_items

def find_active_device():
    devices = sp.devices()["devices"]
    speaker_device = next((device for device in devices if device["type"] == "Speaker"), None)
    if speaker_device:
        if speaker_device['is_active']:
            return -1
        return speaker_device["id"]
    else:
        return None


def start_playback_on_active_device(track_uri: str, playlist_uri: str) -> int:
    device_id = find_active_device()
    if device_id:
        if device_id != -1:
            sp.transfer_playback(device_id, force_play=False)
            sp.start_playback(device_id=device_id, uris=[track_uri])
        else:
            sp.start_playback(uris=[track_uri])
        if wait_for_playback_to_start(track_uri):
            return 1
        else:
            return 0
    else:
        print("No active device found.")
        return -1

def wait_for_playback_to_start(expected_track_uri: str, timeout=30) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_playback = sp.current_playback()
        if current_playback and current_playback.get('item') and current_playback['item']['uri'] == expected_track_uri:
            print("Playback started successfully.")
            return True
        time.sleep(1)
    print("Playback did not start within the expected timeout.")
    return False


def load_user_playlists(playlists):
    playlist_names = []
    playlist_ids = {}
    for playlist in playlists['items']:
        playlist_names.append(playlist['name'])
        playlist_ids[playlist['name']] = playlist['id']
    return playlist_names, playlist_ids