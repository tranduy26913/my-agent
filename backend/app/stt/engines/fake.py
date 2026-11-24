"""Engine giả cho test: không cần model hay GPU. KHÔNG đăng ký trong ENGINES mặc định."""

from collections.abc import Iterator

from app.stt.engines.base import Segment


class FakeEngine:
    name = "fake"

    def __init__(self, segments: list[Segment] | None = None, is_available: bool = True):
        self.segments = segments if segments is not None else [
            Segment(0.0, 4.0, "Xin chào mọi người."),
            Segment(4.0, 9.5, "Hôm nay ta bàn về tiến độ dự án."),
            Segment(9.5, 12.0, "Cảm ơn."),
        ]
        self.is_available = is_available
        self.calls = 0
        self.languages: list[str | None] = []
        self.paths: list[str] = []

    def available(self) -> bool:
        return self.is_available

    def transcribe(self, audio_path: str, *, language: str | None) -> Iterator[Segment]:
        self.calls += 1
        self.languages.append(language)
        self.paths.append(audio_path)
        yield from self.segments
