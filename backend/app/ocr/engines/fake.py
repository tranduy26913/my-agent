"""Engine giả cho test: không cần Tesseract hay GPU. KHÔNG đăng ký trong ENGINES mặc định."""


class FakeEngine:
    name = "fake"

    def __init__(self, text: str = "VAN BAN GIA", is_available: bool = True):
        self.text = text
        self.is_available = is_available
        self.calls = 0
        self.layouts: list[str | None] = []

    def available(self) -> bool:
        return self.is_available

    def recognize(self, image, *, layout: str | None = None) -> str:
        self.calls += 1
        self.layouts.append(layout)
        return self.text
