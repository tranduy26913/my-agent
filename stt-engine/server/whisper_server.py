"""Server STT nhỏ cho faster-whisper: một việc duy nhất, chép MỘT file WAV -> các đoạn lời nói (ADR-006 mục 8).

    POST /transcribe  (multipart: file=WAV 16 kHz mono; query: language=vi, diarize=true, speakers=N)
        -> application/x-ndjson, mỗi dòng {"start","end","text","speaker"}, dòng cuối {"done": true, "duration": giây, "ms": ...}
           "speaker" là "A", "B", ... theo thứ tự xuất hiện (null khi không phân tách được người nói)
           (thiếu dòng cuối = bị ngắt giữa chừng; client coi là lỗi, không coi là "xong")
    GET  /health      -> {"status": "ok", "loaded": bool, "model", "device", "compute_type"}

Backend lo ffmpeg, tiến độ, hủy job và quyền; server không biết gì về người dùng. Client ngắt kết nối thì dừng giải mã
ngay ở đoạn kế tiếp. Model nạp lười và NHẢ sau STT_IDLE_SECONDS không có việc (giữ RAM/VRAM cho chat).
"""

import json
import os
import threading
import time

import numpy as np
from faster_whisper.audio import decode_audio
from faster_whisper.vad import VadOptions, get_speech_timestamps
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import StreamingResponse

import diarize
from chunking import assign_speakers, label, merge_short

_LOCAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "phowhisper-small")
# Mặc định: PhoWhisper-small (VinAI, tinh chỉnh tiếng Việt, ~240 MB int8) nếu đã chuyển đổi vào models/; không thì large-v3-turbo.
# STT_MODEL là tên faster-whisper hoặc đường dẫn thư mục model đã chuyển đổi sang CTranslate2.
MODEL = os.environ.get("STT_MODEL") or (_LOCAL if os.path.isdir(_LOCAL) else "large-v3-turbo")
DEVICE = os.environ.get("STT_DEVICE", "cpu")  # cpu | cuda
COMPUTE_TYPE = os.environ.get("STT_COMPUTE_TYPE", "int8")  # cpu: int8; cuda: float16 hoặc int8_float16
CPU_THREADS = int(os.environ.get("STT_CPU_THREADS", "0"))  # 0 = để thư viện chọn
BEAM_SIZE = int(os.environ.get("STT_BEAM_SIZE", "5"))
IDLE_SECONDS = float(os.environ.get("STT_IDLE_SECONDS", "60"))
MAX_CHUNK_S = float(os.environ.get("STT_MAX_CHUNK_S", "20"))  # đoạn chép tối đa (Whisper tối đa 30 giây/lần; ngắn hơn thì ổn định hơn)
MODEL_CACHE = os.environ.get("STT_MODEL_CACHE") or None

app = FastAPI(title="stt-engine")
_lock = threading.Lock()  # một lượt tại một thời điểm và bảo vệ việc nạp/nhả model
_model = None
_last_used = 0.0


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE_TYPE, cpu_threads=CPU_THREADS, download_root=MODEL_CACHE)
    return _model


def _janitor() -> None:
    global _model
    while True:
        time.sleep(5)
        if _lock.acquire(blocking=False):
            try:
                if _model is not None and time.time() - _last_used > IDLE_SECONDS:
                    _model = None
            finally:
                _lock.release()


threading.Thread(target=_janitor, daemon=True).start()


@app.get("/health")
def health():
    return {
        "status": "ok", "loaded": _model is not None, "model": os.path.basename(MODEL), "device": DEVICE,
        "compute_type": COMPUTE_TYPE, "diarization": diarize.available(),
    }


SR = 16000


def _plan(audio: np.ndarray, want_speakers: bool, num_speakers: int | None) -> list[tuple[float, float, int | None]]:
    """Cắt thành các đoạn lời nói theo KHOẢNG LẶNG (không cắt theo mốc 30 giây cố định), rồi gán người nói nếu có thể.

    Cắt theo khoảng lặng thay vì để Whisper tự chia khối 30 giây: PhoWhisper không có mốc thời gian theo câu nên cho cả khối
    một đoạn duy nhất, và câu nằm ngay ranh giới khối dễ bị rơi mất.
    """
    vad = VadOptions(min_silence_duration_ms=400, max_speech_duration_s=MAX_CHUNK_S, speech_pad_ms=150)
    raw = [(t["start"] / SR, t["end"] / SR) for t in get_speech_timestamps(audio, vad, sampling_rate=SR)]
    chunks = merge_short(raw, max_s=MAX_CHUNK_S)
    if want_speakers and diarize.available():
        turns = diarize.diarize(audio, num_speakers=num_speakers)
        return assign_speakers(chunks, turns)
    return [(s, e, None) for s, e in chunks]


@app.post("/transcribe")
def transcribe(
    file: UploadFile = File(...),
    language: str | None = Query(None, max_length=16),
    diarize_speakers: bool = Query(True, alias="diarize"),
    speakers: int | None = Query(None, ge=1, le=20, description="Số người nói nếu biết; bỏ trống = tự đoán"),
):
    def lines():
        global _last_used
        t0 = time.time()
        with _lock:
            try:
                audio = decode_audio(file.file, sampling_rate=SR)
                duration = len(audio) / SR
                model = _load()
                names: dict[int, str] = {}  # speaker_id của clustering -> "A", "B" theo thứ tự xuất hiện
                for start, end, spk in _plan(audio, diarize_speakers, speakers):
                    piece = audio[int(start * SR) : int(end * SR)]
                    if len(piece) < SR * 0.2:
                        continue
                    # without_timestamps: mốc thời gian lấy từ đoạn đã cắt; vad_filter=False vì đã cắt rồi.
                    segs, _ = model.transcribe(
                        piece, language=language or None, beam_size=BEAM_SIZE, without_timestamps=True,
                        vad_filter=False, condition_on_previous_text=False,
                    )
                    text = " ".join(s.text.strip() for s in segs).strip()
                    if not text:
                        continue
                    speaker = None
                    if spk is not None:
                        speaker = names.setdefault(spk, label(len(names)))
                    yield json.dumps(
                        {"start": round(start, 2), "end": round(end, 2), "text": text, "speaker": speaker}, ensure_ascii=False
                    ) + "\n"
                yield json.dumps({"done": True, "duration": round(duration, 2), "ms": int((time.time() - t0) * 1000)}) + "\n"
            finally:
                _last_used = time.time()

    return StreamingResponse(lines(), media_type="application/x-ndjson")
