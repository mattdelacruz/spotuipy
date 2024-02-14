# spotify_client.py
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

class SpotifyClient:
    _instance = None
    load_dotenv()
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
                scope='playlist-read-private, playlist-read-collaborative, user-read-playback-state, user-modify-playback-state, user-read-currently-playing'
            ))
        return cls._instance