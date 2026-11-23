"""Tiền xử lý ảnh cho Tesseract. Thuần numpy/Pillow, không cần cài Tesseract."""

import numpy as np
from PIL import Image, ImageDraw

from app.config import settings
from app.ocr.engines import tesseract as tess_mod
from app.ocr.preprocess import otsu_threshold, preprocess, remove_table_lines


def table_image(noise: bool = False) -> Image.Image:
    """Trang giả lập: lưới bảng 3x2 + hai khối 'chữ' (hình chữ nhật đặc nhỏ) nằm trong ô."""
    img = Image.new("RGB", (1000, 600), "white")
    d = ImageDraw.Draw(img)
    for y in (100, 250, 400):
        d.line([(50, y), (950, y)], fill="black", width=3)  # đường ngang dài 900
    for x in (50, 500, 950):
        d.line([(x, 100), (x, 400)], fill="black", width=3)  # đường dọc dài 300
    d.rectangle([80, 140, 110, 170], fill="black")  # "chữ" 30x30
    d.rectangle([530, 140, 560, 170], fill="black")
    if noise:
        rng = np.random.default_rng(0)
        px = img.load()
        for _ in range(800):
            px[int(rng.integers(0, 1000)), int(rng.integers(0, 600))] = (60, 60, 60)  # hạt đơn lẻ
    return img


def ink(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L")) < 128


def test_otsu_tach_hai_dinh():
    gray = np.array([20] * 100 + [230] * 100, dtype=np.uint8)
    assert 20 <= otsu_threshold(gray) < 230


def test_otsu_anh_trang_toan_bo_khong_loi():
    otsu_threshold(np.full((10, 10), 255, dtype=np.uint8))


def test_xoa_duong_ke_nhung_giu_chu():
    out = ink(preprocess(table_image()))
    # Cho phép vài điểm sót ở mép chỗ đường dọc gặp đường ngang (PIL vẽ nét dày hơi phình ở đầu mút).
    assert out[95:106, 60:940].sum() < 10  # đường ngang (900 điểm/hàng x 3 hàng) biến mất
    assert out[110:390, 45:56].sum() < 10  # đường dọc biến mất
    assert out[140:171, 80:111].sum() > 800  # khối "chữ" 30x30 còn gần nguyên
    assert out[140:171, 530:561].sum() > 800


def test_khu_nhieu_hat():
    img = table_image(noise=True)
    assert ink(img).sum() > ink(table_image()).sum() + 300  # tiền đề: ảnh có nhiễu thật
    out = ink(preprocess(img))
    assert out.sum() < 2000  # chỉ còn hai khối chữ (~1800), hạt đơn lẻ đã bị lọc


def test_anh_trang_van_la_anh_trang():
    out = ink(preprocess(Image.new("RGB", (300, 200), "white")))
    assert out.sum() == 0


def test_remove_table_lines_dung_bang_boolean_va_khong_sua_dau_vao():
    white = ~ink(table_image())
    before = white.copy()
    remove_table_lines(white, min_len=60)
    assert (white == before).all()


def test_engine_tesseract_ton_trong_co_ocr_preprocess(monkeypatch):
    seen = []

    class FakePt:
        @staticmethod
        def image_to_string(image, lang, config=""):
            seen.append(image)
            return "x"

    monkeypatch.setattr(tess_mod, "_pytesseract", lambda: FakePt)
    src = table_image()

    monkeypatch.setattr(settings, "ocr_preprocess", True)
    tess_mod.TesseractEngine().recognize(src)
    assert seen[-1] is not src and seen[-1].mode == "L"

    monkeypatch.setattr(settings, "ocr_preprocess", False)
    tess_mod.TesseractEngine().recognize(src)
    assert seen[-1] is src
