"""Engine mặc định: Tesseract (CPU, miễn phí, chạy được trên máy demo).

Cần cài chương trình Tesseract + gói ngôn ngữ trong settings.ocr_lang (mặc định `vie+eng`).
Thiếu một trong hai thì `available()` là False -> API báo 503 rõ ràng thay vì lỗi lạ giữa chừng.
"""

import shutil
from pathlib import Path

from app.config import settings

_WINDOWS_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def find_tesseract() -> str | None:
    """settings.tesseract_cmd -> PATH -> thư mục cài mặc định trên Windows (mới cài thì PATH chưa có)."""
    if settings.tesseract_cmd:
        return settings.tesseract_cmd
    return shutil.which("tesseract") or (str(_WINDOWS_DEFAULT) if _WINDOWS_DEFAULT.exists() else None)


def _pytesseract():
    import pytesseract

    cmd = find_tesseract()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract


class TesseractEngine:
    name = "tesseract"

    def available(self) -> bool:
        try:
            installed = set(_pytesseract().get_languages())
        except Exception:  # noqa: BLE001 - thiếu binary / không chạy được = chưa sẵn sàng
            return False
        return set(settings.ocr_lang.split("+")) <= installed

    def recognize(self, image, *, layout: str | None = None) -> str:
        if settings.ocr_preprocess:
            from app.ocr.preprocess import preprocess

            image = preprocess(image)
        # "rows" -> --psm 6 (một khối đồng nhất): mỗi dòng bảng nằm trên một dòng văn bản,
        # kể cả cột HĐ ở rìa phải.
        # Mặc định (psm 3) tách cột rìa phải thành khối riêng đặt cuối trang nên mất liên hệ với dòng của nó.
        config = "--psm 6" if layout == "rows" else ""
        return _pytesseract().image_to_string(image, lang=settings.ocr_lang, config=config)
