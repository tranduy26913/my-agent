"""Mở tài liệu (ảnh / PDF) thành từng trang: trang có lớp text thì lấy text, trang scan thì trả ảnh để OCR.

Logic phát hiện lớp text trùng với app/rag/ingest.py (MIN_TEXT_PER_PAGE, render 250 DPI). Trùng lặp là
CHỦ ĐÍCH và tạm thời: ingest.py đang được session khác sửa; khi xong sẽ đổi ingest.py sang dùng module này.
"""

import io
from dataclasses import dataclass

from app.config import settings
from app.ocr.errors import FileTooLarge, UnsupportedFile

MIN_TEXT_PER_PAGE = 40  # ít hơn ngưỡng này -> coi là trang scan, cần OCR

# Chữ ký đầu file (magic bytes). Không tin đuôi file hay Content-Type do client gửi.
_IMAGE_SIGNATURES = (
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"\xff\xd8\xff",  # JPEG
    b"II*\x00",  # TIFF little-endian
    b"MM\x00*",  # TIFF big-endian
    b"BM",  # BMP
)


def sniff_kind(data: bytes) -> str:
    """'pdf' | 'image', hoặc UnsupportedFile."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(_IMAGE_SIGNATURES):
        return "image"
    raise UnsupportedFile("Chỉ nhận ảnh (png, jpg, tif, bmp) và PDF; nội dung file không khớp định dạng nào")


@dataclass
class PageContent:
    text: str | None = None  # có giá trị = lấy từ lớp text, không cần OCR
    image: object | None = None  # PIL.Image cần OCR khi text là None


def _check_pixels(width: int, height: int) -> None:
    if width * height > settings.ocr_max_pixels:
        raise FileTooLarge(
            f"Ảnh/trang quá lớn ({width}x{height} điểm ảnh), giới hạn {settings.ocr_max_pixels:,}"
        )


class PdfDocument:
    kind = "pdf"

    def __init__(self, data: bytes):
        import pymupdf  # PyMuPDF

        try:
            self._doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception as e:  # noqa: BLE001 - PDF hỏng
            raise UnsupportedFile("Không đọc được file PDF (có thể bị hỏng)") from e
        if self._doc.needs_pass:
            self._doc.close()
            raise UnsupportedFile("PDF có mật khẩu, chưa hỗ trợ")
        self.page_count = self._doc.page_count

    def read(self, page_no: int) -> PageContent:
        page = self._doc[page_no - 1]
        text = page.get_text()
        if len(text.strip()) >= MIN_TEXT_PER_PAGE:
            return PageContent(text=text)
        dpi = settings.ocr_render_dpi
        _check_pixels(int(page.rect.width / 72 * dpi), int(page.rect.height / 72 * dpi))
        from PIL import Image

        pix = page.get_pixmap(dpi=dpi)
        return PageContent(image=Image.frombytes("RGB", (pix.width, pix.height), pix.samples))

    def close(self) -> None:
        self._doc.close()


class ImageDocument:
    """Ảnh đơn, hoặc TIFF nhiều khung (mỗi khung là một trang)."""

    kind = "image"

    def __init__(self, data: bytes):
        from PIL import Image

        try:
            self._img = Image.open(io.BytesIO(data))
            self._img.load()
        except Exception as e:  # noqa: BLE001 - ảnh hỏng / decompression bomb
            raise UnsupportedFile("Không đọc được file ảnh (có thể bị hỏng hoặc quá lớn)") from e
        _check_pixels(*self._img.size)
        self.page_count = getattr(self._img, "n_frames", 1)

    def read(self, page_no: int) -> PageContent:
        self._img.seek(page_no - 1)
        return PageContent(image=self._img.convert("RGB"))

    def close(self) -> None:
        self._img.close()


def open_document(data: bytes):
    kind = sniff_kind(data)
    return PdfDocument(data) if kind == "pdf" else ImageDocument(data)
