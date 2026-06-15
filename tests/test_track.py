"""Unit tests for the Track / PlaylistTracks data model.

These are pure-logic tests with no Spotify or Textual dependency. They protect
the lookup contracts that the player relies on — especially that missing keys
return None rather than raising KeyError, which was the source of several early
crashes before this model replaced the parallel-dict approach.
"""

from tools.track import Track, PlaylistTracks


def make_track(
    uri, name, row_index, artist="Artist", album="Album", duration_ms=200000
):
    return Track(
        uri=uri,
        name=name,
        artist=artist,
        album=album,
        duration_ms=duration_ms,
        row_index=row_index,
    )


def make_collection():
    pt = PlaylistTracks()
    pt.append(make_track("uri:a", "Africa", 0))
    pt.append(make_track("uri:b", "Hold the Line", 1))
    pt.append(make_track("uri:c", "Rosanna", 2))
    return pt


class TestTrack:
    def test_unique_name_combines_name_and_row(self):
        t = make_track("uri:a", "Africa", 0)
        assert t.unique_name == "Africa_0"

    def test_unique_name_uses_row_index_not_position(self):
        t = make_track("uri:x", "Song", 5)
        assert t.unique_name == "Song_5"


class TestPlaylistTracksLookups:
    def test_by_uri_returns_matching_track(self):
        pt = make_collection()
        assert pt.by_uri("uri:b").name == "Hold the Line"

    def test_by_index_returns_track_at_position(self):
        pt = make_collection()
        assert pt.by_index(2).name == "Rosanna"

    def test_by_unique_name_matches_table_row_key(self):
        # The table builds row keys as f"{name}_{row_index}"; by_unique_name
        # must resolve those for track_selected to work.
        pt = make_collection()
        assert pt.by_unique_name("Africa_0").uri == "uri:a"

    def test_index_of_uri_returns_row_index(self):
        pt = make_collection()
        assert pt.index_of_uri("uri:c") == 2

    def test_uris_preserves_order(self):
        pt = make_collection()
        assert pt.uris() == ["uri:a", "uri:b", "uri:c"]

    def test_len_reflects_appends(self):
        pt = make_collection()
        assert len(pt) == 3

    def test_iter_yields_tracks_in_order(self):
        pt = make_collection()
        names = [t.name for t in pt]
        assert names == ["Africa", "Hold the Line", "Rosanna"]


class TestPlaylistTracksMissingKeys:
    """The whole point of the model: missing lookups return None, never raise."""

    def test_by_uri_missing_returns_none(self):
        pt = make_collection()
        assert pt.by_uri("uri:nope") is None

    def test_by_index_out_of_range_returns_none(self):
        pt = make_collection()
        assert pt.by_index(99) is None

    def test_by_index_negative_returns_none(self):
        pt = make_collection()
        assert pt.by_index(-1) is None

    def test_by_unique_name_missing_returns_none(self):
        pt = make_collection()
        assert pt.by_unique_name("Ghost_7") is None

    def test_index_of_uri_missing_returns_none(self):
        pt = make_collection()
        assert pt.index_of_uri("uri:nope") is None

    def test_empty_collection_lookups_return_none(self):
        pt = PlaylistTracks()
        assert pt.by_uri("anything") is None
        assert pt.by_index(0) is None
        assert pt.index_of_uri("x") is None
        assert pt.uris() == []
        assert len(pt) == 0


class TestPlaylistTracksDuplicates:
    def test_duplicate_uri_last_write_wins(self):
        # Matches the old dict behaviour for a track that appears twice.
        pt = PlaylistTracks()
        pt.append(make_track("uri:dup", "First", 0))
        pt.append(make_track("uri:dup", "Second", 3))
        assert pt.by_uri("uri:dup").row_index == 3
        # but both remain in order for positional/ordering operations
        assert pt.uris() == ["uri:dup", "uri:dup"]
        assert len(pt) == 2
