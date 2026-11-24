from collections.abc import Callable

from app.config import settings
from app.ocr.engines.base import OcrEngine
from app.ocr.engines.paddleocr_vl import PaddleOcrVlEngine
from app.ocr.engines.tesseract import TesseractEngine
from app.ocr.engines.unlimited import UnlimitedEngine
from app.ocr.errors import EngineUnavailable, UnknownEngine

# Tên engine -> hàm tạo. Thêm engine mới = thêm một dòng ở đây (test đăng ký engine giả vào đúng dict này).
ENGINES: dict[str, Callable[[], OcrEngine]] = {
    "tesseract": TesseractEngine,
    "paddleocr_vl": PaddleOcrVlEngine,
    "unlimited": UnlimitedEngine,
}


def resolve_name(name: str | None) -> str:
    """Tên engine hợp lệ (mặc định lấy từ cấu hình). Chỉ kiểm tên, chưa kiểm engine có sẵn sàng không."""
    key = name or settings.ocr_engine
    if key not in ENGINES:
        raise UnknownEngine(f"Engine không tồn tại: {key!r}. Có: {', '.join(sorted(ENGINES))}")
    return key


def get_engine(name: str | None = None) -> OcrEngine:
    """Lấy engine đã sẵn sàng; chưa sẵn sàng -> EngineUnavailable (HTTP 503)."""
    key = resolve_name(name)
    engine = ENGINES[key]()
    if not engine.available():
        raise EngineUnavailable(
            f"Engine {key!r} chưa sẵn sàng trên máy chủ (thiếu chương trình/gói ngôn ngữ/dịch vụ)"
        )
    return engine


def list_engines() -> list[dict]:
    return [{"name": n, "available": f().available()} for n, f in sorted(ENGINES.items())]
