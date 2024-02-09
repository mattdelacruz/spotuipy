import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from formatting import format_duration, format_artist_track
from spotify_client import SpotifyClient

sp = SpotifyClient.get_instance()

def load_tracks(tracks, track_table, playlist) -> list:
    list_items = []
    unformatted_list_items = []
    track_info = {}
    track_uris = {}
    uri_list = {}
    uri_list[playlist] = []
    if playlist not in track_info:
        track_info[playlist] = {}
    for item in tracks['items']:
        track = item['track']
        artist_name = track['artists'][0]['name']
        track_name = track['name']
        album_name = track['album']['name']
        duration = format_duration(track['duration_ms'])

        if track_name not in track_info[playlist]:
            track_info[playlist][track_name] = {}

        artist_name_formatted, track_name_formatted, album_name_formatted = format_artist_track(artist_name, track_name, album_name, 20)

        list_items.append((track_name_formatted, artist_name_formatted, album_name_formatted, duration))
        unformatted_list_items.append((track_name, artist_name, album_name, duration))
        track_uris[track['uri']] = track_name
        uri_list[playlist].append(track['uri'])
        track_info[playlist][track_name]['uri'] = track['uri']
        track_info[playlist][track_name]['duration_ms'] = track['duration_ms']
    return list_items, unformatted_list_items, track_info, track_uris, uri_list

def find_active_device():
    devices = sp.devices()["devices"]
    speaker_device = next((device for device in devices if device["type"] == "Speaker"), None)
    if speaker_device:
        if speaker_device['is_active']:
            return -1
        return speaker_device["id"]
    else:
        return None

def start_playback_on_active_device(track_uri):
    device_id = find_active_device()
    print(device_id)
    if device_id:
        if device_id != -1:
            sp.transfer_playback(device_id, force_play=False)
            sp.start_playback(device_id=device_id, uris=[track_uri])
            return
        sp.start_playback(uris=[track_uri])
    else:
        print("No active device found.")
        # load some error window saying 404 device not found and add instructions for user to run a Spotify daemon like spotifyd
            
    
def load_user_playlists(playlists):
    playlist_names = []
    playlist_ids = {}
    for playlist in playlists['items']:
        playlist_names.append(playlist['name'])
        playlist_ids[playlist['name']] = playlist['id']
    return playlist_names, playlist_ids

