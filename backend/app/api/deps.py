"""Dependency dùng chung cho mọi router (/api/ocr, /api/kb, /api/admin, /api/me).

Router chỉ import từ đây, không import thẳng `app.auth`. Điểm nối xác thực là MỘT file này.

Chỉ còn một đường: Bearer access token RS256 của Zitadel -> email đã xác minh -> Principal tra trong bảng
employees (app/auth/oidc.py). Vai trò lấy từ employees.roles, không lấy từ token. Đã gỡ JWT HS256 tự phát,
bảng users, X-Portal-Token và X-KB-Token (docs/06 giai đoạn 6).
"""

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.oidc import (
    OidcError,
    OidcVerifier,
    get_principal,
    get_verifier,
    http_error,
    principal_for,
    require_role,
    unauthorized,
)
from app.db import get_db
from app.security import UserInfo

__all__ = [
    "Actor",
    "UserInfo",
    "get_admin",
    "get_asker_email",
    "get_db",
    "get_kb_admin",
    "get_ocr_user",
    "get_principal",
    "require_role",
]


@dataclass(frozen=True)
class Actor:
    """Người thực hiện một thao tác quản trị, để ghi audit và `documents.uploaded_by`: email đã xác minh."""

    email: str


def _bearer(authorization: str) -> str | None:
    scheme, _, token = authorization.partition(" ")
    return token.strip() or None if scheme.lower() == "bearer" else None


def get_kb_admin(
    authorization: str = Header(default=""),
    verifier: OidcVerifier | None = Depends(get_verifier),
    db: Session = Depends(get_db),
) -> Actor:
    """Admin của /api/kb và /api/admin: token Zitadel của nhân viên có vai trò `admin` trong employees."""
    token = _bearer(authorization)
    if token is None:
        raise unauthorized("Thiếu access token")
    if verifier is None:
        # Chưa cấu hình OIDC thì mọi token đều không hợp lệ: 401, không lộ trạng thái cấu hình.
        raise unauthorized("Token không hợp lệ")
    try:
        identity = verifier.identity(token)
    except OidcError as e:
        raise http_error(e) from e
    p = principal_for(db, identity)
    if "admin" not in p.roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cần vai trò: admin")
    return Actor(p.email)


def get_ocr_user(p=Depends(get_principal)) -> UserInfo:
    """Người dùng của /api/ocr: nhân viên đang hoạt động đăng nhập bằng token Zitadel.

    Đổi Principal sang UserInfo để service OCR (jobs, record_usage) giữ nguyên chữ ký. `id` là employees.id
    (không phải users.id); `username` là email; role chỉ phân biệt admin (xem job người khác, có audit) với
    người thường."""
    return UserInfo(
        id=p.employee_id,
        username=p.email,
        role="admin" if "admin" in p.roles else "user",
        department=p.department,
        full_name=p.full_name,
    )


# Cổng admin của /api/admin/*: cùng quy tắc với /api/kb.
get_admin = get_kb_admin


def get_asker_email(
    authorization: str = Header(default=""),
    verifier: OidcVerifier | None = Depends(get_verifier),
) -> str:
    """Email đã xác minh của người đang hỏi, cho endpoint dành cho MỌI nhân viên (vd /api/kb/ask).
    Vai trò và phòng ban không lấy từ client mà tra trong bảng employees."""
    token = _bearer(authorization)
    if token is None:
        raise unauthorized("Thiếu access token")
    if verifier is None:
        raise unauthorized("Token không hợp lệ")
    try:
        return verifier.identity(token).email
    except OidcError as e:
        raise http_error(e) from e
