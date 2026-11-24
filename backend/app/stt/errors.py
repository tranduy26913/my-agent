"""Lỗi nghiệp vụ của dịch vụ STT (ADR-006). Mỗi lỗi mang sẵn mã HTTP để router chỉ việc dịch ra response."""


class SttError(Exception):
    status_code = 400


class UnsupportedAudio(SttError):
    """Không phải âm thanh/video đọc được (xác định theo NỘI DUNG, không tin đuôi file)."""

    status_code = 400


class UnknownEngine(SttError):
    status_code = 400


class FileTooLarge(SttError):
    status_code = 413


class AudioTooLong(SttError):
    status_code = 422


class JobNotFound(SttError):
    """Không có job, hết hạn, hoặc không phải của người gọi (cố ý gộp chung để không lộ job có tồn tại)."""

    status_code = 404


class TooManyJobs(SttError):
    status_code = 429


class EngineUnavailable(SttError):
    status_code = 503


class EngineFailed(SttError):
    status_code = 502
