"""Đồ nghề test đăng nhập Zitadel: khoá RSA tự sinh + token tự ký, KHÔNG cần Zitadel đang chạy.

Cùng cách với Zitadel thật: access token RS256 có `kid`, `iss`, `aud` (mảng, có project id), `sub`, `exp`.
"""

import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.oidc import KeyStore, OidcVerifier

ISSUER = "https://auth.test.example"
PROJECT_ID = "400000000000000001"
KID = "test-key-1"


def new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_of(*keys_by_kid: tuple[str, object]) -> dict:
    keys = []
    for kid, key in keys_by_kid:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
        keys.append({**jwk, "kid": kid, "use": "sig", "alg": "RS256"})
    return {"keys": keys}


class Idp:
    """Một 'Zitadel giả': giữ khoá riêng, ký token, và đưa JWKS/userinfo cho OidcVerifier."""

    def __init__(self) -> None:
        self.key = new_key()
        self.kid = KID
        self.fetches = 0
        self.userinfo_calls = 0
        self.userinfo_reply: dict | None = None  # None -> userinfo trả lỗi token không còn hiệu lực
        self.now = 1000.0  # đồng hồ giả cho KeyStore / cache userinfo

    def fetch_jwks(self) -> dict:
        self.fetches += 1
        return jwks_of((self.kid, self.key))

    def fetch_userinfo(self, token: str) -> dict:
        from app.auth.oidc import OidcError

        self.userinfo_calls += 1
        if self.userinfo_reply is None:
            raise OidcError("Token không còn hiệu lực")
        return self.userinfo_reply

    def verifier(self) -> OidcVerifier:
        clock = lambda: self.now  # noqa: E731
        return OidcVerifier(
            issuer=ISSUER,
            project_id=PROJECT_ID,
            keys=KeyStore(self.fetch_jwks, clock=clock),
            userinfo=self.fetch_userinfo,
            clock=clock,
        )

    def token(
        self,
        *,
        email: str | None = "binh.le@test.example",
        sub: str = "u-1",
        key=None,
        kid: str | None = None,
        **override,
    ) -> str:
        """Token hợp lệ; truyền `iss=`, `aud=`, `exp=`... để làm hỏng một thứ. None = bỏ claim."""
        claims = {
            "iss": ISSUER,
            "aud": [PROJECT_ID, "client-portal"],
            "sub": sub,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
        }
        if email is not None:
            claims.update(email=email, email_verified=True)
        claims.update(override)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, key or self.key, algorithm="RS256", headers={"kid": kid or self.kid})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
