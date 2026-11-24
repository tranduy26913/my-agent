"""Router /api/ocr: quyền, giới hạn, mã lỗi, ghi vết. Không cần Postgres (DB giả)."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import UserInfo, get_db, get_ocr_user
from app.config import settings
from app.main import create_app
from app.ocr.engines import ENGINES
from app.ocr.engines.fake import FakeEngine
from tests.test_ocr_service import pdf_scan_only, pdf_text_layer, png_bytes


class StubDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


@pytest.fixture
def env(monkeypatch):
    eng = FakeEngine()
    monkeypatch.setitem(ENGINES, "fake", lambda: eng)
    monkeypatch.setattr(settings, "ocr_engine", "fake")
    app = create_app()
    db = StubDb()
    app.dependency_overrides[get_db] = lambda: db
    user = UserInfo(7, "binh.le", "staff", "Kinh doanh", "Lê Văn Bình")
    app.dependency_overrides[get_ocr_user] = lambda: user
    return TestClient(app), db, eng


def up(name: str, data: bytes, mime: str):
    return {"file": (name, data, mime)}


def test_chua_dang_nhap_bi_chan():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: StubDb()
    c = TestClient(app)
    assert c.get("/api/ocr/engines").status_code == 401
    assert c.post("/api/ocr/recognize", files=up("a.png", png_bytes(), "image/png")).status_code == 401


def test_engines(env):
    c, _, _ = env
    body = c.get("/api/ocr/engines").json()
    assert body["default"] == "fake"
    by_name = {e["name"]: e["available"] for e in body["engines"]}
    assert by_name["fake"] is True and "tesseract" in by_name


def test_recognize_anh_ok_va_ghi_vet(env):
    c, db, eng = env
    r = c.post("/api/ocr/recognize", files=up("bien-ban-mat.png", png_bytes(), "image/png"))
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "fake" and body["kind"] == "image" and body["ocr_pages"] == 1
    page = body["pages"][0]
    assert (page["page"], page["text"], page["source"]) == (1, "VAN BAN GIA", "ocr")

    kinds = {type(o).__name__: o for o in db.added}
    audit, usage = kinds["AuditLog"], kinds["UsageLog"]
    assert audit.event == "ocr_run" and audit.user_id == 7
    assert audit.detail["ocr_pages"] == 1 and audit.detail["engine"] == "fake"
    assert usage.purpose == "ocr" and usage.cost_usd == 0 and usage.department == "Kinh doanh"
    # riêng tư: không có tên file hay nội dung văn bản trong vết
    dump = str(audit.detail) + str(usage.__dict__)
    assert "bien-ban-mat" not in dump and "VAN BAN GIA" not in dump


def test_recognize_pdf_chon_trang(env):
    c, _, _ = env
    pdf = up("a.pdf", pdf_text_layer(3), "application/pdf")
    r = c.post("/api/ocr/recognize", params={"pages": "2"}, files=pdf)
    assert r.status_code == 200
    assert [p["page"] for p in r.json()["pages"]] == [2]
    assert r.json()["pages"][0]["source"] == "text-layer"


def test_ma_loi(env):
    c, _, eng = env
    post = c.post
    exe = up("x.png", b"MZ\x90\x00 chay-di", "image/png")
    assert post("/api/ocr/recognize", files=exe).status_code == 400
    assert post("/api/ocr/recognize", params={"engine": "khong-co"},
                files=up("a.png", png_bytes(), "image/png")).status_code == 400
    assert post("/api/ocr/recognize", params={"pages": "9"},
                files=up("a.pdf", pdf_text_layer(2), "application/pdf")).status_code == 422
    eng.is_available = False
    r = post("/api/ocr/recognize", files=up("a.pdf", pdf_scan_only(), "application/pdf"))
    assert r.status_code == 503


def test_file_qua_lon_413(env, monkeypatch):
    c, db, _ = env
    monkeypatch.setattr(settings, "ocr_max_mb", 0.0001)
    r = c.post("/api/ocr/recognize", files=up("a.png", png_bytes((300, 300)), "image/png"))
    assert r.status_code == 413
    assert db.added == []  # bị từ chối thì không ghi vết "đã chạy OCR"


def test_loi_khong_ghi_vet_chay(env):
    c, db, _ = env
    c.post("/api/ocr/recognize", files=up("x.png", b"khong-phai-anh", "image/png"))
    assert db.added == []
