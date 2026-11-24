"""Nghiệp vụ cho /api/admin/users (docs/07 mục 9.1). Không phụ thuộc FastAPI.

Ghép hai nguồn theo email: `employees` (ai là nhân viên, đang làm hay đã nghỉ) và Zitadel (ai có tài khoản đăng nhập).
Mọi thao tác ghi đều ghi `audit_logs` (user_id = NULL, người làm ở detail["actor"], đối tượng ở detail["target"]).

Thứ tự trong mỗi thao tác ghi: (1) kiểm tra điều kiện, (2) thêm dòng audit và flush (chưa commit), (3) gọi Zitadel,
(4) commit. DB hỏng thì từ chối trước khi đổi gì ở Zitadel; Zitadel lỗi thì rollback nên không có dòng audit cho việc
chưa xảy ra. Mật khẩu tạm KHÔNG bao giờ vào audit hay log.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.zitadel_admin import (
    STATE_ACTIVE,
    STATE_INACTIVE,
    ZitadelAdmin,
    ZitadelError,
    ZitadelUser,
    temp_password,
)
from app.models import AuditLog, Employee

log = logging.getLogger("user_admin")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ACTIVE_EMPLOYEE = "dang-lam"

Account = str  # active | inactive | locked | none | other


class UserAdminError(Exception):
    """Lỗi nghiệp vụ có mã HTTP kèm câu tiếng Việt cho người dùng."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class UserRow:
    key: str  # id Zitadel nếu có tài khoản, không thì "e:<mã nhân viên>"
    email: str
    full_name: str
    employee: Employee | None
    zitadel_id: str | None
    account: Account
    warning: str | None = None


def _account_of(state: str) -> Account:
    return {STATE_ACTIVE: "active", STATE_INACTIVE: "inactive", "USER_STATE_LOCKED": "locked"}.get(state, "other")


def _warning(emp: Employee | None, account: Account) -> str | None:
    if emp is None:
        return "Không có trong danh bạ nhân sự: đăng nhập sẽ bị chặn ở bước kiểm tra nhân viên."
    if emp.status != ACTIVE_EMPLOYEE and account in ("active", "locked", "other"):
        return "Đã nghỉ việc nhưng tài khoản còn mở."
    if account == "locked":
        return "Đang bị khoá tạm do nhập sai mật khẩu nhiều lần; trang này chưa mở được loại khoá này."
    return None


def _row(emp: Employee | None, z: ZitadelUser | None) -> UserRow:
    account = _account_of(z.state) if z else "none"
    email = (emp.email if emp else (z.email or z.username if z else "")).lower()
    name = emp.full_name if emp else (z.display_name if z else "")
    return UserRow(
        key=z.id if z else f"e:{emp.code}",  # type: ignore[union-attr]  (emp và z không thể cùng None)
        email=email,
        full_name=name,
        employee=emp,
        zitadel_id=z.id if z else None,
        account=account,
        warning=_warning(emp, account) if z else None,  # chưa có tài khoản thì không có gì để cảnh báo
    )


def _call(fn, *args, **kwargs):
    """Gọi Zitadel; mọi lỗi thành 502 với câu chung (chi tiết chỉ vào log)."""
    try:
        return fn(*args, **kwargs)
    except (ZitadelError, httpx.HTTPError) as e:
        log.error("Zitadel lỗi: %s", e)
        raise UserAdminError(502, "Zitadel không thực hiện được thao tác. Chi tiết nằm trong log của backend.") from e


def _audit(db: Session, actor: str, event: str, target: str) -> None:
    db.add(AuditLog(user_id=None, event=event, detail={"actor": actor, "target": target}))
    db.flush()


def _employee_by_email(db: Session, email: str) -> Employee | None:
    stmt = select(Employee).where(func.lower(Employee.email) == email.strip().lower())
    return db.execute(stmt).scalar_one_or_none()


def list_users(db: Session, z: ZitadelAdmin) -> list[UserRow]:
    employees = db.execute(select(Employee).order_by(Employee.department, Employee.full_name)).scalars().all()
    by_email = {e.email.lower(): e for e in employees}
    accounts = _call(z.list_humans)

    rows: list[UserRow] = []
    seen: set[str] = set()
    for u in accounts:
        key = (u.email or u.username).lower()
        emp = by_email.get(key) or by_email.get(u.username.lower())
        if emp is not None:
            seen.add(emp.email.lower())
        rows.append(_row(emp, u))
    rows += [_row(e, None) for e in employees if e.email.lower() not in seen]

    # Đang làm lên trước; trong mỗi nhóm theo phòng ban rồi tên. Tài khoản vô chủ ở cuối.
    def order(r: UserRow):
        emp = r.employee
        return (
            emp is None,
            emp.status != ACTIVE_EMPLOYEE if emp else False,
            emp.department if emp else "",
            (emp.full_name if emp else r.full_name).casefold(),
        )

    return sorted(rows, key=order)


def create_account(db: Session, z: ZitadelAdmin, actor: str, email: str) -> tuple[UserRow, str]:
    email = email.strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 128:
        raise UserAdminError(422, "Email không hợp lệ")
    emp = _employee_by_email(db, email)
    if emp is None:
        raise UserAdminError(422, "Email chưa có trong danh bạ nhân sự: thêm nhân viên vào danh bạ trước.")
    if emp.status != ACTIVE_EMPLOYEE:
        raise UserAdminError(409, "Nhân viên đã nghỉ việc, không tạo tài khoản mới.")
    email = emp.email.lower()
    if _call(z.find_by_username, email) is not None:
        raise UserAdminError(409, "Nhân viên này đã có tài khoản.")

    password = temp_password()
    _audit(db, actor, "user_create", email)
    try:
        user_id = _call(z.create_human, username=email, email=email, full_name=emp.full_name, password=password)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _row(emp, ZitadelUser(id=user_id, username=email, state=STATE_ACTIVE, email=email)), password


def _human(z: ZitadelAdmin, user_id: str) -> ZitadelUser:
    u = _call(z.get_user, user_id)
    if u is None or not u.human:
        # Cố ý trả 404 cho cả machine user: endpoint này không được dùng để khoá portal-admin-api hay bootstrap.
        raise UserAdminError(404, "Không tìm thấy tài khoản")
    return u


def _row_for(db: Session, u: ZitadelUser) -> UserRow:
    return _row(_employee_by_email(db, u.email or u.username), u)


def set_active(db: Session, z: ZitadelAdmin, actor: str, user_id: str, active: bool) -> UserRow:
    u = _human(z, user_id)
    target = (u.email or u.username).lower()
    if not active and target == actor.strip().lower():
        raise UserAdminError(409, "Không thể tự khoá tài khoản của chính mình.")
    if active and u.state == STATE_ACTIVE:
        raise UserAdminError(409, "Tài khoản đang hoạt động.")
    if not active and u.state == STATE_INACTIVE:
        raise UserAdminError(409, "Tài khoản đã bị khoá.")
    if u.state not in (STATE_ACTIVE, STATE_INACTIVE):
        raise UserAdminError(409, "Trạng thái hiện tại của tài khoản không cho phép thao tác này.")

    _audit(db, actor, "user_reactivate" if active else "user_deactivate", target)
    try:
        _call(z.reactivate if active else z.deactivate, u.id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _row_for(db, ZitadelUser(**{**u.__dict__, "state": STATE_ACTIVE if active else STATE_INACTIVE}))


def reset_password(db: Session, z: ZitadelAdmin, actor: str, user_id: str) -> str:
    u = _human(z, user_id)
    if u.state != STATE_ACTIVE:
        raise UserAdminError(409, "Chỉ đặt lại mật khẩu cho tài khoản đang hoạt động: mở khoá tài khoản trước.")
    password = temp_password()
    _audit(db, actor, "user_password_reset", (u.email or u.username).lower())
    try:
        _call(z.set_temp_password, u.id, password)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return password
