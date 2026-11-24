"""Cắt trang ở khung bảng (layout.py) và engine paddleocr_vl bằng server giả: không cần GPU hay model."""

import io

import httpx
import pytest
from PIL import Image, ImageDraw

from app.config import settings
from app.ocr import service
from app.ocr.engines import ENGINES, list_engines
from app.ocr.engines.fake import FakeEngine
from app.ocr.engines.paddleocr_vl import PaddleOcrVlEngine
from app.ocr.errors import EngineUnavailable
from app.ocr.layout import find_table_box, is_blank, split_regions
from tests.test_ocr_service import png_bytes

W, H = 1000, 1400


def text_block(d: ImageDraw.ImageDraw, y: int, rows: int = 4):
    """Giả dòng chữ: các vạch ngắn dày vừa đủ (mật độ mực giống chữ thật, không tạo thành đường kẻ dài)."""
    for r in range(rows):
        for x in range(100, 800, 14):
            d.rectangle((x, y + r * 28, x + 8, y + r * 28 + 12), fill=0)


def page(table: bool = True, tilt: float = 0.0, underline_only: bool = False) -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    text_block(d, 80)
    if table:
        for y in (500, 560, 620, 680):
            d.line((80, y, 920, y + int(tilt * 840)), fill=0, width=3)
        for x in (80, 300, 560, 920):
            d.line((x, 500, x + 0, 680), fill=0, width=3)
        for y in (520, 580, 640):
            for x in range(100, 280, 14):
                d.rectangle((x, y, x + 8, y + 12), fill=0)
    if underline_only:
        d.line((100, 400, 900, 400), fill=0, width=3)
    text_block(d, 800)
    return img


def test_tim_thay_khung_bang():
    box = find_table_box(page())
    assert box is not None
    left, top, right, bottom = box
    assert left <= 80 and right >= 920 and top <= 500 and bottom >= 680
    assert top > 400 and bottom < 800  # không lấn sang vùng chữ trên/dưới


def test_chiu_duoc_anh_nghieng_nhe():
    assert find_table_box(page(tilt=0.01)) is not None  # ~8 điểm lệch trên 840 điểm


def test_khong_co_bang_thi_khong_cat():
    assert find_table_box(page(table=False)) is None


def test_mot_duong_ke_khong_phai_bang():
    assert find_table_box(page(table=False, underline_only=True)) is None


def test_split_regions_tren_bang_duoi():
    regions = split_regions(page())
    assert [r.name for r in regions] == ["trên", "bảng", "dưới"]
    assert regions[1].image.height < 300


def test_split_bo_vung_trang_va_giu_mot_vung_khi_khong_co_bang():
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    for y in (500, 560, 620, 680):
        d.line((80, y, 920, y), fill=0, width=3)
    names = [r.name for r in split_regions(img)]
    assert "trên" not in names and "dưới" not in names and "bảng" in names
    assert [r.name for r in split_regions(page(table=False))] == ["trang"]
    assert [r.name for r in split_regions(page(), tables=False)] == ["trang"]
    assert is_blank(Image.new("RGB", (50, 50), "white"))


# ---------- engine ----------


class Server:
    """Server giả: ghi lại các lần gọi /ocr và trả "văn bản vùng N"."""

    def __init__(self, healthy=True):
        self.calls: list[tuple[str, int]] = []
        self.healthy = healthy

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200 if self.healthy else 503, json={"status": "ok"})
        assert request.url.path == "/ocr"
        body = request.content
        start = body.index(b"\x89PNG")
        size = Image.open(io.BytesIO(body[start:])).size
        self.calls.append((request.method, size[1]))
        return httpx.Response(200, json={"text": f" vùng {len(self.calls)} ", "ms": 5})


@pytest.fixture(autouse=True)
def _cfg(monkeypatch):
    monkeypatch.setattr(settings, "ocr_paddlevl_url", "http://ocr.test:10001/")
    monkeypatch.setattr(settings, "ocr_paddlevl_split_tables", True)


def engine(server: Server) -> PaddleOcrVlEngine:
    return PaddleOcrVlEngine(client=httpx.Client(transport=httpx.MockTransport(server)))


def test_engine_dang_ky_va_khong_san_sang_khi_chua_cau_hinh(monkeypatch):
    assert "paddleocr_vl" in ENGINES
    monkeypatch.setattr(settings, "ocr_paddlevl_url", "")
    assert PaddleOcrVlEngine().available() is False
    assert {e["name"]: e["available"] for e in list_engines()}["paddleocr_vl"] is False


def test_available_theo_health():
    assert engine(Server()).available() is True
    assert engine(Server(healthy=False)).available() is False

    def down(request):
        raise httpx.ConnectError("refused")

    assert PaddleOcrVlEngine(client=httpx.Client(transport=httpx.MockTransport(down))).available() is False


def test_trang_co_bang_goi_ba_lan_theo_thu_tu_va_noi_bang_xuong_dong():
    s = Server()
    text = engine(s).recognize(page())
    assert text == "vùng 1\nvùng 2\nvùng 3"
    assert len(s.calls) == 3 and s.calls[1][1] < 300  # lần hai là vùng bảng (thấp)


def test_trang_khong_co_bang_goi_mot_lan():
    s = Server()
    assert engine(s).recognize(page(table=False)) == "vùng 1"
    assert len(s.calls) == 1


def test_tat_cat_bang_thi_doc_nguyen_trang(monkeypatch):
    monkeypatch.setattr(settings, "ocr_paddlevl_split_tables", False)
    s = Server()
    engine(s).recognize(page())
    assert len(s.calls) == 1


def test_loi_server_nem_ngoai_le():
    def boom(request):
        return httpx.Response(500, text="oom")

    with pytest.raises(httpx.HTTPStatusError):
        PaddleOcrVlEngine(client=httpx.Client(transport=httpx.MockTransport(boom))).recognize(page(table=False))


# ---------- dự phòng ----------


@pytest.fixture
def two_engines(monkeypatch):
    default, backup = FakeEngine("MAC DINH", is_available=False), FakeEngine("DU PHONG")
    backup.name = "backup"
    monkeypatch.setitem(ENGINES, "primary", lambda: default)
    monkeypatch.setitem(ENGINES, "backup", lambda: backup)
    monkeypatch.setattr(settings, "ocr_engine", "primary")
    monkeypatch.setattr(settings, "ocr_fallback_engine", "backup")
    return default, backup


def test_roi_ve_engine_du_phong_khi_mac_dinh_tat_va_ghi_dung_ten(two_engines):
    default, backup = two_engines
    res = service.recognize(png_bytes())
    assert res.engine == "backup" and res.pages[0].text == "DU PHONG"
    assert backup.calls == 1 and default.calls == 0


def test_chon_dich_danh_engine_tat_thi_van_503_khong_doi_ngam(two_engines, monkeypatch):
    monkeypatch.setitem(ENGINES, "other", lambda: FakeEngine(is_available=False))
    with pytest.raises(EngineUnavailable):
        service.recognize(png_bytes(), engine="other")


def test_khong_cau_hinh_du_phong_thi_503(two_engines, monkeypatch):
    monkeypatch.setattr(settings, "ocr_fallback_engine", "")
    with pytest.raises(EngineUnavailable):
        service.recognize(png_bytes())


def test_du_phong_cung_tat_thi_503(two_engines, monkeypatch):
    _, backup = two_engines
    backup.is_available = False
    with pytest.raises(EngineUnavailable):
        service.recognize(png_bytes())
