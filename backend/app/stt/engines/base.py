"""Hợp đồng chung cho mọi engine STT (cùng mẫu với app/ocr/engines/base.py).

Service chỉ phụ thuộc interface này -> thêm engine mới không sửa service/router.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Segment:
    start: float  # giây tính từ đầu file
    end: float
    text: str
    speaker: str | None = None  # "A", "B", ... theo thứ tự xuất hiện; None = engine không phân biệt người nói


class SttEngine(Protocol):
    name: str

    def available(self) -> bool:
        """Engine dùng được ngay bây giờ không (dịch vụ có đó, model có sẵn)."""
        ...

    def transcribe(self, audio_path: str, *, language: str | None) -> Iterator[Segment]:
        """Chép lời một file WAV 16 kHz mono, trả TỪNG đoạn theo thứ tự thời gian.

        Trả iterator (không phải danh sách) để service tính tiến độ và dừng được giữa chừng khi job bị hủy.
        language: mã ISO ("vi", "en"); None = để engine tự nhận.
        """
        ...
