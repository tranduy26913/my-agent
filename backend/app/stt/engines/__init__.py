from collections.abc import Callable

from app.config import settings
from app.stt.engines.base import SttEngine
from app.stt.errors import EngineUnavailable, UnknownEngine

# Tên engine -> hàm tạo. Thêm engine mới = thêm một dòng ở đây (test đăng ký engine giả vào đúng dict này).
# Giai đoạn 1 (ADR-006): chưa có engine thật nào; server và client engine làm ở giai đoạn 2.
ENGINES: dict[str, Callable[[], SttEngine]] = {}


def resolve_name(name: str | None) -> str:
    """Tên engine hợp lệ (mặc định lấy từ cấu hình). Chỉ kiểm tên, chưa kiểm engine có sẵn sàng không."""
    key = name or settings.stt_engine
    if key not in ENGINES:
        have = ", ".join(sorted(ENGINES)) or "chưa có engine nào được cài"
        raise UnknownEngine(f"Engine không tồn tại: {key!r}. Có: {have}")
    return key


def get_engine(name: str | None = None) -> SttEngine:
    """Lấy engine đã sẵn sàng; chưa sẵn sàng -> EngineUnavailable (HTTP 503)."""
    key = resolve_name(name)
    engine = ENGINES[key]()
    if not engine.available():
        raise EngineUnavailable(f"Engine {key!r} chưa sẵn sàng trên máy chủ (dịch vụ hoặc model chưa chạy)")
    return engine


def list_engines() -> list[dict]:
    return [{"name": n, "available": f().available()} for n, f in sorted(ENGINES.items())]
