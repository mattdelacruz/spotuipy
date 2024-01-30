import spotipy
import pytermgui as ptg
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

def setup_spotify_auth():
    client_id = os.environ.get("SPOTIPY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")
    scope = 'playlist-read-private'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret,                                                  redirect_uri=redirect_uri, scope=scope))
    return sp

def show_tracks(results):
    for i, item in enumerate(results['items']):
        track = item['track']
        print(
            "   %32.32s %s" %
            (track['artists'][0]['name'], track['name']))

if __name__ == '__main__':
    load_dotenv()
    sp = setup_spotify_auth() 
    playlists = sp.current_user_playlists()
    user_id = sp.me()['id']
    
    manager = ptg.WindowManager()
    
    
    for playlist in playlists['items']:
        if playlist['owner']['id'] == user_id:
            print(playlist['name'])
            #print('  total tracks', playlist['tracks']['total'])
            results = sp.playlist(playlist['id'], fields="tracks,next,items")
            tracks = results['tracks']
            #show_tracks(tracks)

            while tracks['next']:
                tracks = sp.next(tracks)
                #show_tracks(tracks)
                
