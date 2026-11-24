"""GET /api/me: người đang đăng nhập, như backend biết (docs/06 giai đoạn 5, docs/07).

Portal gọi endpoint này bằng access token Zitadel của người dùng để dựng menu (vai trò admin thì hiện nhóm
Quản trị). Vai trò và phòng ban lấy từ bảng employees theo email trong token, KHÔNG lấy từ token. Việc ẩn menu
chỉ để gọn giao diện; các API phía sau vẫn tự kiểm quyền.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_principal
from app.rag.acl import Principal

router = APIRouter(tags=["me"])


class MeOut(BaseModel):
    email: str
    name: str
    department: str
    roles: list[str]


@router.get("", response_model=MeOut)
def me(p: Principal = Depends(get_principal)) -> MeOut:
    # get_principal đã trả 401 (token sai), 403 (chưa có trong danh bạ / đã nghỉ việc) trước khi vào đây.
    return MeOut(email=p.email, name=p.full_name or p.email, department=p.department, roles=sorted(p.roles))
