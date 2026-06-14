from dataclasses import dataclass


@dataclass
class Track:
    """A single track within a playlist.

    Replaces the parallel track_info / track_uris / uri_list dicts: one object
    holds everything previously spread across three keying schemes, and the
    ordered PlaylistTracks collection below preserves position.
    """

    uri: str
    name: str
    artist: str
    album: str
    duration_ms: int
    row_index: int

    @property
    def unique_name(self) -> str:
        """Stable per-row identifier (name + row index), matching the old
        f"{track_name}_{row_index}" key so existing call sites can be migrated
        gradually."""
        return f"{self.name}_{self.row_index}"


class PlaylistTracks:
    """Ordered collection of Tracks for a single playlist.

    Provides the three lookups the app needs — by position, by URI, and by
    unique name — all derived from one ordered list instead of three
    hand-maintained dicts.
    """

    def __init__(self) -> None:
        self._tracks: list[Track] = []
        self._by_uri: dict[str, Track] = {}
        self._by_unique_name: dict[str, Track] = {}

    def append(self, track: Track) -> None:
        self._tracks.append(track)
        # Last-write-wins on URI matches the old behaviour for duplicate tracks.
        self._by_uri[track.uri] = track
        self._by_unique_name[track.unique_name] = track

    def by_index(self, index: int) -> Track | None:
        if 0 <= index < len(self._tracks):
            return self._tracks[index]
        return None

    def by_uri(self, uri: str) -> Track | None:
        return self._by_uri.get(uri)

    def by_unique_name(self, unique_name: str) -> Track | None:
        return self._by_unique_name.get(unique_name)

    def index_of_uri(self, uri: str) -> int | None:
        track = self._by_uri.get(uri)
        if track is None:
            return None
        return track.row_index

    def uris(self) -> list[str]:
        """Ordered list of track URIs (replaces uri_list[playlist])."""
        return [t.uri for t in self._tracks]

    def __len__(self) -> int:
        return len(self._tracks)

    def __iter__(self):
        return iter(self._tracks)
