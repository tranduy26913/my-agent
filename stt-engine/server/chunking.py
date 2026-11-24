"""Logic thuần (không model, không I/O) để cắt âm thanh thành các đoạn lời nói và gán người nói. Có test: test_chunking.py.

Đơn vị là GIÂY. Đoạn = (start, end). Lượt nói của một người = (start, end, speaker_id) từ bộ phân tách người nói.
"""

MIN_PIECE_S = 0.6  # đoạn con ngắn hơn mức này (do đổi người nói) bị gộp vào đoạn kề, tránh vụn vặt khó chép


def merge_short(chunks: list[tuple[float, float]], *, max_s: float, max_gap_s: float = 0.8, min_s: float = 1.0) -> list[tuple[float, float]]:
    """Gộp các đoạn ngắn kề nhau (khoảng lặng nhỏ) miễn tổng không vượt max_s: đoạn quá ngắn chép kém vì thiếu ngữ cảnh."""
    out: list[tuple[float, float]] = []
    for s, e in chunks:
        if out:
            ps, pe = out[-1]
            if s - pe <= max_gap_s and e - ps <= max_s and ((pe - ps) < min_s or (e - s) < min_s):
                out[-1] = (ps, e)
                continue
        out.append((s, e))
    return out


def assign_speakers(
    chunks: list[tuple[float, float]], turns: list[tuple[float, float, int]]
) -> list[tuple[float, float, int | None]]:
    """Gán người nói cho từng đoạn; đoạn trùm qua chỗ đổi người nói được cắt tại chỗ đổi.

    Không có lượt nói nào phủ lên đoạn -> người nói None (đoạn vẫn được chép).
    """
    out: list[tuple[float, float, int | None]] = []
    for s, e in chunks:
        # Phần giao của đoạn với từng lượt nói, theo thứ tự thời gian.
        pieces: list[tuple[float, float, int]] = []
        for ts, te, spk in sorted(turns):
            lo, hi = max(s, ts), min(e, te)
            if hi > lo:
                if pieces and pieces[-1][2] == spk:  # cùng người nói liền nhau: nối lại
                    pieces[-1] = (pieces[-1][0], hi, spk)
                else:
                    pieces.append((lo, hi, spk))
        if not pieces:
            out.append((s, e, None))
            continue
        # Gộp đoạn con quá ngắn vào đoạn trước (hoặc sau nếu là đoạn đầu).
        merged: list[tuple[float, float, int]] = []
        for p in pieces:
            if merged and (p[1] - p[0]) < MIN_PIECE_S:
                merged[-1] = (merged[-1][0], p[1], merged[-1][2])
            else:
                merged.append(p)
        if len(merged) > 1 and (merged[0][1] - merged[0][0]) < MIN_PIECE_S:
            merged[1] = (merged[0][0], merged[1][1], merged[1][2])
            merged.pop(0)
        # Mép ngoài lấy theo đoạn gốc (turn có thể hẹp hơn tiếng nói thật); mép giữa giữ chỗ đổi người nói.
        merged[0] = (s, merged[0][1], merged[0][2])
        merged[-1] = (merged[-1][0], e, merged[-1][2])
        out.extend(merged)
    return out


def label(index: int) -> str:
    """0 -> A, 1 -> B, ..., 25 -> Z, 26 -> A2 ..."""
    letter = chr(ord("A") + index % 26)
    return letter if index < 26 else f"{letter}{index // 26 + 1}"
