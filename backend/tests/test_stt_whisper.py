"""Engine whisper (client HTTP của stt-engine/, ADR-006 giai đoạn 2): hợp đồng NDJSON, không cần model hay mạng."""

import httpx
import pytest

from app.config import settings
from app.stt.engines import ENGINES, list_engines
from app.stt.engines.whisper import WhisperEngine


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def wav(tmp_path):
    p = tmp_path / "a.wav"
    p.write_bytes(b"RIFFxxxx")
    return str(p)


@pytest.fixture(autouse=True)
def url(monkeypatch):
    monkeypatch.setattr(settings, "stt_whisper_url", "http://stt.test")


def ndjson(*lines: str) -> httpx.Response:
    return httpx.Response(200, content="\n".join(lines) + "\n", headers={"content-type": "application/x-ndjson"})


def test_registered_and_off_without_url(monkeypatch):
    assert ENGINES["whisper"] is WhisperEngine
    monkeypatch.setattr(settings, "stt_whisper_url", "")
    assert WhisperEngine().available() is False
    assert {"name": "whisper", "available": False} in list_engines()


def test_available_follows_health():
    ok = WhisperEngine(client(lambda r: httpx.Response(200, json={"status": "ok"})))
    assert ok.available() is True
    down = WhisperEngine(client(lambda r: (_ for _ in ()).throw(httpx.ConnectError("x"))))
    assert down.available() is False
    bad = WhisperEngine(client(lambda r: httpx.Response(500)))
    assert bad.available() is False


def test_streams_segments_and_sends_language(wav):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return ndjson(
            '{"start": 0.0, "end": 3.5, "text": "Xin chào"}',
            '{"start": 3.5, "end": 6.0, "text": "tiến độ dự án"}',
            '{"done": true, "duration": 6.0, "ms": 100}',
        )

    segs = list(WhisperEngine(client(handler)).transcribe(wav, language="vi"))
    assert [(s.start, s.end, s.text) for s in segs] == [(0.0, 3.5, "Xin chào"), (3.5, 6.0, "tiến độ dự án")]
    assert seen["url"] == "http://stt.test/transcribe?language=vi"


def test_no_language_param_when_auto(wav):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return ndjson('{"done": true, "duration": 0, "ms": 1}')

    assert list(WhisperEngine(client(handler)).transcribe(wav, language=None)) == []
    assert seen["url"] == "http://stt.test/transcribe"


def test_truncated_stream_is_an_error_not_a_short_transcript(wav):
    eng = WhisperEngine(client(lambda r: ndjson('{"start": 0, "end": 1, "text": "a"}')))
    it = eng.transcribe(wav, language="vi")
    assert next(it).text == "a"
    with pytest.raises(RuntimeError, match="ngắt giữa chừng"):
        next(it)


def test_http_error_raises(wav):
    with pytest.raises(RuntimeError, match="503"):
        list(WhisperEngine(client(lambda r: httpx.Response(503))).transcribe(wav, language="vi"))


def test_wer():
    from app.stt.eval import wer

    assert wer("Xin chào, mọi người!", "xin chào mọi người") == 0.0
    assert wer("a b c d", "a x c") == 0.5  # 1 thay + 1 thiếu trên 4 từ
    assert wer("chào", "chao") == 1.0  # sai dấu là sai từ
    assert wer("", "") == 0.0


def test_speaker_label_is_passed_through(wav):
    eng = WhisperEngine(
        client(
            lambda r: ndjson(
                '{"start": 0, "end": 2, "text": "a", "speaker": "A"}',
                '{"start": 2, "end": 4, "text": "b", "speaker": null}',
                '{"start": 4, "end": 6, "text": "c"}',
                '{"done": true, "duration": 6, "ms": 1}',
            )
        )
    )
    assert [s.speaker for s in eng.transcribe(wav, language="vi")] == ["A", None, None]
