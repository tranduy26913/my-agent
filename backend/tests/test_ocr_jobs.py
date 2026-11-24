"""Job OCR bất đồng bộ (ADR-005). Dùng SQLite + engine giả: không cần Postgres, Tesseract hay GPU."""

import threading
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import UserInfo, get_db, get_ocr_user
from app.config import settings
from app.main import create_app
from app.models import OcrJob
from app.ocr import jobs
from app.ocr.engines import ENGINES
from app.ocr.engines.fake import FakeEngine
from tests.test_ocr_service import pdf_scan_only, pdf_text_layer, png_bytes

A = UserInfo(1, "binh.le", "staff", "Kinh doanh", "Lê Văn Bình")
B = UserInfo(2, "ha.pham", "staff", "Nhân sự", "Phạm Hà")
ADMIN = UserInfo(9, "quan.tri", "admin", "CNTT", "Quản trị")


class HookEngine(FakeEngine):
    """Engine giả cho phép chèn hành vi (xóa job, chờ cổng, ném lỗi) vào mỗi lần OCR."""

    def __init__(self):
        super().__init__()
        self.hook = None

    def recognize(self, image, **kw) -> str:
        if self.hook:
            self.hook()
        return super().recognize(image, **kw)


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'jobs.db'}", connect_args={"check_same_thread": False})
    OcrJob.__table__.create(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    audit, usage = [], []
    eng = HookEngine()

    monkeypatch.setattr(jobs, "session_factory", factory)
    monkeypatch.setattr(jobs, "_audit", lambda db, uid, event, detail: audit.append((uid, event, detail)))
    monkeypatch.setattr(jobs, "_usage", lambda db, user, engine_name: usage.append((user.id, engine_name)))
    monkeypatch.setattr(jobs, "_submit", lambda fn, *args: fn(*args))  # chạy đồng bộ cho dễ kiểm tra
    monkeypatch.setitem(ENGINES, "fake", lambda: eng)
    monkeypatch.setattr(settings, "ocr_engine", "fake")

    app = create_app()

    def db_override():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    who = {"user": A}
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_ocr_user] = lambda: who["user"]
    return SimpleNamespace(
        client=TestClient(app), factory=factory, audit=audit, usage=usage, eng=eng, who=who,
        monkeypatch=monkeypatch,
    )


def post(env, data: bytes, name="a.pdf", mime="application/pdf", **params):
    return env.client.post("/api/ocr/jobs", params=params, files={"file": (name, data, mime)})


def rows(env) -> list:
    with env.factory() as db:
        return list(db.scalars(select(OcrJob)))


# ---------- đường đi chính ----------

def test_tao_job_tra_202_va_chay_xong(env):
    r = post(env, pdf_scan_only(2), name="bien-ban-mat.pdf")
    assert r.status_code == 202
    body = r.json()
    assert r.headers["location"] == f"/api/ocr/jobs/{body['job_id']}"
    assert body["status"] == "queued" and body["engine"] == "fake"

    got = env.client.get(f"/api/ocr/jobs/{body['job_id']}").json()
    assert got["status"] == "done" and got["kind"] == "pdf"
    assert got["pages_done"] == got["pages_total"] == 2 and got["ocr_pages"] == 2
    assert [p["source"] for p in got["pages"]] == ["ocr", "ocr"]
    assert got["pages"][0]["text"] == "VAN BAN GIA" and got["finished_at"] is not None


def test_ghi_vet_va_rieng_tu(env):
    job_id = post(env, pdf_scan_only(1), name="bien-ban-mat.pdf").json()["job_id"]
    (uid, event, detail), = env.audit
    assert (uid, event) == (A.id, "ocr_run")
    assert detail["async"] is True and detail["job_id"] == job_id and detail["ocr_pages"] == 1
    assert "bien-ban-mat" not in str(env.audit) and "VAN BAN GIA" not in str(env.audit)
    assert env.usage == [(A.id, "fake")]
    # DB cũng không có tên file
    row = rows(env)[0]
    assert "bien-ban-mat" not in str(row.__dict__)


def test_job_cho_phep_nhieu_trang_hon_request_dong_bo(env, monkeypatch):
    monkeypatch.setattr(settings, "ocr_max_pages", 2)
    monkeypatch.setattr(settings, "ocr_job_max_pages", 5)
    pdf = {"file": ("a.pdf", pdf_text_layer(4), "application/pdf")}
    sync = env.client.post("/api/ocr/recognize", files=pdf)
    assert sync.status_code == 422
    job_id = post(env, pdf_text_layer(4)).json()["job_id"]
    got = env.client.get(f"/api/ocr/jobs/{job_id}").json()
    assert got["status"] == "done" and len(got["pages"]) == 4


def test_job_that_su_bat_dong_bo(env):
    """Không chạy inline: POST trả ngay trong khi engine còn đang bị giữ, rồi poll tới khi xong."""
    env.monkeypatch.undo()  # bỏ patch _submit inline; dựng lại phần còn lại
    env.monkeypatch.setattr(jobs, "session_factory", env.factory)
    env.monkeypatch.setattr(jobs, "_audit", lambda *a: None)
    env.monkeypatch.setattr(jobs, "_usage", lambda *a: None)
    env.monkeypatch.setitem(ENGINES, "fake", lambda: env.eng)
    env.monkeypatch.setattr(settings, "ocr_engine", "fake")
    gate = threading.Event()
    env.eng.hook = lambda: gate.wait(5)
    try:
        job_id = post(env, pdf_scan_only(1)).json()["job_id"]
        time.sleep(0.2)
        assert env.client.get(f"/api/ocr/jobs/{job_id}").json()["status"] in {"queued", "running"}
        gate.set()
        for _ in range(50):
            got = env.client.get(f"/api/ocr/jobs/{job_id}").json()
            if got["status"] == "done":
                break
            time.sleep(0.1)
        assert got["status"] == "done"
    finally:
        gate.set()
        if jobs._executor:
            jobs._executor.shutdown(wait=True)
            jobs._executor = None


# ---------- lỗi ----------

def test_engine_chua_san_sang_thanh_failed(env):
    env.eng.is_available = False
    job_id = post(env, pdf_scan_only(1)).json()["job_id"]
    got = env.client.get(f"/api/ocr/jobs/{job_id}").json()
    assert got["status"] == "failed" and "chưa sẵn sàng" in got["error"] and got["pages"] is None
    assert [e for _, e, _ in env.audit] == ["ocr_job_failed"]


def test_loi_bat_ngo_khong_lo_chi_tiet(env):
    def boom():
        raise RuntimeError("duong dan noi bo C:\\secret")

    env.eng.hook = boom
    job_id = post(env, pdf_scan_only(1)).json()["job_id"]
    got = env.client.get(f"/api/ocr/jobs/{job_id}").json()
    assert got["status"] == "failed" and "secret" not in got["error"]


def test_tu_choi_ngay_khong_tao_job(env, monkeypatch):
    assert post(env, b"MZ\x90\x00 chay-di").status_code == 400
    assert post(env, png_bytes(), engine="khong-co").status_code == 400
    monkeypatch.setattr(settings, "ocr_job_max_mb", 0.0001)
    assert post(env, png_bytes((300, 300))).status_code == 413
    assert rows(env) == []


def test_chua_dang_nhap(env):
    env.client.app.dependency_overrides.pop(get_ocr_user)
    png = {"file": ("a.png", png_bytes(), "image/png")}
    assert env.client.post("/api/ocr/jobs", files=png).status_code == 401
    assert env.client.get("/api/ocr/jobs").status_code == 401


# ---------- hạn mức ----------

def test_han_muc_moi_nguoi_va_toan_he_thong(env, monkeypatch):
    monkeypatch.setattr(jobs, "_submit", lambda fn, *args: None)  # job nằm yên ở trạng thái queued
    monkeypatch.setattr(settings, "ocr_job_max_active_per_user", 2)
    monkeypatch.setattr(settings, "ocr_job_queue_max", 3)
    assert post(env, png_bytes(), mime="image/png").status_code == 202
    assert post(env, png_bytes(), mime="image/png").status_code == 202
    assert post(env, png_bytes(), mime="image/png").status_code == 429  # A đã đủ 2 job
    env.who["user"] = B
    assert post(env, png_bytes(), mime="image/png").status_code == 202  # B còn chỗ (toàn hệ thống 3/3)
    assert post(env, png_bytes(), mime="image/png").status_code == 429  # hàng đợi chung đầy


def test_job_xong_thi_giai_phong_han_muc(env, monkeypatch):
    monkeypatch.setattr(settings, "ocr_job_max_active_per_user", 1)
    for _ in range(3):  # chạy inline nên mỗi job xong ngay -> luôn còn chỗ
        assert post(env, pdf_text_layer(1)).status_code == 202


# ---------- quyền ----------

def test_chi_chu_job_va_admin_xem_duoc(env):
    job_id = post(env, pdf_text_layer(1)).json()["job_id"]
    url = f"/api/ocr/jobs/{job_id}"

    env.who["user"] = B
    assert env.client.get(url).status_code == 404  # không lộ là job có tồn tại
    assert env.client.delete(url).status_code == 404
    assert env.client.get("/api/ocr/jobs").json() == []

    env.audit.clear()
    env.who["user"] = ADMIN
    assert env.client.get(url).status_code == 200
    (uid, event, detail), = env.audit
    assert (uid, event) == (ADMIN.id, "ocr_job_view") and detail["owner_id"] == A.id
    assert env.client.delete(url).status_code == 404  # admin xem được nhưng không xóa hộ

    env.who["user"] = A
    assert env.client.get(url).status_code == 200 and len(rows(env)) == 1


def test_chu_job_xem_khong_bi_ghi_vet_admin(env):
    job_id = post(env, pdf_text_layer(1)).json()["job_id"]
    env.audit.clear()
    env.client.get(f"/api/ocr/jobs/{job_id}")
    assert env.audit == []


def test_admin_xem_that_bai_khi_ghi_vet_loi_thi_khong_tra_noi_dung(env, monkeypatch):
    job_id = post(env, pdf_text_layer(1)).json()["job_id"]

    def broken(*_a):
        raise OSError("audit hỏng")

    monkeypatch.setattr(jobs, "_audit", broken)
    env.who["user"] = ADMIN
    client = TestClient(env.client.app, raise_server_exceptions=False)
    r = client.get(f"/api/ocr/jobs/{job_id}")
    assert r.status_code == 500 and "VAN BAN" not in r.text and "Trang" not in r.text


# ---------- danh sách / xóa / hết hạn ----------

def test_danh_sach_chi_cua_minh_moi_nhat_truoc_va_khong_co_van_ban(env):
    first = post(env, pdf_text_layer(1)).json()["job_id"]
    second = post(env, pdf_text_layer(1)).json()["job_id"]
    env.who["user"] = B
    post(env, pdf_text_layer(1))
    env.who["user"] = A
    listing = env.client.get("/api/ocr/jobs").json()
    assert [j["job_id"] for j in listing] == [second, first]
    assert all("pages" not in j for j in listing)


def test_xoa_job(env):
    job_id = post(env, pdf_text_layer(1)).json()["job_id"]
    assert env.client.delete(f"/api/ocr/jobs/{job_id}").status_code == 204
    assert env.client.get(f"/api/ocr/jobs/{job_id}").status_code == 404
    assert rows(env) == []


def test_xoa_job_dang_chay_thi_worker_dung(env):
    """Người dùng hủy giữa chừng: worker thấy dòng mất sau trang hiện tại và không OCR thêm trang nào."""
    job_id_box = []

    def cancel_during_first_page():
        with env.factory() as db:
            db.delete(db.get(OcrJob, job_id_box[0]))
            db.commit()

    env.eng.hook = cancel_during_first_page
    # chạy inline nên job_id chưa có trước khi _submit -> lấy qua patch _submit
    def submit(fn, jid, *args):
        job_id_box.append(jid)
        fn(jid, *args)

    env.monkeypatch.setattr(jobs, "_submit", submit)
    post(env, pdf_scan_only(3))
    assert env.eng.calls == 1  # chỉ trang 1; trang 2, 3 không chạy
    assert rows(env) == [] and env.audit == [] and env.usage == []


def test_het_han_coi_nhu_khong_ton_tai_va_duoc_don(env):
    job_id = post(env, pdf_text_layer(1)).json()["job_id"]
    with env.factory() as db:
        db.get(OcrJob, job_id).expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert env.client.get(f"/api/ocr/jobs/{job_id}").status_code == 404
    assert env.client.get("/api/ocr/jobs").json() == []
    assert len(rows(env)) == 1  # còn xác trong DB cho tới lần dọn
    post(env, pdf_text_layer(1))  # tạo job mới sẽ dọn job hết hạn
    assert job_id not in [r.id for r in rows(env)]


def test_ttl_theo_cau_hinh(env, monkeypatch):
    monkeypatch.setattr(settings, "ocr_job_ttl_days", 2)
    body = post(env, pdf_text_layer(1)).json()
    created = datetime.fromisoformat(body["created_at"])
    expires = datetime.fromisoformat(body["expires_at"])
    assert expires - created == timedelta(days=2)


# ---------- khởi động lại ----------

def test_job_bi_gian_doan_duoc_danh_dau_failed(env):
    now = datetime.now(UTC)
    with env.factory() as db:
        for jid, status in (("q", "queued"), ("r", "running"), ("d", "done")):
            db.add(OcrJob(id=jid, user_id=1, status=status, engine="fake", created_at=now,
                          expires_at=now + timedelta(days=1)))
        db.commit()
        assert jobs.recover_interrupted(db) == 2
    by_id = {r.id: r for r in rows(env)}
    assert by_id["q"].status == by_id["r"].status == "failed" and "khởi động lại" in by_id["r"].error
    assert by_id["d"].status == "done"
