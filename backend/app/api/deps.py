"""Dependency dùng chung cho mọi router (/api/ocr, /api/kb, sau này /api/me).

Router chỉ import từ đây, không import thẳng `app.security`. Nhờ vậy khi chuyển sang Zitadel
(docs/06-ke-hoach-zitadel.md, ADR-004) chỉ sửa MỘT file này:

    hiện tại : get_current_user = JWT tự phát của backend (bảng users, vai trò admin/manager/staff)
               get_asker_email  = BFF của portal truyền X-User-Email kèm bí mật dùng chung
    sau này  : get_principal    = kiểm token Zitadel (OIDC), tra Principal theo email trong bảng employees

Hai hàm trả hai kiểu khác nhau (UserInfo và Principal), nên router nào cần danh tính phải khai báo rõ
đang dùng cái nào; khi chuyển Zitadel thì đổi dòng import ở router, không đổi logic nghiệp vụ.
"""

import hmac

from fastapi import Header, HTTPException, status

from app.config import settings
from app.db import get_db
from app.security import UserInfo, get_current_user, require_roles

__all__ = ["UserInfo", "get_asker_email", "get_current_user", "get_db", "require_roles"]


def get_asker_email(
    x_portal_token: str = Header(default="", alias="X-Portal-Token"),
    x_user_email: str = Header(default="", alias="X-User-Email"),
) -> str:
    """Email của người đang hỏi, cho endpoint dành cho MỌI nhân viên (không chỉ admin), vd /api/kb/ask.

    Cùng cách tin cậy với knowledge-mcp: header email CHỈ được tin khi X-Portal-Token đúng, tức là request
    đến từ BFF của portal (nơi đã biết ai đang đăng nhập). Vai trò và phòng ban không lấy từ client mà tra
    trong bảng employees. Chưa cấu hình token thì từ chối hết (fail closed).
    TẠM: Zitadel sẽ thay bằng email trong token OIDC.
    """
    expected = settings.portal_bff_token.encode()
    # So sánh bytes: compare_digest với str chỉ nhận ASCII, header chứa ký tự lạ sẽ thành lỗi 500 thay vì 401.
    if not expected or not hmac.compare_digest(x_portal_token.encode(), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Thiếu hoặc sai X-Portal-Token")
    email = x_user_email.strip()
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Không xác định được người dùng (X-User-Email)")
    return email
