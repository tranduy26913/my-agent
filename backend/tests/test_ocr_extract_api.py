"""Endpoint /api/ocr/schemas và /api/ocr/extract: quyền, mã lỗi, ghi vết. OCR và LLM đều giả, DB giả."""

import pytest
from fastapi.testclient import TestClient

from app.api import ocr as ocr_api
from app.api.deps import UserInfo, get_current_user, get_db
from app.config import settings
from app.main import create_app
from app.ocr import extract
from app.ocr.engines import ENGINES
from app.ocr.engines.fake import FakeEngine
from tests.test_ocr_extract import EMP, OCR, BrokenLLM, StubLLM, llm_raw
from tests.test_ocr_service import png_bytes

USER = UserInfo(7, "binh.le", "staff", "Kinh doanh", "Lê Văn Bình")


class StubDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


@pytest.fixture
def env(monkeypatch):
    eng = FakeEngine(text=OCR["NV018"])
    monkeypatch.setitem(ENGINES, "fake", lambda: eng)
    monkeypatch.setattr(settings, "ocr_engine", "fake")
    monkeypatch.setattr(ocr_api, "_employee_lookup", lambda db: EMP.get)  # không cần bảng employees
    monkeypatch.setattr(extract, "get_extract_llm", lambda: StubLLM(llm_raw("NV018")))
    app = create_app()
    db = StubDb()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: USER
    return TestClient(app), db, eng


def post(client, name="phieu-mat.png", **params):
    return client.post("/api/ocr/extract", params=params, files={"file": (name, png_bytes(), "image/png")})


def test_schemas(env):
    client, _, _ = env
    body = client.get("/api/ocr/schemas").json()
    assert [s["id"] for s in body] == ["cong-tac-phi"] and "08/2025/QĐ-SVT" in body[0]["description"]


def test_extract_nv018_end_to_end(env):
    client, db, _ = env
    r = post(client)
    assert r.status_code == 200
    body = r.json()
    assert body["needs_review"] is True and body["llm_model"] == "local:stub" and body["engine"] == "fake"
    errors = {f["code"] for f in body["findings"] if f["severity"] == "error"}
    assert errors == {"khach_san_vuot_dinh_muc", "taxi_vuot_dinh_muc", "ngoai_danh_muc", "quyet_toan_tre"}
    assert body["data"]["ma_nv"] == "NV018" and len(body["data"]["cac_khoan"]) == 5
    over = {f["code"]: f["over_amount"] for f in body["findings"] if f["over_amount"]}
    assert over["khach_san_vuot_dinh_muc"] == 750_000

    kinds = {type(o).__name__: o for o in db.added}
    audit, usage = kinds["AuditLog"], kinds["UsageLog"]
    assert audit.event == "ocr_extract" and audit.user_id == USER.id
    assert audit.detail["errors"] == 4 and audit.detail["needs_review"] is True
    assert usage.purpose == "ocr-extract" and usage.model == "local:stub" and usage.cost_usd == 0
    # riêng tư: vết không chứa tên file, nội dung phiếu hay số tiền
    dump = str(audit.detail)
    assert "phieu-mat" not in dump and "Phương" not in dump and "4350000" not in dump


def test_extract_schema_la_404(env):
    client, db, _ = env
    assert post(client, schema_id="khong-co").status_code == 404
    assert db.added == []


def test_extract_loi_khong_ghi_vet_thanh_cong(env, monkeypatch):
    client, db, _ = env
    monkeypatch.setattr(extract, "get_extract_llm", lambda: BrokenLLM())
    r = post(client)
    assert r.status_code == 502 and "10.0.0.5" not in r.text
    assert db.added == []


def test_extract_file_gia_mao_va_qua_lon(env, monkeypatch):
    client, db, _ = env
    bad = client.post("/api/ocr/extract", files={"file": ("x.png", b"MZ\x90\x00 chay-di", "image/png")})
    assert bad.status_code == 400
    monkeypatch.setattr(settings, "ocr_max_mb", 0.0001)
    big = client.post("/api/ocr/extract", files={"file": ("x.png", png_bytes((300, 300)), "image/png")})
    assert big.status_code == 413
    assert db.added == []


def test_extract_provider_fake_tra_503(env, monkeypatch):
    client, _, _ = env
    monkeypatch.undo()  # bỏ patch get_extract_llm
    monkeypatch.setitem(ENGINES, "fake", lambda: FakeEngine(text=OCR["NV018"]))
    monkeypatch.setattr(settings, "ocr_engine", "fake")
    monkeypatch.setattr(ocr_api, "_employee_lookup", lambda db: EMP.get)
    monkeypatch.setattr(settings, "llm_provider", "fake")
    assert post(client).status_code == 503


def test_chua_dang_nhap():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: StubDb()
    c = TestClient(app)
    assert c.get("/api/ocr/schemas").status_code == 401
    assert c.post("/api/ocr/extract", files={"file": ("a.png", png_bytes(), "image/png")}).status_code == 401
