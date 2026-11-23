"""Phân quyền tài liệu (ADR-001: docs/adr/ADR-001-phan-quyen-tai-lieu.md).

Quy tắc (theo frontmatter `pham_vi_truy_cap`):
- cong-khai : mọi nhân viên đang làm việc.
- phong-ban : phòng ban ∈ phong_ban_duoc_xem  HOẶC  có vai trò ∈ vai_tro_duoc_xem.
- han-che   : phòng ban ∈ phong_ban_duoc_xem  VÀ   có vai trò ∈ vai_tro_duoc_xem
              (danh sách nào rỗng thì bỏ qua điều kiện đó).
- Nhân viên đã nghỉ việc: không xem được gì.
- KHÔNG có ngoại lệ cho `admin`: quản trị hệ thống không đồng nghĩa được đọc quy chế lương (least privilege).

Có HAI bản cài đặt cùng một quy tắc:
1. `acl_sql()`  -> mệnh đề WHERE, lọc ngay trong truy vấn (tài liệu không được phép không bao giờ ra khỏi DB).
2. `can_read()` -> hàm Python thuần, dùng trong eval để kiểm tra chéo bản SQL. Hai bản viết độc lập
   nên nếu một bản sai, eval sẽ báo "rò quyền" thay vì cả hai cùng sai lặng lẽ.
"""

from dataclasses import dataclass, field

from sqlalchemy import and_, false, or_


@dataclass(frozen=True)
class Principal:
    """Người đang hỏi. Lấy từ bảng employees theo email, KHÔNG lấy vai trò do client tự khai."""

    email: str
    department: str
    roles: frozenset[str] = field(default_factory=frozenset)
    active: bool = True
    employee_id: int | None = None
    full_name: str = ""
    code: str = ""  # mã nhân viên (NV017): phạm vi own/team của ADR-003 so với code / manager_code


def load_principal(db, email: str) -> Principal | None:
    from sqlalchemy import func, select

    from app.models import Employee

    stmt = select(Employee).where(func.lower(Employee.email) == email.strip().lower())
    emp = db.execute(stmt).scalar_one_or_none()
    if emp is None:
        return None
    return Principal(
        email=emp.email,
        department=emp.department,
        roles=frozenset(emp.roles or []),
        active=emp.status == "dang-lam",
        employee_id=emp.id,
        full_name=emp.full_name,
        code=emp.code,
    )


def acl_sql(p: Principal):
    from app.models import Document

    if not p.active:
        return false()
    roles = list(p.roles)
    in_dept = Document.allowed_departments.any(p.department)
    has_role = Document.allowed_roles.overlap(roles) if roles else false()
    no_dept_list = Document.allowed_departments == []
    no_role_list = Document.allowed_roles == []
    return or_(
        Document.visibility == "cong-khai",
        and_(Document.visibility == "phong-ban", or_(in_dept, has_role)),
        and_(
            Document.visibility == "han-che",
            or_(in_dept, no_dept_list),
            or_(has_role, no_role_list),
            # cả hai danh sách đều rỗng ở tài liệu hạn chế = cấu hình lỗi -> không ai xem (fail closed)
            ~and_(no_dept_list, no_role_list),
        ),
    )


def can_read(p: Principal, visibility: str, departments: list[str], roles: list[str]) -> bool:
    if not p.active:
        return False
    in_dept = p.department in departments
    has_role = bool(p.roles & set(roles))
    if visibility == "cong-khai":
        return True
    if visibility == "phong-ban":
        return in_dept or has_role
    if visibility == "han-che":
        if not departments and not roles:
            return False
        return (in_dept or not departments) and (has_role or not roles)
    return False  # giá trị lạ -> từ chối (fail closed)
