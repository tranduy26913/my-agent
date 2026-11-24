"""Engine PaddleOCR-VL-1.6 (PaddlePaddle, Apache-2.0, 0,9B) qua server nhỏ trong `ocr-engine/` (ADR-005).

Backend CHỈ là client HTTP: model chạy ở container riêng (`ocr-engine/run-paddle.sh`), địa chỉ ở
OCR_PADDLEVL_URL. Chưa cấu hình hoặc server tắt thì `available()` là False -> API báo 503, hoặc rơi về
OCR_FALLBACK_ENGINE.

Backend lo bố cục (cắt trang ở khung bảng, `app/ocr/layout.py`) rồi gọi server một lần cho mỗi vùng;
server chỉ đọc một ảnh.
"""

import io

import httpx

from app.config import settings
from app.ocr.layout import is_blank, split_regions

_HEALTH_TIMEOUT = 2.0


class PaddleOcrVlEngine:
    name = "paddleocr_vl"

    def __init__(self, client: httpx.Client | None = None):
        self._client = client  # test truyền httpx.Client(transport=MockTransport) vào đây

    def _base(self) -> str:
        return settings.ocr_paddlevl_url.rstrip("/")

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

    def _read(self, c: httpx.Client, image) -> str:
        buf = io.BytesIO()
        image.convert("RGB").save(buf, "PNG")
        r = c.post(
            f"{self._base()}/ocr",
            files={"file": ("page.png", buf.getvalue(), "image/png")},
            timeout=settings.ocr_paddlevl_timeout,
        )
        r.raise_for_status()
        return str(r.json()["text"]).strip()

    def recognize(self, image, *, layout: str | None = None) -> str:
        # `layout` bị bỏ qua: việc cắt bảng luôn bật (không thấy bảng thì đọc nguyên trang), xem layout.py.
        regions = split_regions(image, tables=settings.ocr_paddlevl_split_tables)
        parts: list[str] = []
        with self._http() as c:
            for region in regions:
                if len(regions) > 1 and is_blank(region.image):
                    continue
                text = self._read(c, region.image)
                if text:
                    parts.append(text)
        return "\n".join(parts)
