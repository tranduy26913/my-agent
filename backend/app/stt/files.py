"""Tệp tạm của STT (ADR-006 mục 4): ghi tạm xuống đĩa, xóa ngay khi xong. Không bao giờ lưu lâu dài."""

import contextlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

from app.config import settings
from app.stt.errors import FileTooLarge

CHUNK = 1024 * 1024


def tmp_dir() -> Path:
    """Thư mục tạm của STT (tạo nếu chưa có). Mặc định nằm trong thư mục tạm của hệ điều hành."""
    d = Path(settings.stt_tmp_dir) if settings.stt_tmp_dir else Path(tempfile.gettempdir()) / "svt-stt"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_stream(stream: BinaryIO, limit_bytes: int) -> tuple[str, int]:
    """Chép luồng upload vào một tệp tạm theo từng khối (không nạp cả file vào RAM).

    Vượt `limit_bytes` thì dừng, xóa tệp và ném FileTooLarge. Trả (đường dẫn, số byte).
    """
    fd, path = tempfile.mkstemp(prefix="up-", suffix=".bin", dir=tmp_dir())
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := stream.read(CHUNK):
                size += len(chunk)
                if size > limit_bytes:
                    raise FileTooLarge(f"File vượt giới hạn {limit_bytes / 1024 / 1024:g} MB")
                out.write(chunk)
    except BaseException:
        remove(path)
        raise
    return path, size


def remove(path: str | None) -> None:
    """Xóa tệp tạm, bỏ qua nếu không còn."""
    if path:
        with contextlib.suppress(OSError):
            os.unlink(path)


def purge_all() -> int:
    """Dọn sạch thư mục tạm (lúc khởi động: job dở đã bị đánh dấu failed nên không cần tệp nữa)."""
    n = 0
    for p in tmp_dir().iterdir():
        try:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            n += 1
        except OSError:
            pass
    return n
