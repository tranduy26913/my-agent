"""Client cho User Service (API v2) của Zitadel (docs/06, giai đoạn 2.6 và 4.4).

Dùng PAT của machine user `portal-admin-api` (role org ORG_USER_MANAGER: chỉ quản lý user).
Gọi qua httpx (đồng bộ). Lớp này không biết gì về audit hay quyền: người gọi (app/user_admin_service.py, dùng cho
/api/admin/users) kiểm quyền và ghi audit_logs.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from functools import lru_cache

import httpx


class ZitadelError(RuntimeError):
    pass


def get_zitadel_admin() -> ZitadelAdmin | None:
    """Client dùng chung cho /api/admin/users; None khi chưa cấu hình PAT. Là dependency để test thay bằng bản giả."""
    return _default_client()


@lru_cache
def _default_client() -> ZitadelAdmin | None:
    from app.config import settings

    base = (settings.zitadel_admin_url or settings.oidc_internal_url or settings.oidc_issuer).rstrip("/")
    if not settings.zitadel_admin_pat or not base:
        return None
    return ZitadelAdmin(base, settings.zitadel_admin_pat, host=settings.oidc_host_header or None)


def split_name(full_name: str) -> tuple[str, str]:
    """'Phạm Đức Long' -> ('Long', 'Phạm Đức'): tên là từ cuối (givenName), phần còn lại là họ đệm."""
    parts = full_name.split()
    if len(parts) < 2:
        return (parts[0] if parts else "", "-")  # Zitadel bắt buộc có cả hai
    return parts[-1], " ".join(parts[:-1])


def temp_password(length: int = 16) -> str:
    """Mật khẩu tạm đạt chính sách (>= 10 ký tự, đủ 4 loại ký tự); buộc đổi khi vào lần đầu."""
    pools = [string.ascii_uppercase, string.ascii_lowercase, string.digits, "!@#$%*-_"]
    chars = [secrets.choice(p) for p in pools]
    chars += [secrets.choice("".join(pools)) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


@dataclass
class ZitadelUser:
    id: str
    username: str
    state: str  # USER_STATE_ACTIVE | USER_STATE_INACTIVE | ...
    email: str = ""
    display_name: str = ""
    human: bool = True


STATE_ACTIVE = "USER_STATE_ACTIVE"
STATE_INACTIVE = "USER_STATE_INACTIVE"
LIST_PAGE = 100
LIST_MAX = 1000  # trần số tài khoản đọc một lần: quá thì ném lỗi thay vì lặng lẽ cắt bớt


def _to_user(u: dict) -> ZitadelUser:
    human = u.get("human") or {}
    return ZitadelUser(
        id=u["userId"],
        username=u.get("username", ""),
        state=u["state"],
        email=(human.get("email") or {}).get("email", ""),
        display_name=(human.get("profile") or {}).get("displayName", ""),
        human="human" in u,
    )


class ZitadelAdmin:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        host: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        # `host`: Zitadel chọn instance theo header Host, nên khi gọi qua localhost phải giả domain ngoài.
        headers = {"Authorization": f"Bearer {token}"}
        if host:
            headers["Host"] = host
        self._c = httpx.Client(base_url=base_url, headers=headers, timeout=30, transport=transport)

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        r = self._c.request(method, path, json=body)
        if r.status_code >= 400:
            raise ZitadelError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else {}

    def find_by_username(self, username: str) -> ZitadelUser | None:
        q = {"queries": [{"userNameQuery": {"userName": username, "method": "TEXT_QUERY_METHOD_EQUALS"}}]}
        found = self._call("POST", "/v2/users", q).get("result", [])
        if not found:
            return None
        return _to_user(found[0])

    def list_humans(self) -> list[ZitadelUser]:
        """Mọi tài khoản người (không gồm machine user như portal-admin-api). Quá LIST_MAX thì ném lỗi."""
        out: list[ZitadelUser] = []
        while True:
            body = {
                "query": {"offset": len(out), "limit": LIST_PAGE, "asc": True},
                "sortingColumn": "USER_FIELD_NAME_CREATION_DATE",
                "queries": [{"typeQuery": {"type": "TYPE_HUMAN"}}],
            }
            page = self._call("POST", "/v2/users", body).get("result", [])
            out.extend(_to_user(u) for u in page)
            if len(page) < LIST_PAGE:
                return out
            if len(out) >= LIST_MAX:
                raise ZitadelError(f"Hơn {LIST_MAX} tài khoản: cần làm phân trang cho trang quản trị")

    def get_user(self, user_id: str) -> ZitadelUser | None:
        """None nếu không có. `user_id` phải là chuỗi số (id của Zitadel): chặn ký tự lạ trước khi ghép vào đường dẫn."""
        if not user_id.isascii() or not user_id.isdigit() or len(user_id) > 32:
            return None
        r = self._c.request("GET", f"/v2/users/{user_id}")
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise ZitadelError(f"GET /v2/users/{{id}} -> {r.status_code}: {r.text[:300]}")
        return _to_user(r.json()["user"])

    def set_temp_password(self, user_id: str, password: str) -> None:
        """Đặt mật khẩu tạm, buộc người dùng đổi ở lần đăng nhập sau."""
        self._call("POST", f"/v2/users/{user_id}/password", {"newPassword": {"password": password, "changeRequired": True}})

    def create_human(self, *, username: str, email: str, full_name: str, password: str) -> str:
        """Tạo human user, email đã xác minh sẵn (không cần SMTP), buộc đổi mật khẩu ở lần đăng nhập đầu."""
        given, family = split_name(full_name)
        body = {
            "username": username,
            "profile": {
                "givenName": given,
                "familyName": family,
                "displayName": full_name,
                "preferredLanguage": "vi",
            },
            "email": {"email": email, "isVerified": True},
            "password": {"password": password, "changeRequired": True},
        }
        return self._call("POST", "/v2/users/human", body)["userId"]

    def change_login(self, user_id: str, *, username: str, email: str) -> None:
        """Đổi tên đăng nhập và email (đánh dấu đã xác minh, không cần SMTP). Giữ nguyên user id và mật khẩu."""
        self._call(
            "PUT",
            f"/v2/users/human/{user_id}",
            {"username": username, "email": {"email": email, "isVerified": True}},
        )

    def deactivate(self, user_id: str) -> None:
        self._call("POST", f"/v2/users/{user_id}/deactivate", {})

    def reactivate(self, user_id: str) -> None:
        self._call("POST", f"/v2/users/{user_id}/reactivate", {})
