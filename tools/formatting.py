def truncate_track(text, max_width) -> str:
    if len(text) > max_width:
        return text[:max_width]
    return text

def format_artist_track(artist_name, track_name, album_name, max_width):
    return truncate_track(artist_name, max_width), truncate_track(track_name, max_width), truncate_track(album_name, max_width)

def format_duration(duration_ms: int):
    minutes = int((duration_ms / 1000) / 60)
    seconds = int((duration_ms / 1000) % 60)
    return f"{minutes}:{str(seconds).zfill(2)}"
