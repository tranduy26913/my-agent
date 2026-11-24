"""Danh tính người dùng dùng chung cho agent/OCR.

Xác thực nằm ở `app/auth/oidc.py` (token Zitadel); file này chỉ còn kiểu dữ liệu `UserInfo`.
Đã xoá JWT HS256 tự phát và bcrypt (docs/06 giai đoạn 6).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserInfo:
    """Danh tính thuần (không phụ thuộc ORM) -> agent/tool dùng được cả khi test không có DB."""

    id: int
    username: str
    role: str
    department: str
    full_name: str = ""
