"""Dependency dùng chung cho mọi router (/api/ocr, sau này /api/kb, /api/me).

Router chỉ import từ đây, không import thẳng `app.security`. Nhờ vậy khi chuyển sang Zitadel
(docs/06-ke-hoach-zitadel.md, ADR-004) chỉ sửa MỘT file này:

    hiện tại : get_current_user = JWT tự phát của backend (bảng users, vai trò admin/manager/staff)
    sau này  : get_principal    = kiểm token Zitadel (OIDC), tra Principal theo email trong bảng employees

Hai hàm trả hai kiểu khác nhau (UserInfo và Principal), nên router nào cần danh tính phải khai báo rõ
đang dùng cái nào; khi chuyển Zitadel thì đổi dòng import ở router, không đổi logic nghiệp vụ.
"""

from app.db import get_db
from app.security import UserInfo, get_current_user, require_roles

__all__ = ["UserInfo", "get_current_user", "get_db", "require_roles"]
