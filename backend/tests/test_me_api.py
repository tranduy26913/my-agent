"""GET /api/me bằng token Zitadel tự ký (tests/oidc_testkit.py), bảng employees trong transaction rollback."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.auth.oidc import get_verifier
from app.main import create_app
from tests.kb_testkit import _kb_db, add_employee  # noqa: F401  (_kb_db = fixture kb_db)
from tests.oidc_testkit import Idp, bearer


@pytest.fixture(name="idp")
def _idp():
    return Idp()


@pytest.fixture(name="client")
def _client(kb_db, idp):
    add_employee(
        kb_db,
        "TEST-M1",
        "test.me@test.example",
        department="HCNS",
        roles=["manager", "admin"],
        name="Người Thử Me",
    )
    add_employee(kb_db, "TEST-M2", "test.cu@test.example", roles=["employee"], status="da-nghi-viec")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = idp.verifier
    return TestClient(app, raise_server_exceptions=False)


def test_tra_ve_ho_so_tu_employees_khong_tu_token(client, idp):
    r = client.get(
        "/api/me", headers=bearer(idp.token(email="Test.Me@test.example", roles={"superadmin": {}}))
    )
    assert r.status_code == 200
    assert r.json() == {
        "email": "test.me@test.example",
        "name": "Người Thử Me",
        "department": "HCNS",
        "roles": ["admin", "manager"],
    }


def test_khong_token_401(client):
    assert client.get("/api/me").status_code == 401


def test_chua_co_trong_danh_ba_403(client, idp):
    r = client.get("/api/me", headers=bearer(idp.token(email="la@test.example")))
    assert r.status_code == 403 and "danh bạ" in r.json()["detail"]


def test_nghi_viec_403(client, idp):
    assert client.get("/api/me", headers=bearer(idp.token(email="test.cu@test.example"))).status_code == 403


def test_jwt_cu_hs256_khong_dung_duoc_o_day(client):
    """/api/me chỉ nhận token Zitadel."""
    import jwt

    legacy = jwt.encode({"sub": "1", "role": "admin"}, "k" * 32, algorithm="HS256")
    assert client.get("/api/me", headers=bearer(legacy)).status_code == 401
