"""Kiểm access token của Zitadel (OIDC) và dựng Principal (docs/06 giai đoạn 4.1, ADR-004).

Phân vai: Zitadel chỉ trả lời "người này là ai" (chữ ký, issuer, audience, hạn dùng). "Được làm gì" do
backend quyết định, dựa trên `employees.roles` tra theo email: không tin vai trò nằm trong token.

Luồng một request:
    Bearer token -> OidcVerifier.verify (RS256, iss, aud = project id, exp/nbf)
                 -> email (trong claim, hoặc hỏi userinfo của Zitadel rồi cache)
                 -> load_principal(db, email)  -> 403 nếu chưa có trong danh bạ hoặc đã nghỉ việc
Quyền tra lại từ DB ở MỖI request, nên đổi trạng thái nhân viên có hiệu lực ngay dù token còn hạn.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.rag.acl import Principal, load_principal

log = logging.getLogger("oidc")

LEEWAY_SECONDS = 10  # lệch đồng hồ giữa các máy
JWKS_MIN_REFRESH_SECONDS = 30  # kid lạ chỉ được tải lại khoá tối đa mỗi 30 giây (chống bị spam kid giả)
USERINFO_TTL_SECONDS = 300


class OidcError(Exception):
    """Token không dùng được. `status_code` 401 (token sai/hết hạn) hoặc 503 (Zitadel không với tới)."""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Identity:
    """Người đã được Zitadel xác thực. Chưa phải nhân viên: còn phải tra danh bạ (load_principal)."""

    sub: str
    email: str


class KeyStore:
    """Cache khoá công khai (JWKS). Gặp kid lạ thì tải lại, tối đa một lần mỗi JWKS_MIN_REFRESH_SECONDS."""

    def __init__(self, fetch: Callable[[], dict], clock: Callable[[], float] = time.monotonic) -> None:
        self._fetch, self._clock = fetch, clock
        self._keys: dict[str, object] = {}
        self._last_fetch = float("-inf")
        self._lock = threading.Lock()

    def _refresh(self) -> None:
        jwks = self._fetch()
        keys = {}
        for jwk in jwks.get("keys", []):
            if jwk.get("use", "sig") == "sig" and jwk.get("kty") == "RSA" and jwk.get("kid"):
                keys[jwk["kid"]] = jwt.PyJWK.from_dict(jwk).key
        self._keys = keys
        self._last_fetch = self._clock()

    def key_for(self, kid: str | None):
        with self._lock:
            if kid in self._keys:
                return self._keys[kid]
            if self._clock() - self._last_fetch >= JWKS_MIN_REFRESH_SECONDS:
                try:
                    self._refresh()
                except (httpx.HTTPError, ValueError, jwt.PyJWTError) as e:
                    raise OidcError("Không lấy được khoá xác thực của Zitadel", 503) from e
            if kid in self._keys:
                return self._keys[kid]
        raise OidcError("Token ký bằng khoá không rõ")


class OidcVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        project_id: str,
        keys: KeyStore,
        userinfo: Callable[[str], dict] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.issuer, self.project_id, self.keys = issuer, project_id, keys
        self._userinfo = userinfo
        self._clock = clock
        self._userinfo_cache: dict[str, tuple[float, str]] = {}

    def verify(self, token: str) -> dict:
        """Trả claims khi token hợp lệ; ném OidcError nếu không. Chỉ nhận RS256 (không nhận `none`/HS256)."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise OidcError("Token không hợp lệ") from e
        if header.get("alg") != "RS256":
            raise OidcError("Token không hợp lệ")
        key = self.keys.key_for(header.get("kid"))
        try:
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.project_id,  # aud (mảng) phải chứa project id: token dự án khác bị từ chối
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError as e:
            raise OidcError("Token đã hết hạn") from e
        except jwt.PyJWTError as e:
            raise OidcError("Token không hợp lệ") from e

    def identity(self, token: str) -> Identity:
        claims = self.verify(token)
        sub = claims["sub"]
        email, verified = claims.get("email"), claims.get("email_verified")
        if not email:
            email = self._email_from_userinfo(sub, token)
            verified = True  # _email_from_userinfo đã loại email chưa xác minh
        if verified is not True:
            raise OidcError("Email chưa được xác minh")
        return Identity(sub=sub, email=str(email).strip().lower())

    def _email_from_userinfo(self, sub: str, token: str) -> str:
        """Access token JWT của Zitadel không có sẵn email: hỏi userinfo (luôn kiểm token còn hiệu lực)."""
        hit = self._userinfo_cache.get(sub)
        if hit and hit[0] > self._clock():
            return hit[1]
        if self._userinfo is None:
            raise OidcError("Token không có email", 401)
        info = self._userinfo(token)
        if info.get("sub") != sub or not info.get("email") or info.get("email_verified") is not True:
            raise OidcError("Không xác định được email đã xác minh của người dùng")
        self._userinfo_cache[sub] = (self._clock() + USERINFO_TTL_SECONDS, str(info["email"]))
        return str(info["email"])


def _internal_headers() -> dict[str, str]:
    # Zitadel chọn instance theo header Host: gọi qua localhost (chưa có route tunnel) phải giả domain ngoài.
    return {"Host": settings.oidc_host_header} if settings.oidc_host_header else {}


def _base() -> str:
    return (settings.oidc_internal_url or settings.oidc_issuer).rstrip("/")


def _fetch_jwks() -> dict:
    r = httpx.get(f"{_base()}/oauth/v2/keys", headers=_internal_headers(), timeout=5)
    r.raise_for_status()
    return r.json()


def _fetch_userinfo(token: str) -> dict:
    try:
        r = httpx.get(
            f"{_base()}/oidc/v1/userinfo",
            headers={**_internal_headers(), "Authorization": f"Bearer {token}"},
            timeout=5,
        )
    except httpx.HTTPError as e:
        raise OidcError("Không hỏi được userinfo của Zitadel", 503) from e
    if r.status_code in (401, 403):
        raise OidcError("Token không còn hiệu lực")
    if r.status_code >= 400:
        raise OidcError("Zitadel từ chối userinfo", 503)
    return r.json()


@lru_cache
def _default_verifier() -> OidcVerifier | None:
    if not settings.oidc_issuer or not settings.oidc_project_id:
        return None
    return OidcVerifier(
        issuer=settings.oidc_issuer.rstrip("/"),
        project_id=settings.oidc_project_id,
        keys=KeyStore(_fetch_jwks),
        userinfo=_fetch_userinfo,
    )


def get_verifier() -> OidcVerifier | None:
    """None = chưa cấu hình OIDC_ISSUER / OIDC_PROJECT_ID. Là dependency để test thay bằng verifier tự ký."""
    return _default_verifier()


def unauthorized(message: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, message, headers={"WWW-Authenticate": "Bearer"})


def http_error(e: OidcError) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if e.status_code == status.HTTP_401_UNAUTHORIZED else None
    return HTTPException(e.status_code, str(e), headers=headers)


_bearer = HTTPBearer(auto_error=False)


def get_identity(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    verifier: OidcVerifier | None = Depends(get_verifier),
) -> Identity:
    if creds is None or creds.scheme.lower() != "bearer":
        raise unauthorized("Thiếu access token")
    if verifier is None:
        # Fail closed: chưa cấu hình (OIDC_ISSUER, OIDC_PROJECT_ID) thì không ai vào được bằng đường OIDC.
        log.warning("OIDC chưa cấu hình: từ chối mọi Bearer token")
        raise unauthorized("Token không hợp lệ")
    try:
        return verifier.identity(creds.credentials)
    except OidcError as e:
        raise http_error(e) from e


def principal_for(db: Session, identity: Identity) -> Principal:
    """Danh tính đã xác thực -> nhân viên. 403 (không phải 500) khi chưa có trong danh bạ / đã nghỉ việc."""
    p = load_principal(db, identity.email)
    if p is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chưa có trong danh bạ nhân sự")
    if not p.active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản nhân sự không còn hoạt động")
    return p


def get_principal(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)) -> Principal:
    return principal_for(db, identity)


def require_role(*roles: str):
    """Cần một trong các vai trò; kiểm trên Principal.roles (bảng employees), không kiểm trên token."""

    def checker(p: Principal = Depends(get_principal)) -> Principal:
        if not (p.roles & set(roles)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Cần vai trò: {', '.join(roles)}")
        return p

    return checker
