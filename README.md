# Spotuipy

_A lightweight terminal UI for controlling Spotify playback, written in Python with [Textual](https://textual.textualize.io/) and [Spotipy](https://spotipy.readthedocs.io/)._

_Currently a work in progress._

![Spotuipy-UI](/images/spotuipy_player_image.png?raw=true)

## About

Spotuipy is a terminal-based Spotify remote. It browses your playlists, starts playback on an active device, and shows the currently playing track — title, artist, album art, a live progress bar, and the device playback is coming from. It controls Spotify devices through the Web API rather than playing audio itself, so playback needs to happen on a Spotify Connect device — either an existing one (desktop app, web player, phone) or a local headless daemon you run yourself (see [Local playback with spotifyd](#local-playback-with-spotifyd)).

Playback state is driven by a single background poller (`PlaybackMonitor`) that queries Spotify once per second and broadcasts changes as Textual messages. The UI widgets react to those messages, so the display stays in sync even when the track is changed from another device.

## Features

- Browse your Spotify playlists and tracks in a terminal table
- Start playback on the active device by selecting a track
- Live "now playing" display: title, artist, and the device name
- Album art rendered inline (see terminal support below)
- Progress bar with smooth local animation, corrected against Spotify each second
- Automatic UI updates when playback changes on any device
- Client-side play queue that advances through a playlist

## Terminal support for album art

Album covers are rendered with [`textual-image`](https://pypi.org/project/textual-image/), which uses the Terminal Graphics Protocol (TGP) or Sixel. For full-quality images, use a terminal that supports one of these:

- **Kitty** (full TGP support)
- **Ghostty**
- **WezTerm** (mostly complete TGP)

In terminals without graphics support (e.g. plain xterm, rxvt-unicode), the rest of the app works but album art falls back to a low-fidelity rendering or none.

## Requirements

- Python 3.10+
- A Spotify account and a registered app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- A Spotify Connect device for playback — either an existing one, or [spotifyd](#local-playback-with-spotifyd) running locally (Spotify Premium required for spotifyd)

## Setup

1. Clone the repository and enter it:

   ```bash
   git clone https://github.com/mattdelacruz/spotuipy.git
   cd spotuipy
   ```

2. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a Spotify app in the Developer Dashboard. Note the **Client ID** and **Client Secret**, and add a redirect URI of `http://127.0.0.1:8888/callback` in the app settings (loopback redirects must use the explicit `127.0.0.1` form, not `localhost`).

4. Create a `.env` file in the project root:

   ```
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

   The `.env` file is gitignored and should never be committed.

## Usage

With Spotify playing on a device, run:

```bash
python main.py
```

On first launch a browser window opens for Spotify authorization. After you approve, a token is cached locally so subsequent runs don't prompt again.

### Controls

| Key              | Action                              |
| ---------------- | ----------------------------------- |
| `Enter` / select | Play the highlighted track          |
| `Space`          | Play / pause                        |
| `Ctrl+D`         | Scroll down (next page of tracks)   |
| `Ctrl+U`         | Scroll up (previous page of tracks) |
| `N`              | Play next track                     |
| `P`              | Play previous track                 |
| `[`              | Seek 10 seconds backward            |
| `]`              | Seek 10 seconds forward             |

## Local playback with spotifyd

By default Spotuipy controls whatever Spotify Connect device is available (your phone, desktop app, a TV, etc.). To play audio directly on the machine running Spotuipy — with no other device involved — run [spotifyd](https://github.com/Spotifyd/spotifyd), a lightweight headless Spotify Connect daemon. **This requires Spotify Premium.**

Spotuipy's device selection prefers a Connect device named `spotifyd`, so once the daemon is running and registered, selecting a track plays through this machine automatically.

1. Install spotifyd (via your package manager or the project's releases).

2. Create `~/.config/spotifyd/spotifyd.conf`. A minimal PulseAudio/PipeWire config:

   ```ini
   [global]
   backend = "pulseaudio"
   device_name = "spotifyd"
   bitrate = 320
   cache_path = "~/.cache/spotifyd"
   volume_normalisation = true
   normalisation_pregain = -10
   ```

   The `device_name` must be `spotifyd` to match Spotuipy's device preference. Adjust `backend` for your audio system (`alsa`, `pulseaudio`, etc.).

3. Authenticate once via OAuth. Spotify has phased out username/password login, so spotifyd uses a browser-based flow that persists credentials under `cache_path`:

   ```bash
   spotifyd authenticate
   ```

   Settle on `cache_path` before doing this, since the login data is stored there.

4. Run spotifyd in the background as a systemd user service so it's always available:

   ```bash
   systemctl --user enable --now spotifyd
   ```

   (On macOS, use `brew services start spotifyd` or a launchd agent instead.)

5. Launch Spotuipy and select a track — playback transfers to the local `spotifyd` device and plays through this machine's speakers.

To verify spotifyd is registered, it should appear in your device list (for example, the Spotify Connect picker in any official client, or a quick `spotipy` `devices()` call). OAuth login registers it with Spotify's backend automatically, so you do not need to claim it from another device first.

## Required scopes

Spotuipy requests these Spotify scopes:

`playlist-read-private`, `playlist-read-collaborative`, `user-read-playback-state`, `user-modify-playback-state`, `user-read-currently-playing`

## Project structure

```
main.py                       App entry point and message routing
spotify_api/
  spotify_client.py           Authenticated Spotipy client (singleton)
  spotify_utils.py            Playback control and track loading helpers
spotify_player/
  player.py                   Playlist/track browsing, queue, auto-advance
  player_controls.py          Now-playing controls layout
tools/
  widgets.py                  PlaybackMonitor and UI widgets
  formatting.py               Duration/text formatting helpers
css/
  playlist.tcss               Textual styling
```

## Notes

- Spotify's Web API has no endpoint for managing the playback queue, so Spotuipy maintains its own client-side queue that mirrors playlist order and drives playback track by track.
- Closing the app does not stop playback — it's a remote control, not the player.
