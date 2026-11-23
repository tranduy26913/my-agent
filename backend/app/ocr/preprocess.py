"""Tiền xử lý ảnh cho Tesseract: khử nhiễu hạt -> nhị phân hóa (Otsu) -> xóa đường kẻ bảng.

Vì sao cần: đo trên data/scan (2026-11-23) cho thấy Tesseract đọc văn bản thuần tốt (CER ~4%) nhưng đọc HỎNG
mọi ô số trong bảng có đường kẻ (0/8 số tiền thành tiền). Xóa đường kẻ đưa lên 9/9; khử nhiễu hoặc đổi chế độ
phân trang (--psm) riêng lẻ không giúp gì. Xem data/eval/reports/*-ocr*.md.

Chỉ dùng numpy + Pillow (không thêm OpenCV). Dành riêng cho Tesseract: engine hiểu bố cục (vd Unlimited-OCR)
cần ảnh gốc, nên hàm này được gọi trong engine chứ không trong service.
"""

import numpy as np
from PIL import Image, ImageFilter


def otsu_threshold(gray: np.ndarray) -> int:
    """Ngưỡng Otsu: chọn ngưỡng làm phương sai giữa hai lớp (mực / nền) lớn nhất."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    w0 = np.cumsum(hist)  # số điểm tối hơn hoặc bằng ngưỡng
    w1 = total - w0
    m = np.cumsum(hist * np.arange(256))
    with np.errstate(divide="ignore", invalid="ignore"):
        between = np.nan_to_num((m[-1] * w0 - m * total) ** 2 / (w0 * w1))
    return int(np.argmax(between))


def _erase_long_runs(ink: np.ndarray, out: np.ndarray, min_len: int) -> None:
    """Xóa (ghi False vào `out`) mọi đoạn mực liên tục dài >= min_len theo từng HÀNG của `ink`."""
    for y in np.flatnonzero(ink.sum(axis=1) >= min_len):
        padded = np.concatenate(([0], ink[y].astype(np.int8), [0]))
        edges = np.diff(padded)
        for start, end in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True):
            if end - start >= min_len:
                out[y, start:end] = False


def remove_table_lines(white: np.ndarray, min_len: int) -> np.ndarray:
    """Xóa đường kẻ ngang và dọc. `white` True = nền. Chữ không có đoạn mực thẳng liên tục dài như vậy."""
    ink = ~white
    out = ink.copy()
    _erase_long_runs(ink, out, min_len)  # đường ngang
    _erase_long_runs(ink.T, out.T, min_len)  # đường dọc (.T là view nên ghi thẳng vào out)
    return ~out


def preprocess(image: Image.Image, *, median: int = 3, line_frac: float = 0.04) -> Image.Image:
    """Ảnh gốc -> ảnh xám nhị phân đã bỏ nhiễu hạt và đường kẻ bảng.

    median: cỡ bộ lọc trung vị để khử nhiễu hạt (0 = tắt).
    line_frac: đoạn mực thẳng dài hơn tỉ lệ này của bề rộng ảnh bị coi là đường kẻ. Tính theo bề rộng
    (không phải số điểm ảnh cố định) để không phụ thuộc DPI: 4% của trang A4 ~ 8 mm.
    """
    gray = image.convert("L")
    if median:
        gray = gray.filter(ImageFilter.MedianFilter(median))
    arr = np.asarray(gray)
    white = arr > otsu_threshold(arr)
    white = remove_table_lines(white, min_len=max(20, int(image.width * line_frac)))
    return Image.fromarray((white * 255).astype(np.uint8))
