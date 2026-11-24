"""Client Zitadel: kiểm bằng httpx.MockTransport, không cần Zitadel đang chạy."""

import json

import httpx
import pytest

from app.auth.zitadel_admin import ZitadelAdmin, ZitadelError, split_name, temp_password


def test_split_name():
    assert split_name("Phạm Đức Long") == ("Long", "Phạm Đức")
    assert split_name("Long") == ("Long", "-")


def test_temp_password_meets_policy():
    for _ in range(50):
        pw = temp_password()
        assert len(pw) >= 10
        assert any(c.isupper() for c in pw) and any(c.islower() for c in pw)
        assert any(c.isdigit() for c in pw) and any(not c.isalnum() for c in pw)


def _client(handler):
    return ZitadelAdmin("http://z", "tok", host="auth.example", transport=httpx.MockTransport(handler))


def test_create_human_sends_verified_email_and_forces_password_change():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"], seen["auth"], seen["host"] = (
            req.url.path,
            req.headers["authorization"],
            req.headers["host"],
        )
        seen["body"] = json.loads(req.content)
        return httpx.Response(201, json={"userId": "42"})

    uid = _client(handler).create_human(
        username="a@x", email="a@x", full_name="Lê Văn Bình", password="Pw1!pw1!pw"
    )
    assert uid == "42" and seen["path"] == "/v2/users/human"
    assert seen["auth"] == "Bearer tok" and seen["host"] == "auth.example"
    body = seen["body"]
    assert body["email"] == {"email": "a@x", "isVerified": True}
    assert body["password"]["changeRequired"] is True
    assert body["profile"]["givenName"] == "Bình" and body["profile"]["familyName"] == "Lê Văn"


def test_find_by_username_and_errors():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/v2/users":
            name = json.loads(req.content)["queries"][0]["userNameQuery"]["userName"]
            if name == "no@x":
                return httpx.Response(200, json={"result": []})
            return httpx.Response(
                200, json={"result": [{"userId": "7", "username": "a@x", "state": "USER_STATE_INACTIVE"}]}
            )
        return httpx.Response(403, text="no")

    z = _client(handler)
    assert z.find_by_username("no@x") is None
    u = z.find_by_username("a@x")
    assert u and u.id == "7" and u.state == "USER_STATE_INACTIVE"
    with pytest.raises(ZitadelError):
        z.deactivate("7")
