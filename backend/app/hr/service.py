"""Nghiệp vụ cho /api/hr: phép năm, đơn nghỉ, danh bạ (ADR-003, docs/07 mục 9.3). Không phụ thuộc FastAPI.

Phân quyền (ADR-003):
- Danh tính là Principal lấy từ token + bảng employees; mã nhân viên KHÔNG bao giờ nhận từ client.
- Danh sách lọc bằng điều kiện SQL của `app.hr.authz` (`scope_sql`, `directory_sql`); mỗi dòng ra khỏi service còn
  được kiểm lại bằng hàm Python thuần `can()` / `can_view_employee()` (bản cài thứ hai, ADR-003 mục 9). Hai bản lệch
  nhau thì dòng đó bị bỏ và ghi log "rò quyền": thà thiếu một dòng còn hơn lộ dữ liệu.
- Chỉ đọc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.hr.authz import (
    Target,
    can,
    can_view_employee,
    can_view_phone,
    directory_sql,
    scope_sql,
    scopes_of,
)
from app.models import AuditLog, Employee, EmployeeContact, LeaveBalance, LeaveRequest
from app.rag.acl import Principal

log = logging.getLogger("hr")

LEAVE_BALANCE = "leave_balance:read"
LEAVE_REQUEST = "leave_request:read"
MAX_REQUESTS = 500
MAX_DIRECTORY = 300

NO_TEAM_SCOPE = "Bạn không có quyền xem phép của người khác."


class HrError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Balance:
    year: int
    entitled: float
    carried_over: float
    carried_expired: float
    used: float
    remaining: float


@dataclass(frozen=True)
class Person:
    code: str
    name: str
    department: str
    title: str


@dataclass(frozen=True)
class Leave:
    code: str
    employee: Person
    kind: str
    from_date: date
    to_date: date
    days: float
    status: str
    approver_name: str | None
    note: str


@dataclass(frozen=True)
class Member:
    person: Person
    balance: Balance | None
    pending: int  # số đơn đang chờ duyệt


@dataclass(frozen=True)
class MyLeave:
    year: int
    person: Person
    balance: Balance | None
    requests: list[Leave]
    can_view_team: bool


@dataclass(frozen=True)
class TeamLeave:
    year: int
    scopes: list[str]
    members: list[Member]
    requests: list[Leave]


@dataclass(frozen=True)
class DirectoryRow:
    person: Person
    email: str
    phone: str | None
    phone_visible: bool
    active: bool


@dataclass(frozen=True)
class Directory:
    items: list[DirectoryRow]
    departments: list[str]
    truncated: bool


def _person(e: Employee) -> Person:
    return Person(e.code, e.full_name, e.department, e.title)


def _balance(b: LeaveBalance | None) -> Balance | None:
    if b is None:
        return None
    return Balance(b.year, b.entitled, b.carried_over, b.carried_expired, b.used, b.remaining)


def audit(db: Session, p: Principal, event: str, detail: dict) -> None:
    """ADR-003 mục 8. Chỉ ghi phạm vi, số dòng, lý do: không ghi dữ liệu nhân sự. `actor` là email người hỏi."""
    db.add(AuditLog(user_id=None, event=event, detail={**detail, "actor": p.email}))
    db.commit()


def _leaves(db: Session, p: Principal, *where, limit: int = MAX_REQUESTS) -> list[Leave]:
    """Đơn nghỉ kèm người nghỉ và người duyệt, qua một truy vấn; mỗi đơn còn được kiểm lại bằng `can()`."""
    owner, approver = aliased(Employee), aliased(Employee)
    stmt = (
        select(LeaveRequest, owner, approver.full_name)
        .join(owner, owner.code == LeaveRequest.employee_code)
        .outerjoin(approver, approver.code == LeaveRequest.approver_code)
        .where(*where)
        # chờ duyệt lên trước, rồi mới nhất trước
        .order_by(
            (LeaveRequest.status != "cho-duyet"), LeaveRequest.from_date.desc(), LeaveRequest.code.desc()
        )
        .limit(limit)
    )
    out: list[Leave] = []
    for r, emp, approver_name in db.execute(stmt).all():
        if not can(p, LEAVE_REQUEST, Target.of(emp)):
            log.warning("Rò quyền? SQL trả đơn %s của %s nhưng can() từ chối %s", r.code, emp.code, p.code)
            continue
        out.append(
            Leave(r.code, _person(emp), r.kind, r.from_date, r.to_date, r.days, r.status, approver_name, r.note)
        )
    return out


def _can_view_team(p: Principal) -> bool:
    return any(s != "own" for s in scopes_of(p, LEAVE_BALANCE) + scopes_of(p, LEAVE_REQUEST))


def my_leave(db: Session, p: Principal, year: int) -> MyLeave:
    me = db.execute(select(Employee).where(Employee.code == p.code)).scalar_one()
    bal = db.execute(
        select(LeaveBalance).where(LeaveBalance.employee_code == p.code, LeaveBalance.year == year)
    ).scalar_one_or_none()
    own = _leaves(db, p, LeaveRequest.employee_code == p.code)
    return MyLeave(year, _person(me), _balance(bal), own, _can_view_team(p))


def team_leave(db: Session, p: Principal, year: int) -> TeamLeave:
    """Phép của NGƯỜI KHÁC theo các phạm vi team/dept/all mà vai trò có. Không có phạm vi nào thì từ chối (và ghi)."""
    scopes = sorted(
        {s for s in scopes_of(p, LEAVE_BALANCE) + scopes_of(p, LEAVE_REQUEST) if s != "own"},
        key=("team", "dept", "all").index,
    )
    if not scopes:
        audit(db, p, "hr_denied", {"resource": "leave_team", "reason": "no_scope"})
        raise HrError(403, NO_TEAM_SCOPE)

    not_me = Employee.code != p.code
    emps = (
        db.execute(
            select(Employee).where(scope_sql(p, LEAVE_BALANCE), not_me).order_by(Employee.department, Employee.full_name)
        )
        .scalars()
        .all()
    )
    members_emps = [e for e in emps if can(p, LEAVE_BALANCE, Target.of(e))]
    if len(members_emps) != len(emps):
        log.warning("Rò quyền? scope_sql và can() lệch nhau với %s (số dư phép)", p.code)

    codes = [e.code for e in members_emps]
    balances = {
        b.employee_code: b
        for b in db.execute(
            select(LeaveBalance).where(LeaveBalance.employee_code.in_(codes), LeaveBalance.year == year)
        ).scalars()
    }
    in_scope = select(Employee.code).where(scope_sql(p, LEAVE_REQUEST), not_me)  # subquery: tránh nhân đôi bảng employees
    requests = _leaves(db, p, LeaveRequest.employee_code.in_(in_scope))
    pending: dict[str, int] = {}
    for r in requests:
        if r.status == "cho-duyet":
            pending[r.employee.code] = pending.get(r.employee.code, 0) + 1

    members = [Member(_person(e), _balance(balances.get(e.code)), pending.get(e.code, 0)) for e in members_emps]
    audit(db, p, "hr_view", {"resource": "leave_team", "scopes": scopes, "rows": len(members) + len(requests)})
    return TeamLeave(year, scopes, members, requests)


def _unaccent_like(col, text: str):
    """Tìm không phân biệt hoa thường và dấu: gõ "nguyen" khớp "Nguyễn" (f_unaccent do init_db tạo)."""
    like = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    return func.f_unaccent(col).ilike(func.f_unaccent(like), escape="\\")


def directory(db: Session, p: Principal, *, q: str | None = None, department: str | None = None) -> Directory:
    visible = directory_sql(p)
    stmt = select(Employee, EmployeeContact.phone).outerjoin(
        EmployeeContact, EmployeeContact.employee_code == Employee.code
    )
    stmt = stmt.where(visible)
    if department:
        stmt = stmt.where(Employee.department == department)
    if q and q.strip():
        t = q.strip()
        stmt = stmt.where(
            or_(
                _unaccent_like(Employee.full_name, t),
                _unaccent_like(Employee.email, t),
                _unaccent_like(Employee.title, t),
                _unaccent_like(Employee.code, t),
            )
        )
    rows = db.execute(stmt.order_by(Employee.department, Employee.full_name).limit(MAX_DIRECTORY + 1)).all()
    truncated = len(rows) > MAX_DIRECTORY

    items: list[DirectoryRow] = []
    for emp, phone in rows[:MAX_DIRECTORY]:
        target = Target.of(emp)
        if not can_view_employee(p, target):
            log.warning("Rò quyền? directory_sql trả %s nhưng can_view_employee() từ chối %s", emp.code, p.code)
            continue
        show_phone = bool(can_view_phone(p, target))
        items.append(
            DirectoryRow(
                _person(emp), emp.email, phone if show_phone else None, show_phone, emp.status == "dang-lam"
            )
        )
    departments = sorted(
        db.execute(select(Employee.department).where(visible).distinct()).scalars().all()
    )
    return Directory(items, departments, truncated)
