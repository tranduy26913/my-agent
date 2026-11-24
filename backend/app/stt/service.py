"""Nghiệp vụ STT duy nhất (ADR-006). REST gọi vào đây; sau này MCP cũng gọi vào đây, không viết lại.

Luồng: tệp tạm -> ffmpeg đổi sang WAV 16 kHz mono (kiểm thời lượng) -> engine chép từng đoạn -> chuẩn hóa.
Hàm này KHÔNG xóa `src_path` (người gọi sở hữu); WAV trung gian nằm trong thư mục tạm riêng và luôn bị xóa.
"""

import logging
import tempfile
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.stt import audio, files
from app.stt.engines import get_engine, resolve_name
from app.stt.errors import EngineFailed, SttError

log = logging.getLogger("stt")

_gates: dict[str, threading.Semaphore] = {}
_gates_lock = threading.Lock()


def _gate(engine_name: str) -> threading.Semaphore:
    """Giới hạn số lượt giải mã song song cho mỗi engine (GPU/CPU dễ nghẽn nếu chạy dồn)."""
    with _gates_lock:
        if engine_name not in _gates:
            _gates[engine_name] = threading.Semaphore(max(1, settings.stt_max_concurrency))
        return _gates[engine_name]


@dataclass
class SegmentResult:
    start: float
    end: float
    text: str


@dataclass
class TranscribeResult:
    engine: str
    duration_s: float
    segments: list[SegmentResult] = field(default_factory=list)
    ms: int = 0


def _nfc(text: str) -> str:
    """Chuẩn hóa Unicode NFC: 'Điều' dựng sẵn và tổ hợp là một, nếu không so khớp từ khóa hỏng âm thầm."""
    return unicodedata.normalize("NFC", text).strip()


def transcribe(
    src_path: str,
    *,
    engine: str | None = None,
    language: str | None = None,
    max_minutes: float | None = None,
    progress: Callable[[float, float], None] | None = None,
) -> TranscribeResult:
    """`progress(giây_đã_xong, tổng_giây)` được gọi một lần với đã_xong=0 và sau mỗi đoạn.

    Nếu nó ném ngoại lệ (vd job bị xóa giữa chừng) thì việc chép dừng ngay và ngoại lệ đó được truyền ra.
    """
    engine_name = resolve_name(engine)  # tên sai -> 400 ngay, trước khi đụng tới file
    lang = language if language is not None else (settings.stt_language or None)
    limit_s = (settings.stt_max_minutes if max_minutes is None else max_minutes) * 60

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="wav-", dir=files.tmp_dir()) as work:
        wav = str(Path(work) / "audio.wav")
        total = audio.convert(src_path, wav, max_seconds=limit_s)
        stt = get_engine(engine_name)  # chưa sẵn sàng -> 503 (kiểm sau khi biết file hợp lệ)
        result = TranscribeResult(engine=engine_name, duration_s=round(total, 2))
        if progress:
            progress(0.0, total)
        segments = iter(stt.transcribe(wav, language=lang))
        try:
            with _gate(engine_name):
                while True:
                    try:
                        seg = next(segments)
                    except StopIteration:
                        break
                    except SttError:
                        raise
                    except Exception as e:  # noqa: BLE001 - lỗi bên trong engine, không lộ chi tiết ra ngoài
                        log.exception("STT engine %s lỗi", engine_name)
                        raise EngineFailed(f"Engine {engine_name!r} lỗi khi chép lời") from e
                    text = _nfc(seg.text)
                    start = min(max(seg.start, 0.0), total)
                    end = min(max(seg.end, start), total)
                    if text:
                        result.segments.append(SegmentResult(round(start, 2), round(end, 2), text))
                    if progress:  # ngoài try ở trên: ngoại lệ hủy job đi thẳng ra, không bị coi là lỗi engine
                        progress(end, total)
        finally:
            close = getattr(segments, "close", None)
            if close:
                close()  # dừng engine ngay nếu job bị hủy giữa chừng
    result.ms = int((time.perf_counter() - t0) * 1000)
    return result

