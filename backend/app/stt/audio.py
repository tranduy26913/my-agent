"""Chuẩn bị âm thanh cho engine: mọi đầu vào (MP3, M4A, WAV, video họp...) -> WAV 16 kHz mono (ADR-006).

Dùng ffmpeg. Loại file xác định bằng việc ffmpeg có đọc ra tiếng hay không, không tin đuôi hay Content-Type.
"""

import logging
import re
import shutil
import subprocess
import wave

from app.config import settings
from app.stt.errors import AudioTooLong, EngineUnavailable, UnsupportedAudio

log = logging.getLogger("stt")

SAMPLE_RATE = 16_000
MIN_SECONDS = 0.5
_WINDOWS_DEFAULT = r"C:\ffmpeg\bin\ffmpeg.exe"
CONVERT_TIMEOUT_S = 900  # đổi định dạng một file dài vẫn xong trong vài phút; quá mốc này coi như treo


def find_ffmpeg() -> str | None:
    """FFMPEG_CMD, rồi PATH, rồi thư mục cài mặc định trên Windows. None = máy chủ chưa cài."""
    for cand in (settings.ffmpeg_cmd, shutil.which("ffmpeg"), _WINDOWS_DEFAULT):
        if cand and shutil.which(cand):
            return cand
    return None


def require_ffmpeg() -> str:
    path = find_ffmpeg()
    if path is None:
        raise EngineUnavailable("Máy chủ chưa cài ffmpeg nên chưa xử lý được ghi âm")
    return path


_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
PROBE_TIMEOUT_S = 60
_NOT_AUDIO = "Không đọc được file này như âm thanh hoặc video có tiếng"


def probe(src_path: str, *, max_seconds: float) -> float | None:
    """Kiểm nhanh TRƯỚC khi nhận job: ffmpeg giải mã thử 1 giây đầu.

    Trả thời lượng khai báo (None nếu không biết).

    Để rác (đuôi .mp3 nhưng là mã thực thi, file rỗng, video không có tiếng) bị từ chối ngay bằng 400 thay vì
    thành một job thất bại. Thời lượng khai báo vượt giới hạn thì từ chối ngay bằng 422; thời lượng thật vẫn
    được kiểm lại sau khi đổi sang WAV (`convert`) vì metadata có thể sai.
    """
    ffmpeg = require_ffmpeg()
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-i", src_path, "-vn", "-t", "1", "-f", "null", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=PROBE_TIMEOUT_S, check=False)  # noqa: S603
    except subprocess.TimeoutExpired as e:
        raise UnsupportedAudio(_NOT_AUDIO) from e
    err = proc.stderr.decode("utf-8", "replace")
    if proc.returncode != 0 or "Audio:" not in err:
        log.warning("ffmpeg probe lỗi (mã %s): %s", proc.returncode, err[-300:])
        raise UnsupportedAudio(_NOT_AUDIO)
    m = _DURATION.search(err)
    if not m:
        return None
    seconds = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    if seconds > max_seconds:
        raise AudioTooLong(f"Ghi âm dài hơn giới hạn {max_seconds / 60:g} phút; hãy cắt nhỏ file")
    return seconds


def convert(src_path: str, dst_path: str, *, max_seconds: float) -> float:
    """Đổi `src_path` thành WAV 16 kHz mono 16 bit ở `dst_path`. Trả thời lượng (giây).

    Chỉ đọc tối đa `max_seconds + 1` giây (file dài hơn thì bị từ chối sau đó, không đổi cả file khổng lồ).
    Lỗi: UnsupportedAudio (không có tiếng hoặc hỏng), AudioTooLong.
    """
    ffmpeg = require_ffmpeg()
    cmd = [
        ffmpeg, "-hide_banner", "-nostdin", "-v", "error",
        "-i", src_path, "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le",
        "-t", str(max_seconds + 1), "-y", dst_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=CONVERT_TIMEOUT_S, check=False)  # noqa: S603
    except subprocess.TimeoutExpired as e:
        raise UnsupportedAudio("Đổi định dạng âm thanh quá lâu; file có thể hỏng") from e
    if proc.returncode != 0:
        # stderr của ffmpeg có thể chứa đường dẫn tệp tạm: chỉ ghi log, không trả cho người dùng.
        log.warning("ffmpeg lỗi (mã %s): %s", proc.returncode, proc.stderr.decode("utf-8", "replace")[-300:])
        raise UnsupportedAudio(_NOT_AUDIO)

    try:
        with wave.open(dst_path, "rb") as w:
            seconds = w.getnframes() / w.getframerate()
    except (wave.Error, EOFError, OSError) as e:
        raise UnsupportedAudio(_NOT_AUDIO) from e
    if seconds < MIN_SECONDS:
        raise UnsupportedAudio("File không có tiếng (hoặc quá ngắn)")
    if seconds > max_seconds:
        raise AudioTooLong(f"Ghi âm dài hơn giới hạn {max_seconds / 60:g} phút; hãy cắt nhỏ file")
    return seconds
