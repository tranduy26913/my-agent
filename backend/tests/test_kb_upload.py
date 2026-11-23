"""POST /api/kb/documents (bước 3): kiểm tra tệp, các nhánh nạp, 409/413/415/422, thay thế bản cũ, giao dịch.

Chạy trên Postgres thật trong transaction rollback (tests/kb_testkit.py). Embedding dùng HashEmbedder
(không tải model e5 ~2 GB) và upload_dir trỏ vào thư mục tạm của pytest.
"""

import io
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import UserInfo, get_current_user, get_db
from app.config import settings
from app.main import create_app
from app.models import AuditLog, Document
from app.rag import kb_service
from app.rag.embeddings import get_embedder
from app.rag.kb_service import KbError, check_file, derive_doc_id
from tests.kb_testkit import _kb_db, add_doc, add_user  # noqa: F401  (_kb_db = fixture kb_db)

URL = "/api/kb/documents"
MD = "text/markdown"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

FRONTMATTER_MD = """---
doc_id: TEST-UP-001
tieu_de: Quy chế thử nghiệm
so_hieu: 99/2026/TEST
loai: quy-che
phong_ban_so_huu: HCNS
pham_vi_truy_cap: cong-khai
hieu_luc_tu: 2026-03-01
{extra}---

# Quy chế thử nghiệm

## Điều 1. Phạm vi
Quy chế này áp dụng cho mọi nhân viên của công ty trong thời gian thử việc.

## Điều 2. Nội dung
Nhân viên được nghỉ phép năm theo quy định hiện hành của pháp luật lao động.
"""
PLAIN_MD = "# Biên bản họp\n\n## Mục 1\nThống nhất lịch triển khai dự án trong quý tới của phòng.\n"
META = {"docType": "bien-ban-hop", "department": "DA", "visibility": "phong-ban",
        "allowedDepartments": ["DA", "BGD"], "allowedRoles": [], "classified": False}


def make_pdf(pages: int = 2) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for i in range(pages):
        text = f"Trang {i + 1}. " + "Noi dung quy dinh nghi phep nam cong ty. " * 3
        doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


def make_docx() -> bytes:
    import docx

    d = docx.Document()
    d.add_paragraph("Hướng dẫn sử dụng dịch vụ CNTT nội bộ. " * 5)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


@pytest.fixture
def env(kb_db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "embedding_provider", "hash")
    get_embedder.cache_clear()
    admin = add_user(kb_db)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_current_user] = lambda: UserInfo(admin.id, "test.admin", "admin", "CNTT")
    yield TestClient(app, raise_server_exceptions=False), kb_db, admin, tmp_path / "uploads"
    get_embedder.cache_clear()


def post(c, name, data, mime=None, meta=None):
    kw = {"data": {"meta": json.dumps(meta)}} if meta is not None else {}
    return c.post(URL, files={"file": (name, data, mime)}, **kw)


def saved_files(folder):
    return sorted(p.name for p in folder.glob("*")) if folder.exists() else []


def audit(db, event="kb_upload"):
    return db.execute(select(AuditLog).where(AuditLog.event == event)).scalars().all()


# ---------------------------------------------------------------- check_file / derive_doc_id (thuần)

@pytest.mark.parametrize("name,mime,data,status", [
    ("a.exe", "application/octet-stream", b"MZ", 415),  # đuôi không nhận
    ("a", None, b"x", 415),  # không có đuôi
    ("a.pdf", "image/png", b"%PDF-1.7", 415),  # MIME khai báo không khớp đuôi
    ("a.png", "image/png", b"MZ\x90\x00 chay-di", 415),  # đuôi + MIME đúng nhưng ruột không phải PNG
    ("a.pdf", PDF, b"", 422),  # rỗng
])
def test_check_file_tu_choi(name, mime, data, status):
    with pytest.raises(KbError) as e:
        check_file(name, mime, data)
    assert e.value.status_code == status


@pytest.mark.parametrize("name,mime,data,ext", [
    ("a.MD", "text/plain; charset=utf-8", b"# x", ".md"),
    ("a.md", "", b"# x", ".md"),  # trình duyệt không khai MIME
    ("a.md", "application/octet-stream", b"# x", ".md"),
    ("a.pdf", PDF, b"%PDF-1.7 ...", ".pdf"),
    ("b.docx", DOCX, b"PK\x03\x04...", ".docx"),
    ("c.jpg", "image/jpeg", b"\xff\xd8\xff\xe0", ".jpg"),
])
def test_check_file_chap_nhan(name, mime, data, ext):
    assert check_file(name, mime, data) == ext


def test_derive_doc_id():
    sha = "ab" * 32
    assert derive_doc_id("SVT-TB-018-dieu-chinh-gio-lam.pdf", sha) == "SVT-TB-018"
    assert derive_doc_id("de-nghi-thanh-toan.png", sha) == "UPLOAD-abababababab"
    assert derive_doc_id("", sha).startswith("UPLOAD-")


# ---------------------------------------------------------------- quyền

def test_upload_can_dang_nhap_va_admin():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: None
    files = {"file": ("a.md", b"# x", MD)}
    assert TestClient(app).post(URL, files=files).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: UserInfo(2, "nv", "staff", "KD")
    assert TestClient(app).post(URL, files=files).status_code == 403


# ---------------------------------------------------------------- nhánh .md có frontmatter

def test_md_frontmatter_nap_dung_va_ghi_vet(env):
    c, db, admin, folder = env
    r = post(c, "quy-che-thu.md", FRONTMATTER_MD.format(extra="").encode(), MD)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["docId"] == "TEST-UP-001" and body["title"] == "Quy chế thử nghiệm"
    assert body["soHieu"] == "99/2026/TEST" and body["effectiveFrom"] == "2026-03-01"
    assert body["uploadedBy"] == "test.admin" and body["chunkCount"] >= 2
    assert body["fileKind"] == "md" and body["source"].endswith(".md")
    assert len(saved_files(folder)) == 1 and saved_files(folder)[0].endswith(".md")  # bản gốc đã lưu

    logs = [a for a in audit(db) if a.detail["doc_id"] == "TEST-UP-001"]
    assert len(logs) == 1 and logs[0].user_id == admin.id
    assert "quy-che-thu" not in str(logs[0].detail)  # riêng tư: không ghi tên tệp
    hist = c.get(f"{URL}/TEST-UP-001").json()["history"]
    assert [h["text"] for h in hist] == ["Nạp tài liệu vào kho"] and hist[0]["by"] == "test.admin"


def test_md_co_bom_van_nhan_frontmatter(env):
    c, *_ = env
    r = post(c, "a.md", b"\xef\xbb\xbf" + FRONTMATTER_MD.format(extra="").encode(), MD)
    assert r.status_code == 201, r.text


def test_nap_trung_tra_409_khong_them_gi(env):
    c, db, _, folder = env
    data = FRONTMATTER_MD.format(extra="").encode()
    assert post(c, "a.md", data, MD).status_code == 201
    r = post(c, "a.md", data, MD)
    assert r.status_code == 409 and "TEST-UP-001" in r.text
    assert db.execute(select(Document).where(Document.doc_id == "TEST-UP-001")).scalars().all().__len__() == 1
    assert len(audit(db)) == 1 and len(saved_files(folder)) == 1  # không thêm audit, không mất tệp đã lưu


def test_trung_doc_id_noi_dung_khac_van_409(env):
    c, *_ = env
    assert post(c, "a.md", FRONTMATTER_MD.format(extra="").encode(), MD).status_code == 201
    other = FRONTMATTER_MD.format(extra="").replace("Phạm vi", "Phạm vi áp dụng").encode()
    assert post(c, "b.md", other, MD).status_code == 409


@pytest.mark.parametrize("bad", [
    PLAIN_MD,  # không có frontmatter, không meta
    "---\ndoc_id: X\n---\nthiếu tiêu đề và phạm vi",
    "---\ndoc_id: 123\ntieu_de: A\npham_vi_truy_cap: cong-khai\n---\n# A\n\nnội dung",  # doc_id là số
    "---\ndoc_id: X\ntieu_de: A\npham_vi_truy_cap: bi-mat\n---\n# A\n\nnội dung",  # phạm vi lạ
    "---\ndoc_id: [unclosed\ntieu_de: A\n---\nnội dung",  # YAML hỏng
    "---\ndoc_id: X\ntieu_de: A\npham_vi_truy_cap: cong-khai\nhieu_luc_tu: sai-ngay\n---\n# A\n\nnoi dung",
])
def test_md_frontmatter_sai_tra_422(env, bad):
    c, db, _, folder = env
    r = post(c, "a.md", bad.encode(), MD)
    assert r.status_code == 422, r.text
    assert saved_files(folder) == [] and audit(db) == []


def test_md_khong_phai_utf8_tra_422(env):
    c, *_ = env
    assert post(c, "a.md", "---\ndoc_id: X\n---\n".encode("utf-16"), MD).status_code == 422


# ---------------------------------------------------------------- nhánh meta

def test_md_khong_frontmatter_co_meta(env):
    c, db, _, _ = env
    r = post(c, "bien-ban.md", PLAIN_MD.encode(), MD, META)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["docId"].startswith("UPLOAD-") and b["title"] == "bien-ban" and b["department"] == "DA"
    assert b["visibility"] == "phong-ban" and b["allowedDepartments"] == ["DA", "BGD"]
    assert b["classified"] is False
    assert b["chunkCount"] >= 1 and b["docType"] == "bien-ban-hop"
    # UPLOAD-<sha> nên nạp lại đúng tệp đó là 409
    assert post(c, "bien-ban.md", PLAIN_MD.encode(), MD, META).status_code == 409


def test_pdf_meta_ma_tu_ten_tep_va_so_trang(env):
    c, _, _, folder = env
    meta = {**META, "title": "Thông báo giờ làm", "classified": True, "effectiveFrom": "2026-04-01"}
    r = post(c, "SVT-TB-018-dieu-chinh-gio-lam.pdf", make_pdf(2), PDF, meta)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["docId"] == "SVT-TB-018" and b["fileKind"] == "pdf" and b["title"] == "Thông báo giờ làm"
    assert b["classified"] is True and b["effectiveFrom"] == "2026-04-01" and b["ocrPages"] == 0
    assert saved_files(folder)[0].endswith(".pdf")
    pages = {ch["page"] for ch in c.get(f"{URL}/SVT-TB-018").json()["chunks"]}
    assert pages == {1, 2}


def test_docx_meta(env):
    c, *_ = env
    meta = {**META, "visibility": "cong-khai", "allowedDepartments": []}
    r = post(c, "huong-dan.docx", make_docx(), DOCX, meta)
    assert r.status_code == 201, r.text
    assert r.json()["fileKind"] == "docx"


def test_anh_scan_dem_trang_ocr(env, monkeypatch):
    c, *_ = env
    scan = ([(1, "Đề nghị thanh toán 5 triệu")], 1)  # (các trang, số trang phải OCR)
    monkeypatch.setattr(kb_service, "extract_pages", lambda data, name: scan)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 50
    r = post(c, "de-nghi.png", png, "image/png", META)
    assert r.status_code == 201, r.text
    assert (r.json()["fileKind"], r.json()["ocrPages"]) == ("image", 1)


def test_tep_hong_tra_422_khong_de_lai_gi(env):
    c, db, _, folder = env
    r = post(c, "hong.pdf", b"%PDF-1.7 khong phai pdf that", PDF, META)
    assert r.status_code == 422, r.text
    assert saved_files(folder) == [] and audit(db) == []  # tệp đã lưu được dọn lại


def test_tep_khong_co_noi_dung_tra_422(env, monkeypatch):
    c, *_ = env
    monkeypatch.setattr(kb_service, "extract_pages", lambda data, name: ([(1, "   ")], 0))
    assert post(c, "trang.pdf", b"%PDF-1.7", PDF, META).status_code == 422


def test_tep_khong_meta_tra_422(env):
    c, *_ = env
    r = post(c, "a.pdf", make_pdf(1), PDF)
    assert r.status_code == 422 and "meta" in r.text


def test_phong_ban_khong_khai_danh_sach_mac_dinh_phong_so_huu(env):
    c, *_ = env
    meta = {**META, "allowedDepartments": [], "allowedRoles": []}
    assert post(c, "a.md", PLAIN_MD.encode(), MD, meta).json()["allowedDepartments"] == ["DA"]


def test_han_che_khong_khai_gi_tra_422(env):
    c, *_ = env
    meta = {**META, "visibility": "han-che", "allowedDepartments": [], "allowedRoles": []}
    r = post(c, "a.md", PLAIN_MD.encode(), MD, meta)
    assert r.status_code == 422 and "hạn chế" in r.text


@pytest.mark.parametrize("meta_raw", [
    "{khong-phai-json",
    json.dumps({**META, "visibility": "bi-mat"}),
    json.dumps({**META, "effectiveFrom": "01/02/2026"}),
    json.dumps({**META, "department": "x" * 65}),
    json.dumps({"department": "KD", "visibility": "cong-khai"}),  # thiếu docType
])
def test_meta_sai_tra_422(env, meta_raw):
    c, db, _, folder = env
    r = c.post(URL, files={"file": ("a.md", PLAIN_MD.encode(), MD)}, data={"meta": meta_raw})
    assert r.status_code == 422, r.text
    assert saved_files(folder) == [] and audit(db) == []


# ---------------------------------------------------------------- giới hạn, định dạng

def test_qua_lon_413(env, monkeypatch):
    c, db, _, folder = env
    monkeypatch.setattr(settings, "max_upload_mb", 0.0001)
    r = post(c, "a.md", PLAIN_MD.encode() * 50, MD, META)
    assert r.status_code == 413
    assert saved_files(folder) == [] and audit(db) == []


@pytest.mark.parametrize("name,data,mime", [
    ("virus.exe", b"MZ", "application/octet-stream"),
    ("a.pdf", b"%PDF-1.7", "image/png"),
    ("gia-pdf.pdf", b"MZ\x90\x00 chay-di", PDF),
])
def test_dinh_dang_sai_415(env, name, data, mime):
    c, _, _, folder = env
    assert post(c, name, data, mime, META).status_code == 415
    assert saved_files(folder) == []


# ---------------------------------------------------------------- thay thế bản cũ (cùng transaction)

def test_supersedes_dong_ban_cu_qua_meta(env):
    c, db, _, _ = env
    add_doc(db, "TEST-OLD-001", effective_from=date(2025, 1, 1))
    meta = {**META, "supersedes": "TEST-OLD-001", "effectiveFrom": "2026-05-01"}
    r = post(c, "a.md", PLAIN_MD.encode(), MD, meta)
    assert r.status_code == 201, r.text
    new_id = r.json()["docId"]
    old = db.execute(select(Document).where(Document.doc_id == "TEST-OLD-001")).scalar_one()
    assert old.superseded_by == new_id and old.effective_to == date(2026, 5, 1)
    assert r.json()["supersedes"] == "TEST-OLD-001"


def test_supersedes_khong_keo_dai_han_cu(env):
    c, db, _, _ = env
    add_doc(db, "TEST-OLD-002", effective_to=date(2026, 1, 1))  # đã hết hạn sớm hơn ngày bản mới
    meta = {**META, "supersedes": "TEST-OLD-002", "effectiveFrom": "2026-05-01"}
    post(c, "a.md", PLAIN_MD.encode(), MD, meta)
    old = db.execute(select(Document).where(Document.doc_id == "TEST-OLD-002")).scalar_one()
    assert old.effective_to == date(2026, 1, 1)


def test_supersedes_qua_frontmatter(env):
    c, db, _, _ = env
    add_doc(db, "TEST-OLD-003")
    r = post(c, "a.md", FRONTMATTER_MD.format(extra="thay_the: TEST-OLD-003\n").encode(), MD)
    assert r.status_code == 201, r.text
    old = db.execute(select(Document).where(Document.doc_id == "TEST-OLD-003")).scalar_one()
    assert old.superseded_by == "TEST-UP-001" and old.effective_to == date(2026, 3, 1)


def test_supersedes_khong_co_ban_cu_tra_422(env):
    c, db, _, folder = env
    r = post(c, "a.md", PLAIN_MD.encode(), MD, {**META, "supersedes": "TEST-KHONG-CO"})
    assert r.status_code == 422 and "TEST-KHONG-CO" in r.text
    assert saved_files(folder) == [] and audit(db) == []


def test_supersedes_ban_da_bi_thay_boi_ban_khac_tra_409(env):
    c, db, _, _ = env
    add_doc(db, "TEST-OLD-004", superseded_by="TEST-KHAC-9", effective_to=date(2026, 2, 1))
    r = post(c, "a.md", PLAIN_MD.encode(), MD, {**META, "supersedes": "TEST-OLD-004"})
    assert r.status_code == 409
    old = db.execute(select(Document).where(Document.doc_id == "TEST-OLD-004")).scalar_one()
    assert old.superseded_by == "TEST-KHAC-9"


def test_tu_thay_the_chinh_no_tra_422(env):
    c, *_ = env
    r = post(c, "a.md", FRONTMATTER_MD.format(extra="thay_the: TEST-UP-001\n").encode(), MD)
    assert r.status_code == 422


def test_loi_giua_chung_thi_ban_cu_khong_bi_dong(env, monkeypatch):
    """Giao dịch: bản mới lỗi (embed hỏng) thì bản cũ phải còn nguyên, tệp đã lưu bị dọn, không audit."""
    c, db, _, folder = env
    add_doc(db, "TEST-OLD-005", effective_from=date(2025, 1, 1))

    class Boom:
        def embed(self, *_a, **_k):
            raise RuntimeError("model embedding hỏng")

    monkeypatch.setattr(kb_service, "get_embedder", lambda: Boom())
    r = post(c, "a.md", PLAIN_MD.encode(), MD, {**META, "supersedes": "TEST-OLD-005"})
    assert r.status_code == 500
    old = db.execute(select(Document).where(Document.doc_id == "TEST-OLD-005")).scalar_one()
    assert old.superseded_by is None and old.effective_to is None
    assert saved_files(folder) == [] and audit(db) == []


def test_chay_dua_cung_doc_id_tra_409_khong_phai_500(env, monkeypatch):
    c, db, _, folder = env
    real = kb_service.build_chunks

    def racing(data, ext, doc_id, title):
        add_doc(db, doc_id)  # "request kia" chen tài liệu cùng mã đúng lúc giữa kiểm trước và ghi
        return real(data, ext, doc_id, title)

    monkeypatch.setattr(kb_service, "build_chunks", racing)
    r = post(c, "SVT-TB-777-x.pdf", make_pdf(1), PDF, META)
    assert r.status_code == 409, r.text
    assert saved_files(folder) == []
    assert db.execute(select(Document).where(Document.doc_id == "SVT-TB-777")).scalars().all().__len__() == 1
