"""Client cho User Service (API v2) của Zitadel (docs/06, giai đoạn 2.6 và 4.4).

Dùng PAT của machine user `portal-admin-api` (role org ORG_USER_MANAGER: chỉ quản lý user).
Gọi qua httpx (đồng bộ); chưa ghi audit_logs: bước đó thuộc giai đoạn 4.4, khi có người
thực hiện (Principal) để ghi.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass

import httpx


class ZitadelError(RuntimeError):
    pass


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
        u = found[0]
        return ZitadelUser(id=u["userId"], username=u["username"], state=u["state"])

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

    def deactivate(self, user_id: str) -> None:
        self._call("POST", f"/v2/users/{user_id}/deactivate", {})

    def reactivate(self, user_id: str) -> None:
        self._call("POST", f"/v2/users/{user_id}/reactivate", {})
