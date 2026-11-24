"""Chạy: python -m pytest test_chunking.py (cần pytest) hoặc python test_chunking.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "server"))
from chunking import assign_speakers, label, merge_short  # noqa: E402


def test_merge_short_joins_tiny_neighbours_but_respects_max():
    assert merge_short([(0, 0.5), (0.8, 3.0)], max_s=15) == [(0, 3.0)]
    assert merge_short([(0, 6), (6.2, 12)], max_s=15) == [(0, 6), (6.2, 12)]  # cả hai đủ dài: giữ nguyên
    assert merge_short([(0, 0.5), (0.8, 20.0)], max_s=15) == [(0, 0.5), (0.8, 20.0)]  # gộp sẽ vượt max


def test_single_speaker_and_boundaries_follow_chunk():
    assert assign_speakers([(1.0, 5.0)], [(0.0, 10.0, 0)]) == [(1.0, 5.0, 0)]


def test_chunk_spanning_speaker_change_is_split_at_change():
    got = assign_speakers([(0.0, 10.0)], [(0.0, 4.0, 0), (4.0, 10.0, 1)])
    assert got == [(0.0, 4.0, 0), (4.0, 10.0, 1)]


def test_tiny_overlap_does_not_create_a_fragment():
    got = assign_speakers([(0.0, 10.0)], [(0.0, 9.8, 0), (9.8, 10.0, 1)])
    assert got == [(0.0, 10.0, 0)]


def test_chunk_without_any_turn_has_no_speaker():
    assert assign_speakers([(0.0, 3.0)], []) == [(0.0, 3.0, None)]


def test_labels():
    assert [label(i) for i in (0, 1, 25, 26)] == ["A", "B", "Z", "A2"]


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("ok")
