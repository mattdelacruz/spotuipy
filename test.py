from spotify_api.spotify_client import SpotifyClient

sp = SpotifyClient.get_instance()
for d in sp.devices()["devices"]:
    print(d["name"], d["type"], d["is_active"])
