"""Xác thực (JWT) + phân quyền (RBAC). Tương đương [Authorize(Roles=...)] trong ASP.NET Core."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass(frozen=True)
class UserInfo:
    """Danh tính thuần (không phụ thuộc ORM) -> agent/tool dùng được cả khi test không có DB."""

    id: int
    username: str
    role: str
    department: str
    full_name: str = ""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def to_user_info(user) -> UserInfo:
    return UserInfo(user.id, user.username, user.role, user.department, user.full_name)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserInfo:
    from app.models import User

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ") from e
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User không tồn tại")
    return to_user_info(user)


def require_roles(*roles: str):
    def checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Cần quyền: {', '.join(roles)}")
        return user

    return checker
