"""Dịch vụ OCR (ADR-005, bước 2). Dùng engine giả, không cần Tesseract hay Postgres."""

import io
import unicodedata

import pymupdf
import pytest
from PIL import Image

from app.config import settings
from app.ocr import service
from app.ocr.engines import ENGINES
from app.ocr.engines.fake import FakeEngine
from app.ocr.errors import (
    BadPageSpec,
    EngineFailed,
    EngineUnavailable,
    FileTooLarge,
    TooManyPages,
    UnknownEngine,
    UnsupportedFile,
)

LONG_TEXT = "Thong bao dieu chinh gio lam viec mua dong cua Cong ty A, ap dung tu thang 12."


def png_bytes(size=(80, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, "PNG")
    return buf.getvalue()


def pdf_text_layer(pages: int = 1) -> bytes:
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"{LONG_TEXT} Trang {i + 1}")
    return doc.tobytes()


def pdf_scan_only(pages: int = 1) -> bytes:
    """PDF chỉ có ảnh, không có lớp text (giống SVT-TB-018)."""
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page().insert_image(pymupdf.Rect(50, 50, 300, 200), stream=png_bytes((250, 150)))
    return doc.tobytes()


@pytest.fixture
def fake(monkeypatch):
    eng = FakeEngine()
    monkeypatch.setitem(ENGINES, "fake", lambda: eng)
    monkeypatch.setattr(settings, "ocr_engine", "fake")
    return eng


def test_pdf_co_lop_text_khong_goi_engine(fake):
    r = service.recognize(pdf_text_layer())
    assert [p.source for p in r.pages] == ["text-layer"]
    assert "Thong bao" in r.pages[0].text
    assert r.ocr_pages == 0 and fake.calls == 0


def test_pdf_co_lop_text_doc_duoc_ke_ca_khi_engine_tat(fake):
    fake.is_available = False
    r = service.recognize(pdf_text_layer())
    assert r.pages[0].source == "text-layer"


def test_pdf_scan_chay_ocr(fake):
    r = service.recognize(pdf_scan_only(2))
    assert [p.source for p in r.pages] == ["ocr", "ocr"]
    assert r.ocr_pages == 2 and fake.calls == 2
    assert r.kind == "pdf" and r.engine == "fake"


def test_anh_png_chay_ocr(fake):
    r = service.recognize(png_bytes())
    assert r.kind == "image"
    assert r.pages[0].text == "VAN BAN GIA" and r.pages[0].source == "ocr"


def test_chon_trang(fake):
    r = service.recognize(pdf_text_layer(3), pages="2")
    assert [p.page for p in r.pages] == [2]
    assert "Trang 2" in r.pages[0].text


@pytest.mark.parametrize("spec", ["0", "4", "abc", "3-2", "1,x", "1-9"])
def test_chon_trang_sai(fake, spec):
    with pytest.raises(BadPageSpec):
        service.recognize(pdf_text_layer(3), pages=spec)


def test_parse_pages():
    assert service.parse_pages(None, 3) == [1, 2, 3]
    assert service.parse_pages("1,3-4", 5) == [1, 3, 4]
    assert service.parse_pages("2,2,1", 5) == [1, 2]


def test_qua_nhieu_trang(fake, monkeypatch):
    monkeypatch.setattr(settings, "ocr_max_pages", 2)
    with pytest.raises(TooManyPages):
        service.recognize(pdf_text_layer(3))
    assert len(service.recognize(pdf_text_layer(3), pages="1-2").pages) == 2  # chia nhỏ thì được


def test_file_gia_mao_bi_tu_choi(fake):
    with pytest.raises(UnsupportedFile):
        service.recognize(b"MZ\x90\x00" + b"\x00" * 100)  # mã thực thi đội lốt .png
    with pytest.raises(UnsupportedFile):
        service.recognize(b"")


def test_pdf_hong_va_anh_hong(fake):
    with pytest.raises(UnsupportedFile):
        service.recognize(b"%PDF-1.4 rac rac rac")
    with pytest.raises(UnsupportedFile):
        service.recognize(png_bytes()[:30])  # đúng chữ ký PNG nhưng bị cắt cụt


def test_file_qua_lon(fake, monkeypatch):
    monkeypatch.setattr(settings, "ocr_max_mb", 0.0001)  # ~104 byte
    with pytest.raises(FileTooLarge):
        service.recognize(png_bytes((200, 200)))


def test_anh_qua_nhieu_diem_anh(fake, monkeypatch):
    monkeypatch.setattr(settings, "ocr_max_pixels", 100)
    with pytest.raises(FileTooLarge):
        service.recognize(png_bytes((80, 40)))


def test_engine_sai_ten_va_engine_chua_san_sang(fake):
    with pytest.raises(UnknownEngine):
        service.recognize(png_bytes(), engine="khong-co")
    fake.is_available = False
    with pytest.raises(EngineUnavailable):
        service.recognize(png_bytes())


def test_engine_loi_giua_chung_khong_lo_chi_tiet(fake):
    def boom(_image):
        raise RuntimeError("duong dan noi bo C:\\secret")

    fake.recognize = boom
    with pytest.raises(EngineFailed) as ei:
        service.recognize(png_bytes())
    assert "secret" not in str(ei.value)


def test_chuan_hoa_unicode_nfc(fake):
    fake.text = unicodedata.normalize("NFD", "Điều 3: Giờ làm việc")  # dạng tổ hợp
    text = service.recognize(png_bytes()).pages[0].text
    assert text == unicodedata.normalize("NFC", "Điều 3: Giờ làm việc")
    assert unicodedata.is_normalized("NFC", text)
