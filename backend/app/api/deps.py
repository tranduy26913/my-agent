"""Dependency dùng chung cho mọi router (/api/ocr, /api/kb, sau này /api/me).

Router chỉ import từ đây, không import thẳng `app.security` hay `app.auth`. Điểm nối xác thực là MỘT file này.

Đang chuyển từ JWT tự phát sang Zitadel (docs/06, ADR-004), nên có hai đường chạy SONG SONG:

    Zitadel (đích)  : Bearer access token RS256 -> get_principal / require_role (app/auth/oidc.py), Principal
                      tra theo email trong bảng employees; vai trò lấy từ employees.roles.
    Cũ (tạm)        : get_current_user = JWT HS256 của backend (bảng users); get_asker_email = BFF của portal
                      truyền X-User-Email kèm bí mật dùng chung. Gỡ ở giai đoạn 6 (portal đã đăng nhập thật).

Endpoint nào đã chuyển thì dùng `get_kb_admin` / `get_asker_email` (nhận cả hai đường). OCR đã chuyển hẳn
sang Zitadel (`get_ocr_user`, không còn đường JWT cũ): ocr_jobs.user_id / audit / usage ghi employees.id.
"""

import hmac
from dataclasses import dataclass

import jwt
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
from app.config import settings
from app.db import get_db
from app.security import UserInfo, get_current_user, require_roles

__all__ = [
    "Actor",
    "UserInfo",
    "get_asker_email",
    "get_current_user",
    "get_admin",
    "get_db",
    "get_kb_admin",
    "get_legacy_user",
    "get_ocr_user",
    "get_principal",
    "require_role",
    "require_roles",
]


@dataclass(frozen=True)
class Actor:
    """Người thực hiện một thao tác quản trị, để ghi audit. `id` là users.id (đường cũ); người dùng Zitadel
    chưa có dòng trong bảng users nên `id` = None và audit ghi email vào detail["actor"] (xem kb_service)."""

    id: int | None
    name: str


def _bearer(authorization: str) -> str | None:
    scheme, _, token = authorization.partition(" ")
    return token.strip() or None if scheme.lower() == "bearer" else None


def get_legacy_user(
    authorization: str = Header(default=""), db: Session = Depends(get_db)
) -> UserInfo | None:
    """UserInfo nếu request mang JWT HS256 cũ của backend, ngược lại None (để thử đường Zitadel).
    Chọn đường theo `alg` trong header chưa kiểm chứng là an toàn: mỗi đường tự kiểm chữ ký bằng thuật toán
    và khoá riêng (HS256 + jwt_secret / RS256 + JWKS của Zitadel), không đường nào nhận thuật toán kia."""
    token = _bearer(authorization)
    if token is None:
        return None
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError:
        return None
    return get_current_user(token, db) if alg == "HS256" else None


def get_kb_admin(
    authorization: str = Header(default=""),
    legacy: UserInfo | None = Depends(get_legacy_user),
    verifier: OidcVerifier | None = Depends(get_verifier),
    db: Session = Depends(get_db),
) -> Actor:
    """Admin của /api/kb: JWT cũ có role admin, HOẶC token Zitadel của nhân viên có vai trò `admin`."""
    if legacy is not None:
        if legacy.role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cần quyền: admin")
        return Actor(legacy.id, legacy.username)
    token = _bearer(authorization)
    if token is None:
        raise unauthorized("Thiếu access token")
    if verifier is None:
        # Chưa cấu hình OIDC thì token không phải JWT cũ không thể hợp lệ: 401, không lộ trạng thái cấu hình.
        raise unauthorized("Token không hợp lệ")
    try:
        identity = verifier.identity(token)
    except OidcError as e:
        raise http_error(e) from e
    p = principal_for(db, identity)
    if "admin" not in p.roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cần vai trò: admin")
    return Actor(None, p.email)


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


# Cổng admin của /api/admin/*: cùng quy tắc với /api/kb (JWT cũ role admin hoặc Zitadel + vai trò admin).
get_admin = get_kb_admin


def get_asker_email(
    authorization: str = Header(default=""),
    x_portal_token: str = Header(default="", alias="X-Portal-Token"),
    x_user_email: str = Header(default="", alias="X-User-Email"),
    verifier: OidcVerifier | None = Depends(get_verifier),
) -> str:
    """Email của người đang hỏi, cho endpoint dành cho MỌI nhân viên (không chỉ admin), vd /api/kb/ask.

    Cùng cách tin cậy với knowledge-mcp: header email CHỈ được tin khi X-Portal-Token đúng, tức là request
    đến từ BFF của portal (nơi đã biết ai đang đăng nhập). Vai trò và phòng ban không lấy từ client mà tra
    trong bảng employees. Chưa cấu hình token thì từ chối hết (fail closed).
    Có Bearer token và OIDC đã cấu hình thì dùng email đã xác minh trong token Zitadel (đường đích);
    đường X-Portal-Token là cầu nối TẠM, gỡ ở giai đoạn 6.
    """
    token = _bearer(authorization)
    if token is not None and verifier is not None:
        try:
            return verifier.identity(token).email
        except OidcError as e:
            raise http_error(e) from e
    expected = settings.portal_bff_token.encode()
    # So sánh bytes: compare_digest với str chỉ nhận ASCII, header chứa ký tự lạ sẽ thành lỗi 500 thay vì 401.
    if not expected or not hmac.compare_digest(x_portal_token.encode(), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Thiếu hoặc sai X-Portal-Token")
    email = x_user_email.strip()
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Không xác định được người dùng (X-User-Email)")
    return email
