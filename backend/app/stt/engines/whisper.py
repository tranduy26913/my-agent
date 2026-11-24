"""Engine faster-whisper qua server nhỏ trong `stt-engine/` (ADR-006 mục 8).

Backend CHỈ là client HTTP: model chạy ở tiến trình riêng (`stt-engine/run.ps1`), địa chỉ ở STT_WHISPER_URL. Chưa cấu hình
hoặc server tắt thì `available()` là False -> API báo 503.

Hợp đồng: POST /transcribe (multipart WAV) trả NDJSON, mỗi dòng một đoạn, dòng cuối {"done": true}. Thiếu dòng cuối nghĩa là
server bị ngắt giữa chừng: ném lỗi thay vì trả văn bản cụt như thể đã xong.
"""

import json
from collections.abc import Iterator

import httpx

from app.config import settings
from app.stt.engines.base import Segment

_HEALTH_TIMEOUT = 2.0


class WhisperEngine:
    name = "whisper"

    def __init__(self, client: httpx.Client | None = None):
        self._client = client  # test truyền httpx.Client(transport=MockTransport) vào đây

    def _base(self) -> str:
        return settings.stt_whisper_url.rstrip("/")

    def _http(self) -> httpx.Client:
        return self._client or httpx.Client()

    def available(self) -> bool:
        if not self._base():
            return False
        try:
            with self._http() as c:
                r = c.get(f"{self._base()}/health", timeout=_HEALTH_TIMEOUT)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except (httpx.HTTPError, ValueError):
            return False

    def transcribe(self, audio_path: str, *, language: str | None) -> Iterator[Segment]:
        # read = thời gian tối đa giữa hai dòng (lần đầu gồm cả nạp model); không giới hạn tổng thời gian của cuộc họp.
        timeout = httpx.Timeout(connect=5.0, read=settings.stt_whisper_timeout, write=300.0, pool=5.0)
        params = {"language": language} if language else {}
        with self._http() as c, open(audio_path, "rb") as f:
            with c.stream(
                "POST", f"{self._base()}/transcribe", params=params, files={"file": ("audio.wav", f, "audio/wav")}, timeout=timeout
            ) as r:
                if r.status_code != 200:
                    r.read()
                    raise RuntimeError(f"stt-engine trả {r.status_code}")
                finished = False
                for line in r.iter_lines():
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    if msg.get("done"):
                        finished = True
                        break
                    spk = msg.get("speaker")
                    yield Segment(float(msg["start"]), float(msg["end"]), str(msg["text"]), str(spk) if spk else None)
                if not finished:
                    raise RuntimeError("stt-engine ngắt giữa chừng (không có dòng kết thúc)")
