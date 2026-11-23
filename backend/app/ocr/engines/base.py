"""Hợp đồng chung cho mọi engine OCR (cùng mẫu với app/llm/base.py).

Service chỉ phụ thuộc interface này -> thêm engine mới (vd Unlimited-OCR qua SGLang) không sửa service/router.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PIL.Image import Image


class OcrEngine(Protocol):
    name: str

    def available(self) -> bool:
        """Engine dùng được ngay bây giờ không (binary/dịch vụ có đó, gói ngôn ngữ đủ)."""
        ...

    def recognize(self, image: "Image", *, layout: str | None = None) -> str:
        """Đọc chữ trong MỘT ảnh trang, trả văn bản thô.

        layout: gợi ý bố cục. None = tự nhận (mặc định, tốt cho văn bản chạy dài).
        "rows" = biểu mẫu/bảng: giữ mỗi dòng bảng trên MỘT dòng văn bản. Engine không hỗ trợ thì bỏ qua gợi ý.
        """
        ...
