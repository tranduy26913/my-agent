"""Nghiệp vụ OCR duy nhất (ADR-005). REST gọi vào đây; sau này MCP cũng gọi vào đây, không viết lại.

Luồng: kiểm tra đầu vào -> mở tài liệu -> chọn trang -> mỗi trang: lấy text nếu có lớp text, ngược lại OCR.
Engine chỉ được tạo/kiểm tra khi gặp trang CẦN OCR -> PDF có lớp text vẫn đọc được dù engine đang tắt.
"""

import logging
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

from app.config import settings
from app.ocr.engines import get_engine, resolve_name
from app.ocr.errors import BadPageSpec, EngineFailed, EngineUnavailable, FileTooLarge, OcrError, TooManyPages
from app.ocr.pdf import open_document

log = logging.getLogger("ocr")

_gates: dict[str, threading.Semaphore] = {}
_gates_lock = threading.Lock()


def _gate(engine_name: str) -> threading.Semaphore:
    """Giới hạn số lượt OCR song song cho mỗi engine (engine dùng GPU dễ hết bộ nhớ nếu chạy dồn)."""
    with _gates_lock:
        if engine_name not in _gates:
            _gates[engine_name] = threading.Semaphore(max(1, settings.ocr_max_concurrency))
        return _gates[engine_name]


@dataclass
class PageResult:
    page: int
    text: str
    source: str  # "text-layer" | "ocr"
    ms: int


@dataclass
class RecognizeResult:
    engine: str
    kind: str  # "pdf" | "image"
    pages: list[PageResult] = field(default_factory=list)
    ms: int = 0

    @property
    def ocr_pages(self) -> int:
        return sum(1 for p in self.pages if p.source == "ocr")


def parse_pages(spec: str | None, total: int) -> list[int]:
    """'1,3-5' -> [1, 3, 4, 5]. Rỗng/None = tất cả trang. Số trang tính từ 1."""
    if not spec or not spec.strip():
        return list(range(1, total + 1))
    chosen: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        try:
            if "-" in part:
                a, b = (int(x) for x in part.split("-", 1))
            else:
                a = b = int(part)
        except ValueError as e:
            raise BadPageSpec(f"Danh sách trang không hợp lệ: {spec!r} (ví dụ đúng: 1,3-5)") from e
        if a < 1 or b < a or b > total:
            raise BadPageSpec(f"Trang {part!r} ngoài phạm vi 1..{total}")
        chosen.update(range(a, b + 1))
    return sorted(chosen)


def _pick_engine(name: str):
    """Engine để dùng: `name`, hoặc OCR_FALLBACK_ENGINE khi `name` là engine mặc định mà chưa sẵn sàng.

    Chỉ dự phòng cho engine MẶC ĐỊNH: chọn đích danh engine khác mà nó tắt thì vẫn nhận 503.
    Trả (tên engine thực sự dùng, engine) để kết quả ghi đúng engine đã đọc.
    """
    try:
        return name, get_engine(name)
    except EngineUnavailable:
        fallback = settings.ocr_fallback_engine
        if name != settings.ocr_engine or not fallback or fallback == name:
            raise
        log.warning("Engine %s chưa sẵn sàng, rơi về %s", name, fallback)
        return fallback, get_engine(fallback)


def _nfc(text: str) -> str:
    """Chuẩn hóa Unicode NFC: 'Điều' dựng sẵn và tổ hợp là một, nếu không so khớp từ khóa hỏng âm thầm."""
    return unicodedata.normalize("NFC", text).strip()


def recognize(
    data: bytes,
    *,
    engine: str | None = None,
    pages: str | None = None,
    max_pages: int | None = None,
    max_mb: float | None = None,
    layout: str | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> RecognizeResult:
    """Mặc định áp giới hạn của request đồng bộ; job bất đồng bộ truyền `max_pages`/`max_mb` lớn hơn.

    `progress(đã_xong, tổng)` được gọi trước trang đầu (đã_xong=0) và sau mỗi trang. Nếu nó ném ngoại lệ
    (vd job bị xóa giữa chừng) thì việc OCR dừng ngay và ngoại lệ đó được truyền ra ngoài.
    """
    max_pages = settings.ocr_max_pages if max_pages is None else max_pages
    max_mb = settings.ocr_max_mb if max_mb is None else max_mb
    if len(data) > max_mb * 1024 * 1024:
        raise FileTooLarge(f"File vượt giới hạn {max_mb:g} MB")
    engine_name = resolve_name(engine)  # tên sai -> 400 ngay, trước khi mở file

    t0 = time.perf_counter()
    doc = open_document(data)
    try:
        selected = parse_pages(pages, doc.page_count)
        if len(selected) > max_pages:
            raise TooManyPages(
                f"Chọn {len(selected)} trang, tối đa {max_pages} trang mỗi lần; "
                "dùng tham số pages (vd 1-5) để chia nhỏ"
            )
        result = RecognizeResult(engine=engine_name, kind=doc.kind)
        if progress:
            progress(0, len(selected))
        ocr_engine = None
        for no in selected:
            t = time.perf_counter()
            content = doc.read(no)
            if content.text is not None:
                text, source = content.text, "text-layer"
            else:
                if ocr_engine is None:
                    engine_name, ocr_engine = _pick_engine(engine_name)
                    result.engine = engine_name  # có thể đã rơi về engine dự phòng
                try:
                    with _gate(engine_name):
                        text = ocr_engine.recognize(content.image, **({"layout": layout} if layout else {}))
                except OcrError:
                    raise
                except Exception as e:  # noqa: BLE001 - lỗi bên trong engine, không lộ chi tiết ra ngoài
                    log.exception("OCR engine %s lỗi ở trang %d", engine_name, no)
                    raise EngineFailed(f"Engine {engine_name!r} lỗi khi đọc trang {no}") from e
                source = "ocr"
            result.pages.append(PageResult(no, _nfc(text), source, int((time.perf_counter() - t) * 1000)))
            if progress:
                progress(len(result.pages), len(selected))
    finally:
        doc.close()
    result.ms = int((time.perf_counter() - t0) * 1000)
    return result

