"""Bố cục tối thiểu cho OCR bằng model thị giác (ADR-005 mục 2): tìm khung bảng rồi cắt trang thành các vùng.

Vì sao cần: PaddleOCR-VL đọc nguyên trang thì bảng ra theo CỘT (cả cột tên khoản, rồi cả cột tiền), còn
phần trích xuất phiếu cần mỗi dòng bảng nằm trên MỘT dòng chữ. Đọc riêng phần bảng đã cắt thì ra đúng
từng dòng.

Chỉ dùng numpy + Pillow. Phát hiện bằng đường kẻ ngang dài; không có đường kẻ (bảng không viền) thì không cắt,
trang được đọc nguyên (hành vi cũ). Chỉ cắt được MỘT bảng (từ đường kẻ đầu đến đường kẻ cuối).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PIL.Image import Image

DARK = 120  # điểm ảnh xám dưới ngưỡng này coi là mực
MIN_LINE_FRAC = 0.6  # đường kẻ ngang dài ít nhất 60% bề rộng trang
TILT_PX = 10  # làm dày dọc ±10 điểm để chịu ảnh nghiêng nhẹ (bản scan thường lệch 0,3-1 độ)
LINE_GAP_PX = 20  # hai hàng cách nhau hơn mức này thuộc hai đường kẻ khác nhau
MIN_TABLE_PX = 60  # bảng thấp hơn mức này là gạch chân hay đường phân cách, không phải bảng
MARGIN_PX = 30


@dataclass(frozen=True)
class Region:
    name: str  # "trang" | "trên" | "bảng" | "dưới"
    image: "Image"


def _window_any(mask: np.ndarray, k: int, axis: int) -> np.ndarray:
    """True nếu có điểm True trong cửa sổ ±k dọc theo `axis` (dùng tổng cộng dồn nên chạy nhanh)."""
    pad = [(k, k) if i == axis else (0, 0) for i in range(2)]
    c = np.cumsum(np.pad(mask.astype(np.int32), pad), axis=axis)
    n = c.shape[axis]
    return (np.take(c, range(2 * k, n), axis=axis) - np.take(c, range(0, n - 2 * k), axis=axis)) > 0


def find_table_box(image: "Image") -> tuple[int, int, int, int] | None:
    """Khung (trái, trên, phải, dưới) của bảng có viền, hoặc None.

    Có viền = ít nhất hai đường kẻ ngang dài tách nhau.
    """
    dark = np.asarray(image.convert("L")) < DARK
    h, w = dark.shape
    thick = _window_any(dark, TILT_PX, 0)
    ys = np.where(thick.sum(1) / w > MIN_LINE_FRAC)[0]
    if ys.size < 2:
        return None
    if not np.any(np.diff(ys) > LINE_GAP_PX):  # chỉ một đường kẻ (gạch chân, đường phân cách)
        return None
    top, bottom = int(ys.min()), int(ys.max())
    if bottom - top < MIN_TABLE_PX:
        return None
    xs = np.where(thick[ys].any(0))[0]
    return (
        max(0, int(xs.min()) - MARGIN_PX),
        max(0, top - MARGIN_PX),
        min(w, int(xs.max()) + MARGIN_PX),
        min(h, bottom + MARGIN_PX),
    )


def is_blank(image: "Image") -> bool:
    """Vùng gần như trắng (dưới 0,2% điểm ảnh là mực): không cần đưa cho model."""
    return float((np.asarray(image.convert("L")) < DARK).mean()) < 0.002


def split_regions(image: "Image", *, tables: bool = True) -> list[Region]:
    """Trang -> các vùng cần đọc, theo thứ tự đọc. Vùng trắng bị bỏ. Không thấy bảng -> một vùng "trang"."""
    box = find_table_box(image) if tables else None
    if box is None:
        return [Region("trang", image)]
    left, top, right, bottom = box
    regions = [
        Region("trên", image.crop((0, 0, image.width, top))),
        Region("bảng", image.crop(box)),
        Region("dưới", image.crop((0, bottom, image.width, image.height))),
    ]
    kept = [r for r in regions if not is_blank(r.image)]
    return kept or [Region("trang", image)]
