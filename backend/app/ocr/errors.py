"""Lỗi nghiệp vụ của dịch vụ OCR. Mỗi lỗi mang sẵn mã HTTP để router chỉ việc dịch ra response."""


class OcrError(Exception):
    status_code = 400


class UnsupportedFile(OcrError):
    """Không phải ảnh/PDF hợp lệ (xác định theo NỘI DUNG, không tin đuôi file)."""

    status_code = 400


class UnknownEngine(OcrError):
    status_code = 400


class BadPageSpec(OcrError):
    status_code = 422


class FileTooLarge(OcrError):
    status_code = 413


class TooManyPages(OcrError):
    status_code = 422


class JobNotFound(OcrError):
    """Không có job, hết hạn, hoặc không phải của người gọi (cố ý gộp chung để không lộ job có tồn tại)."""

    status_code = 404


class NoTextFound(OcrError):
    """OCR không đọc ra chữ nào nên không có gì để trích xuất."""

    status_code = 422


class TooManyJobs(OcrError):
    status_code = 429


class EngineUnavailable(OcrError):
    status_code = 503


class EngineFailed(OcrError):
    status_code = 502
