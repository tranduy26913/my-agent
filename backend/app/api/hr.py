"""Router /api/hr: nghỉ phép và danh bạ cho /tools/nghi-phep, /tools/danh-ba (docs/07 mục 9.3, ADR-003).

Mọi nhân viên đang làm việc dùng được (get_principal); phạm vi xem do app.hr.authz quyết định theo vai trò trong bảng
employees. Chỉ đọc. Router chỉ nhận request, gọi app.hr.service, đổi sang schema JSON camelCase.
"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_principal
from app.api.kb import CamelModel
from app.hr import service
from app.rag.acl import Principal

router = APIRouter(tags=["hr"])


class PersonOut(CamelModel):
    code: str
    name: str
    department: str
    title: str


class BalanceOut(CamelModel):
    year: int
    entitled: float
    carried_over: float
    carried_expired: float
    used: float
    remaining: float


class LeaveOut(CamelModel):
    code: str
    employee: PersonOut
    kind: str
    from_date: date
    to_date: date
    days: float
    # `str` chứ không phải Literal: dòng dữ liệu lạ không được làm 500 cả danh sách
    status: str
    approver_name: str | None
    note: str


class MyLeaveOut(CamelModel):
    year: int
    person: PersonOut
    balance: BalanceOut | None
    requests: list[LeaveOut]
    can_view_team: bool  # vai trò có phạm vi ngoài `own`: portal hiện tab "Nhóm của tôi" (backend vẫn tự kiểm)


class MemberOut(CamelModel):
    person: PersonOut
    balance: BalanceOut | None
    pending: int


class TeamLeaveOut(CamelModel):
    year: int
    scopes: list[Literal["team", "dept", "all"]]
    members: list[MemberOut]
    requests: list[LeaveOut]


class DirectoryRowOut(CamelModel):
    person: PersonOut
    email: str
    phone: str | None  # None khi bị che (phone_visible = false) hoặc chưa có số
    phone_visible: bool
    active: bool


class DirectoryOut(CamelModel):
    items: list[DirectoryRowOut]
    departments: list[str]
    truncated: bool


def _person(p: service.Person) -> PersonOut:
    return PersonOut(code=p.code, name=p.name, department=p.department, title=p.title)


def _balance(b: service.Balance | None) -> BalanceOut | None:
    return BalanceOut(**vars(b)) if b else None


def _leave(x: service.Leave) -> LeaveOut:
    return LeaveOut(
        code=x.code, employee=_person(x.employee), kind=x.kind, from_date=x.from_date, to_date=x.to_date,
        days=x.days, status=x.status, approver_name=x.approver_name, note=x.note,
    )


@router.get("/leave/me", response_model=MyLeaveOut)
def leave_me(
    year: int | None = Query(default=None, ge=2000, le=2100),
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> MyLeaveOut:
    r = service.my_leave(db, p, year or date.today().year)
    return MyLeaveOut(
        year=r.year, person=_person(r.person), balance=_balance(r.balance),
        requests=[_leave(x) for x in r.requests], can_view_team=r.can_view_team,
    )


@router.get("/leave/team", response_model=TeamLeaveOut)
def leave_team(
    year: int | None = Query(default=None, ge=2000, le=2100),
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> TeamLeaveOut:
    try:
        r = service.team_leave(db, p, year or date.today().year)
    except service.HrError as e:
        raise HTTPException(e.status_code, str(e)) from e
    return TeamLeaveOut(
        year=r.year, scopes=r.scopes,
        members=[MemberOut(person=_person(m.person), balance=_balance(m.balance), pending=m.pending) for m in r.members],
        requests=[_leave(x) for x in r.requests],
    )


@router.get("/directory", response_model=DirectoryOut)
def directory(
    q: str | None = Query(default=None, max_length=100, description="Tên, email, chức danh hoặc mã (không phân biệt dấu)"),
    department: str | None = Query(default=None, max_length=64),
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> DirectoryOut:
    r = service.directory(db, p, q=q, department=department)
    return DirectoryOut(
        items=[
            DirectoryRowOut(
                person=_person(x.person), email=x.email, phone=x.phone, phone_visible=x.phone_visible, active=x.active
            )
            for x in r.items
        ],
        departments=r.departments,
        truncated=r.truncated,
    )
