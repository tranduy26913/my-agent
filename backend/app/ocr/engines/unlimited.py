"""Engine Unlimited-OCR-2 (baidu, MIT) chạy qua SGLang, gọi bằng API tương thích OpenAI (ADR-005 mục 2, 6).

Backend CHỈ là client HTTP mỏng: model chạy ở một tiến trình/container riêng (thư mục `ocr-engine/`), địa chỉ
cấu hình bằng OCR_SGLANG_URL. Chưa cấu hình hoặc server tắt thì `available()` là False -> API báo 503 như
Tesseract thiếu chương trình, không làm hỏng engine khác.

CHƯA kiểm với server thật (xem docs/adr/ADR-005, "Việc còn lại"). Những chỗ dựa vào model card và có thể phải
chỉnh sau lần chạy đầu: câu lệnh (OCR_SGLANG_PROMPT), thứ tự các phần trong `content`, các token đặc biệt
cần bóc khỏi đầu ra (`_clean`), và `custom_logit_processor` (chuỗi SGLang sinh, đặt ở
OCR_SGLANG_LOGIT_PROCESSOR).
"""

import base64
import io
import re

import httpx

from app.config import settings

# Token đặc biệt chèn vào đầu ra khi skip_special_tokens=false: <PAGE>, <｜end▁of▁sentence｜>, <|im_end|>...
_SPECIAL = re.compile(r"<PAGE>|<[｜|][^<>]{1,40}[｜|]>")
_HEALTH_TIMEOUT = 2.0


def _clean(text: str) -> str:
    return _SPECIAL.sub("", text).strip()


class UnlimitedEngine:
    name = "unlimited"

    def __init__(self, client: httpx.Client | None = None):
        self._client = client  # test truyền httpx.Client(transport=MockTransport) vào đây

    # -- tiện ích ----------------------------------------------------------------------------------

    def _base(self) -> str:
        return settings.ocr_sglang_url.rstrip("/")

    def _http(self) -> httpx.Client:
        return self._client or httpx.Client()

    def _headers(self) -> dict[str, str]:
        key = settings.ocr_sglang_api_key
        return {"Authorization": f"Bearer {key}"} if key else {}

    # -- OcrEngine ---------------------------------------------------------------------------------

    def available(self) -> bool:
        if not self._base():
            return False
        try:
            with self._http() as c:
                r = c.get(f"{self._base()}/v1/models", headers=self._headers(), timeout=_HEALTH_TIMEOUT)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def _payload(self, image) -> dict:
        buf = io.BytesIO()
        image.convert("RGB").save(buf, "PNG")
        url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        payload: dict = {
            "model": settings.ocr_sglang_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": url}},
                        {"type": "text", "text": settings.ocr_sglang_prompt},
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": settings.ocr_sglang_max_tokens,
            "stream": False,
            "skip_special_tokens": False,
            "images_config": {"crop_mode": settings.ocr_sglang_crop_mode},
        }
        if settings.ocr_sglang_logit_processor:
            # Chống lặp n-gram (model OCR dễ lặp vô hạn ở bảng/ô trống). Chuỗi do SGLang sinh một lần.
            payload["custom_logit_processor"] = settings.ocr_sglang_logit_processor
            payload["custom_params"] = {
                "ngram_size": 35,
                "window_size": 128,  # một trang; bản nhiều trang dùng 1024
                "page_token_id": 128827,
                "eos_token_id": 1,
                "max_page_tokens": 20000,
            }
        return payload

    def recognize(self, image, *, layout: str | None = None) -> str:
        # layout="rows" bị bỏ qua: model tự nhận bố cục bảng, không có chế độ ép từng dòng như --psm 6.
        with self._http() as c:
            r = c.post(
                f"{self._base()}/v1/chat/completions",
                json=self._payload(image),
                headers=self._headers(),
                timeout=settings.ocr_sglang_timeout,
            )
        r.raise_for_status()
        choice = r.json()["choices"][0]
        return _clean(choice["message"]["content"] or "")
