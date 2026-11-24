"""/api/ocr bằng token Zitadel tự ký (tests/oidc_testkit.py); bảng employees nằm trong transaction rollback.

OCR không còn nhận JWT HS256 cũ: người dùng là nhân viên (employees), id ghi vào audit/usage là employees.id.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_db
from app.auth.oidc import get_verifier
from app.config import settings
from app.main import create_app
from app.models import UsageLog
from app.ocr.engines import ENGINES
from app.ocr.engines.fake import FakeEngine
from tests.kb_testkit import _kb_db, add_employee, audit_since_start  # noqa: F401  (_kb_db = fixture kb_db)
from tests.oidc_testkit import Idp, bearer
from tests.test_ocr_service import png_bytes

STAFF = "test.ocr@test.example"


@pytest.fixture(name="idp")
def _idp():
    return Idp()


@pytest.fixture(name="emp")
def _emp(kb_db):
    add_employee(kb_db, "TEST-O2", "test.ocr.cu@test.example", roles=["employee"], status="da-nghi-viec")
    return add_employee(kb_db, "TEST-O1", STAFF, department="KD", roles=["employee"])


@pytest.fixture(name="client")
def _client(kb_db, idp, emp, monkeypatch):
    monkeypatch.setitem(ENGINES, "fake", lambda: FakeEngine())
    monkeypatch.setattr(settings, "ocr_engine", "fake")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = idp.verifier
    return TestClient(app, raise_server_exceptions=False)


def test_engines_voi_token_zitadel(client, idp):
    r = client.get("/api/ocr/engines", headers=bearer(idp.token(email=STAFF)))
    assert r.status_code == 200 and r.json()["default"] == "fake"


def test_khong_token_401(client):
    assert client.get("/api/ocr/engines").status_code == 401
    assert client.get("/api/ocr/jobs").status_code == 401


def test_jwt_cu_hs256_khong_con_dung_duoc(client):
    import jwt

    legacy = jwt.encode({"sub": "1", "role": "admin"}, "k" * 32, algorithm="HS256")
    assert client.get("/api/ocr/engines", headers=bearer(legacy)).status_code == 401


def test_khong_co_trong_danh_ba_hoac_da_nghi_403(client, idp):
    for email in ("la@test.example", "test.ocr.cu@test.example"):
        assert client.get("/api/ocr/engines", headers=bearer(idp.token(email=email))).status_code == 403


def test_recognize_ghi_vet_theo_employee_id(client, idp, kb_db, emp):
    mine = (UsageLog.user_id == emp.id, UsageLog.purpose == "ocr")
    uses = select(func.count()).select_from(UsageLog).where(*mine)
    before = kb_db.scalar(uses)
    r = client.post(
        "/api/ocr/recognize",
        headers=bearer(idp.token(email=STAFF)),
        files={"file": ("a.png", png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    (row,) = audit_since_start(kb_db, "ocr_run")
    assert row.user_id == emp.id and row.detail["actor"] == STAFF
    assert "a.png" not in str(row.detail)  # không ghi tên file
    assert kb_db.scalar(uses) == before + 1
