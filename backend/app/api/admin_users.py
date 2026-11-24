"""Router /api/admin/users: tài khoản đăng nhập (Zitadel) ghép với danh bạ nhân sự (docs/07 mục 9.1).

Hợp đồng: portal/src/features/users/types.ts. JSON camelCase. Chỉ admin (get_admin). Router chỉ nhận request, kiểm
quyền, gọi app.user_admin_service rồi đổi sang schema; ghi audit nằm ở service.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field
from sqlalchemy.orm import Session

from app import user_admin_service as svc
from app.api.deps import Actor, get_admin, get_db
from app.api.kb import CamelModel
from app.auth.zitadel_admin import ZitadelAdmin, get_zitadel_admin

router = APIRouter(tags=["admin"])

AccountState = Literal["active", "inactive", "locked", "none", "other"]


def zitadel(z: ZitadelAdmin | None = Depends(get_zitadel_admin)) -> ZitadelAdmin:
    if z is None:
        raise HTTPException(503, "Chưa cấu hình kết nối Zitadel cho trang này (ZITADEL_ADMIN_PAT).")
    return z


class EmployeeOut(CamelModel):
    code: str
    department: str
    title: str
    roles: list[str]
    active: bool  # đang làm việc


class UserOut(CamelModel):
    key: str
    email: str
    full_name: str
    employee: EmployeeOut | None  # None = tài khoản Zitadel không có trong danh bạ nhân sự
    zitadel_id: str | None  # None = chưa có tài khoản
    account: AccountState
    warning: str | None


class UsersOut(CamelModel):
    items: list[UserOut]


class CreateIn(CamelModel):
    email: str = Field(min_length=3, max_length=128)


class TempPasswordOut(CamelModel):
    temp_password: str


class CreatedOut(TempPasswordOut):
    user: UserOut


def to_user_out(r: svc.UserRow) -> UserOut:
    e = r.employee
    return UserOut(
        key=r.key,
        email=r.email,
        full_name=r.full_name,
        employee=EmployeeOut(
            code=e.code,
            department=e.department,
            title=e.title,
            roles=sorted(e.roles or []),
            active=e.status == svc.ACTIVE_EMPLOYEE,
        )
        if e
        else None,
        zitadel_id=r.zitadel_id,
        account=r.account,
        warning=r.warning,
    )


def _no_store(response: Response) -> None:
    # Phản hồi có mật khẩu tạm: không cho trình duyệt hay proxy giữ lại.
    response.headers["Cache-Control"] = "no-store"


def _fail(e: svc.UserAdminError) -> HTTPException:
    return HTTPException(e.status_code, str(e))


# `def` thường: gọi Zitadel và DB đều là việc đồng bộ, FastAPI chạy trong thread pool.
@router.get("/users", response_model=UsersOut)
def list_users(_admin: Actor = Depends(get_admin), db: Session = Depends(get_db), z: ZitadelAdmin = Depends(zitadel)):
    try:
        return UsersOut(items=[to_user_out(r) for r in svc.list_users(db, z)])
    except svc.UserAdminError as e:
        raise _fail(e) from e


@router.post("/users", response_model=CreatedOut, status_code=201)
def create_user(
    body: CreateIn,
    response: Response,
    admin: Actor = Depends(get_admin),
    db: Session = Depends(get_db),
    z: ZitadelAdmin = Depends(zitadel),
):
    _no_store(response)
    try:
        row, password = svc.create_account(db, z, admin.email, body.email)
    except svc.UserAdminError as e:
        raise _fail(e) from e
    return CreatedOut(user=to_user_out(row), temp_password=password)


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: str, admin: Actor = Depends(get_admin), db: Session = Depends(get_db), z: ZitadelAdmin = Depends(zitadel)
):
    try:
        return to_user_out(svc.set_active(db, z, admin.email, user_id, active=False))
    except svc.UserAdminError as e:
        raise _fail(e) from e


@router.post("/users/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(
    user_id: str, admin: Actor = Depends(get_admin), db: Session = Depends(get_db), z: ZitadelAdmin = Depends(zitadel)
):
    try:
        return to_user_out(svc.set_active(db, z, admin.email, user_id, active=True))
    except svc.UserAdminError as e:
        raise _fail(e) from e


@router.post("/users/{user_id}/password", response_model=TempPasswordOut)
def reset_user_password(
    user_id: str,
    response: Response,
    admin: Actor = Depends(get_admin),
    db: Session = Depends(get_db),
    z: ZitadelAdmin = Depends(zitadel),
):
    _no_store(response)
    try:
        return TempPasswordOut(temp_password=svc.reset_password(db, z, admin.email, user_id))
    except svc.UserAdminError as e:
        raise _fail(e) from e
