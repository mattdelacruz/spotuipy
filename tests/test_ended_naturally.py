"""Tests for the 'did the track end naturally?' heuristic used by the
PlaybackMonitor to distinguish a track finishing on its own (auto-advance)
from the user skipping mid-track (no auto-advance).

PlaybackMonitor itself imports Textual, so rather than construct the widget we
test the pure decision against the same contract the monitor implements:

    ended_naturally = duration > 0 and progress >= duration - 3000

If PlaybackMonitor._ended_naturally is ever extracted into a standalone
function, point this test at it directly.
"""

NATURAL_END_THRESHOLD_MS = 3000


def ended_naturally(progress_ms: int, duration_ms: int) -> bool:
    """Mirror of PlaybackMonitor._ended_naturally."""
    if duration_ms <= 0:
        return False
    return progress_ms >= duration_ms - NATURAL_END_THRESHOLD_MS


class TestEndedNaturally:
    def test_track_finished_at_exact_end(self):
        assert ended_naturally(200000, 200000) is True

    def test_track_within_threshold_of_end(self):
        # 1.5s before the end — within the 3s window, counts as natural.
        assert ended_naturally(198500, 200000) is True

    def test_track_at_threshold_boundary(self):
        # Exactly 3s before the end — boundary is inclusive.
        assert ended_naturally(197000, 200000) is True

    def test_track_skipped_mid_play(self):
        # Halfway through — a manual skip, not a natural end.
        assert ended_naturally(100000, 200000) is False

    def test_track_skipped_just_outside_threshold(self):
        # 3.001s before the end — just outside the window, treated as a skip.
        assert ended_naturally(196999, 200000) is False

    def test_zero_duration_returns_false(self):
        # Guards against the no-track / uninitialised state.
        assert ended_naturally(0, 0) is False

    def test_negative_duration_returns_false(self):
        assert ended_naturally(5000, -1) is False

    def test_progress_past_duration_counts_as_natural(self):
        # Progress can briefly exceed duration on slow polls; still natural.
        assert ended_naturally(201000, 200000) is True
