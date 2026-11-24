"""Đo WER và hệ số thời gian thực (RTF) của một engine STT trên ghi âm có bản gỡ băng làm đáp án (ADR-006 mục 9).

    python -m app.stt.eval <thư mục> [--engine whisper] [--language vi]

Thư mục chứa các cặp `ten.<âm thanh/video>` và `ten.txt` (bản gỡ băng đúng, văn bản thường, không cần mốc giờ).
In từng file và trung bình: WER (thấp hơn tốt hơn), RTF = thời gian xử lý / thời lượng (dưới 1 = nhanh hơn thời gian thực).
Đo qua đúng đường chạy của job (ffmpeg + engine), nên số này là số người dùng thật sẽ gặp.
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

from app.stt import service

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".mp4", ".mkv", ".webm", ".mov"}


def normalize(text: str) -> list[str]:
    """NFC, chữ thường, bỏ dấu câu; tách theo khoảng trắng. Giữ dấu thanh tiếng Việt (sai dấu là sai từ)."""
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--engine", default=None)
    ap.add_argument("--language", default=None)
    args = ap.parse_args(argv)

    pairs = [(p, p.with_suffix(".txt")) for p in sorted(args.folder.iterdir()) if p.suffix.lower() in AUDIO_EXT]
    pairs = [(a, t) for a, t in pairs if t.exists()]
    if not pairs:
        print("Không có cặp file âm thanh + .txt nào trong thư mục.", file=sys.stderr)
        return 1
    wers, rtfs = [], []
    for audio_path, ref_path in pairs:
        res = service.transcribe(str(audio_path), engine=args.engine, language=args.language)
        hyp = " ".join(s.text for s in res.segments)
        w = wer(ref_path.read_text(encoding="utf-8"), hyp)
        rtf = (res.ms / 1000) / res.duration_s if res.duration_s else float("nan")
        wers.append(w)
        rtfs.append(rtf)
        print(f"{audio_path.name}: WER {w:.1%}  RTF {rtf:.2f}  ({res.duration_s:.0f} giây âm thanh, {res.ms / 1000:.0f} giây xử lý)")
    print(f"Trung bình {len(pairs)} file: WER {sum(wers) / len(wers):.1%}  RTF {sum(rtfs) / len(rtfs):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
