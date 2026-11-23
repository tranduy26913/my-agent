"""Phân quyền dữ liệu nhân sự - RBAC có phạm vi (ADR-003: docs/adr/ADR-003-phan-quyen-du-lieu-hr.md).

Permission dạng `tài_nguyên:hành_động:phạm_vi`, ví dụ `leave_balance:read:team`.
- Cho/không cho: RBAC thuần - hợp các permission của mọi vai trò người hỏi đang giữ (không có luật cấm).
- Phạm vi (own/team/dept/all) quyết định XEM CỦA AI, được dịch thành điều kiện lọc ở tầng dữ liệu.

Có HAI bản cài đặt cùng một quy tắc, viết độc lập (giống acl.py của ADR-001):
1. `scope_sql()` -> mệnh đề WHERE trên bảng employees, dùng cho truy vấn danh sách.
2. `can()`       -> hàm Python thuần, dùng kiểm tra từng bản ghi và để eval so chéo với bản SQL.
"""

from dataclasses import dataclass

from sqlalchemy import and_, false, or_, true

from app.rag.acl import Principal

# ------------------------------------------------------------------ ma trận ADR-003 (nguồn sự thật)

_OWN = ("leave_balance:read:own", "leave_request:read:own")
_DIRECTORY = ("directory:read:basic", "directory:read:phone_dept")

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "employee": frozenset({*_OWN, *_DIRECTORY}),
    "manager": frozenset({*_OWN, *_DIRECTORY, "leave_balance:read:team", "leave_request:read:team"}),
    "truong-phong": frozenset({*_OWN, *_DIRECTORY, "leave_balance:read:dept", "leave_request:read:dept"}),
    "hr": frozenset({
        *_OWN, *_DIRECTORY, "leave_balance:read:all", "leave_request:read:all",
        "directory:read:phone_all", "directory:read:inactive", "salary:read:all",
    }),
    "executive": frozenset({
        *_OWN, *_DIRECTORY, "leave_balance:read:team", "leave_request:read:team",
        "directory:read:phone_all", "salary:read:all",
    }),
    # Quản trị hệ thống KHÔNG đồng nghĩa được đọc dữ liệu nhân sự (least privilege, như ADR-001).
    "admin": frozenset({*_OWN, *_DIRECTORY}),
}

SCOPED_RESOURCES = ("leave_balance:read", "leave_request:read", "salary:read")
SCOPES = ("own", "team", "dept", "all")
INACTIVE = "directory:read:inactive"


@dataclass(frozen=True)
class Target:
    """Nhân viên đích (người bị hỏi tới). Chỉ chứa các thuộc tính quy tắc cần."""

    code: str
    department: str
    manager_code: str | None = None
    active: bool = True

    @classmethod
    def of(cls, emp) -> "Target":
        return cls(emp.code, emp.department, emp.manager_code, emp.status == "dang-lam")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    scope: str | None = None  # phạm vi đã khớp -> ghi audit

    def __bool__(self) -> bool:
        return self.allowed


def permissions(p: Principal) -> frozenset[str]:
    """Hợp permission của mọi vai trò. Người hỏi đã nghỉ việc hoặc vai trò lạ -> không có gì (fail closed)."""
    if not p.active or not p.code:
        return frozenset()
    out: set[str] = set()
    for role in p.roles:
        out |= ROLE_PERMISSIONS.get(role, frozenset())
    return frozenset(out)


def _scopes(perms: frozenset[str], resource: str) -> list[str]:
    return [s for s in SCOPES if f"{resource}:{s}" in perms]


# ------------------------------------------------------------------ bản 1: Python thuần

def can(p: Principal, resource: str, target: Target) -> Decision:
    """Người hỏi có được đọc `resource` (vd "leave_balance:read") của nhân viên `target` không."""
    if resource not in SCOPED_RESOURCES:
        return Decision(False, f"Tài nguyên không xác định: {resource}")
    if not p.active:
        return Decision(False, "Tài khoản nhân sự của bạn không còn hoạt động.")
    perms = permissions(p)
    if not target.active and INACTIVE not in perms:
        return Decision(False, "Không tìm thấy nhân viên đang làm việc phù hợp.")
    for scope in _scopes(perms, resource):
        if (
            scope == "all"
            or (scope == "own" and target.code == p.code)
            or (scope == "team" and target.manager_code == p.code)
            or (scope == "dept" and target.department == p.department)
        ):
            return Decision(True, f"Khớp {resource}:{scope}", scope)
    if resource == "salary:read" and target.code == p.code:
        return Decision(False, 'Thông tin lương là Mật: vui lòng xem mục "Phiếu lương của tôi" trên HRM.')
    return Decision(False, "Bạn không có quyền xem thông tin này của người khác.")


def can_view_employee(p: Principal, target: Target) -> Decision:
    """Danh bạ cơ bản: tên, phòng, chức danh, email của nhân viên đang làm."""
    perms = permissions(p)
    if "directory:read:basic" not in perms:
        return Decision(False, "Bạn không có quyền tra cứu danh bạ.")
    if not target.active and INACTIVE not in perms:
        return Decision(False, "Không tìm thấy nhân viên đang làm việc phù hợp.")
    return Decision(True, "Khớp directory:read:basic", "all")


def can_view_phone(p: Principal, target: Target) -> Decision:
    """Che số điện thoại: chỉ hiện cho bản thân, người cùng phòng, hoặc ai có phone_all."""
    base = can_view_employee(p, target)
    if not base:
        return base
    perms = permissions(p)
    if "directory:read:phone_all" in perms:
        return Decision(True, "Khớp directory:read:phone_all", "all")
    if "directory:read:phone_dept" in perms and target.department == p.department:
        return Decision(True, "Khớp directory:read:phone_dept", "dept")
    return Decision(False, "Số điện thoại chỉ hiển thị cho người cùng phòng.")


# ------------------------------------------------------------------ bản 2: SQL (viết độc lập với can())

def scope_sql(p: Principal, resource: str):
    """WHERE trên bảng employees: các nhân viên mà người hỏi được đọc `resource`."""
    from app.models import Employee

    if resource not in SCOPED_RESOURCES or not p.active:
        return false()
    perms = permissions(p)
    by_scope = {
        "own": Employee.code == p.code,
        "team": Employee.manager_code == p.code,
        "dept": Employee.department == p.department,
        "all": true(),
    }
    conds = [by_scope[s] for s in _scopes(perms, resource)]
    if not conds:
        return false()
    visible = or_(*conds)
    if INACTIVE in perms:
        return visible
    return and_(visible, Employee.status == "dang-lam")
