"""API /api/kb.

- Phần 1 (schema + hàm chuyển đổi): thuần Python, không cần Postgres hay HTTP.
- Phần 2 (endpoint): TestClient + dependency_overrides theo khuôn tests/test_ocr_api.py. Các test cần dữ liệu
  chạy trên Postgres thật trong transaction rollback (tests/kb_testkit.py); không có DB thì skip.
"""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.api.deps import UserInfo, get_db, get_legacy_user
from app.api.kb import (
    DocIdsIn,
    KbDocumentDetailOut,
    QuarantineIn,
    UploadMetaIn,
    file_kind_of,
    to_kb_document,
)
from app.main import create_app
from app.models import AuditLog, Document
from tests.kb_testkit import _kb_db, add_doc, add_employee, add_user  # noqa: F401  (_kb_db = fixture kb_db)

# Đúng các khoá của interface KbDocument trong portal/src/features/kb/types.ts (trừ statusNote, optional).
KB_DOCUMENT_KEYS = {
    "docId", "soHieu", "title", "docType", "fileKind", "department", "visibility", "allowedDepartments",
    "allowedRoles", "classified", "effectiveFrom", "effectiveTo", "supersedes", "supersededBy", "version",
    "status", "statusNote", "chunkCount", "ocrPages", "source", "uploadedBy", "createdAt",
}


def make_doc(**over) -> Document:
    """Document chưa qua DB: giá trị mặc định (default=...) của cột chỉ áp lúc flush nên phải điền tay."""
    fields = dict(
        doc_id="SVT-QC-003", so_hieu="01/2026/QĐ-SVT", title="Quy chế nghỉ phép (bản 2026)",
        doc_type="quy-che", source="data/knowledge/SVT-QC-003.md", department="HCNS",
        visibility="cong-khai", allowed_departments=[], allowed_roles=[], classification="thuong",
        effective_from=date(2026, 1, 1), effective_to=None, supersedes="SVT-QC-002", superseded_by=None,
        version="2", quarantined=False, ocr_pages=0, created_at=datetime(2026, 11, 14, 2, 42, tzinfo=UTC),
    )
    fields.update(over)
    return Document(**fields)


def wire(out) -> dict:
    """Dạng JSON mà FastAPI sẽ trả ra (response_model_by_alias mặc định = True)."""
    return out.model_dump(by_alias=True, mode="json")


# ---------------------------------------------------------------- to_kb_document

def test_to_kb_document_tai_lieu_thuong():
    out = to_kb_document(make_doc(), "lan.tran", 38)
    assert out.doc_id == "SVT-QC-003"
    assert out.status == "ready" and out.file_kind == "md" and out.classified is False
    assert out.chunk_count == 38 and out.uploaded_by == "lan.tran"
    assert out.supersedes == "SVT-QC-002"


def test_classified_chi_khi_classification_la_Mat():
    assert to_kb_document(make_doc(classification="Mat"), None, 1).classified is True
    assert to_kb_document(make_doc(classification="thuong"), None, 1).classified is False
    # chữ thường "mat" không phải "Mat": khớp đúng giá trị mà acl/ingest ghi, không đoán
    assert to_kb_document(make_doc(classification="mat"), None, 1).classified is False


def test_cach_ly_thanh_status_quarantined():
    assert to_kb_document(make_doc(quarantined=True), None, 5).status == "quarantined"
    assert to_kb_document(make_doc(quarantined=False), None, 5).status == "ready"


def test_nguoi_nap_va_cot_null():
    out = to_kb_document(make_doc(so_hieu=None, doc_type=None, version=None, effective_from=None), None, 0)
    assert out.uploaded_by is None  # tài liệu nạp từ thư mục data/knowledge, không có người upload
    assert out.so_hieu is None and out.doc_type is None and out.version is None
    assert out.effective_from is None and out.chunk_count == 0


def test_mang_null_trong_db_thanh_mang_rong():
    out = to_kb_document(make_doc(allowed_departments=None, allowed_roles=None, ocr_pages=None), None, 1)
    assert out.allowed_departments == [] and out.allowed_roles == [] and out.ocr_pages == 0


def test_visibility_la_giua_khong_lam_hong_ca_danh_sach():
    # Dòng hỏng phải hiện ra để admin thấy, không được làm 500 cả trang
    assert to_kb_document(make_doc(visibility="gia-tri-la"), None, 1).visibility == "gia-tri-la"


def test_json_camel_case_du_khoa_theo_types_ts():
    body = wire(to_kb_document(make_doc(classification="Mat", visibility="han-che",
                                        allowed_departments=["HCNS"], allowed_roles=["hr"]), "lan.tran", 41))
    assert set(body) == KB_DOCUMENT_KEYS
    assert body["docId"] == "SVT-QC-003" and body["chunkCount"] == 41 and body["uploadedBy"] == "lan.tran"
    assert body["allowedDepartments"] == ["HCNS"] and body["allowedRoles"] == ["hr"]
    assert body["effectiveFrom"] == "2026-01-01"  # ISO yyyy-mm-dd
    assert body["effectiveTo"] is None  # null có mặt, không bị bỏ khoá
    assert body["createdAt"].startswith("2026-11-14T02:42:00")  # ISO datetime kèm múi giờ


# ---------------------------------------------------------------- file_kind_of

@pytest.mark.parametrize("source,kind", [
    ("data/knowledge/a.md", "md"),
    ("data/uploads/ab12.PDF", "pdf"),
    ("data/uploads/ab12.docx", "docx"),
    ("x.png", "image"), ("x.JPG", "image"), ("x.jpeg", "image"), ("x.tiff", "image"),
    ("data/uploads/notes.txt", "other"),
    ("data/uploads/khong-co-duoi", "other"),
    ("data.v2/khong-co-duoi", "other"),  # dấu chấm ở thư mục không phải đuôi tệp
    ("C:\\data\\scan\\de-nghi.png", "image"),  # đường dẫn Windows
    ("", "other"),
])
def test_file_kind_of(source, kind):
    assert file_kind_of(source) == kind


# ---------------------------------------------------------------- request schema

def test_upload_meta_doc_camel_case_va_mac_dinh():
    meta = UploadMetaIn.model_validate_json(
        '{"docType": "quy-che", "department": "HCNS", "visibility": "han-che",'
        ' "allowedDepartments": ["HCNS"], "allowedRoles": ["hr"], "classified": true,'
        ' "effectiveFrom": "2026-02-01", "supersedes": "SVT-QC-002"}'
    )
    assert meta.doc_type == "quy-che" and meta.allowed_departments == ["HCNS"]
    assert meta.effective_from == date(2026, 2, 1) and meta.classified is True
    assert meta.title is None
    toi_thieu = UploadMetaIn.model_validate_json(
        '{"docType": "x", "department": "KD", "visibility": "cong-khai"}'
    )
    assert toi_thieu.allowed_departments == [] and toi_thieu.classified is False
    assert toi_thieu.supersedes is None


@pytest.mark.parametrize("bad", [
    '{"docType": "x", "department": "KD", "visibility": "bi-mat"}',  # phạm vi lạ
    '{"docType": "x", "department": "KD", "visibility": "cong-khai", "effectiveFrom": "01/02/2026"}',
    '{"department": "KD", "visibility": "cong-khai"}',  # thiếu docType
])
def test_upload_meta_sai_bi_tu_choi(bad):
    with pytest.raises(ValidationError):
        UploadMetaIn.model_validate_json(bad)


def test_doc_ids_va_quarantine_camel_case():
    assert DocIdsIn.model_validate_json('{"docIds": ["A", "B"]}').doc_ids == ["A", "B"]
    assert QuarantineIn.model_validate_json('{"on": true}').on is True
    with pytest.raises(ValidationError):
        DocIdsIn.model_validate_json('{"doc_ids_sai_ten": ["A"]}')


def test_detail_co_access_logged_mac_dinh_false():
    base = to_kb_document(make_doc(), None, 0)
    detail = KbDocumentDetailOut(**base.model_dump(), chunks=[], history=[])
    body = wire(detail)
    assert body["accessLogged"] is False and body["chunks"] == [] and body["history"] == []
    assert set(body) == KB_DOCUMENT_KEYS | {"chunks", "history", "accessLogged"}


# ================================================================ Phần 2: endpoint (bước 2: chỉ đọc)

class StubDb:
    """Chỉ để get_db không mở kết nối thật ở các test không đụng dữ liệu (401/403)."""


def as_user(role: str, db, user_id: int = 1):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    user = UserInfo(user_id, "test.admin", role, "CNTT", "Quản trị thử")
    app.dependency_overrides[get_legacy_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def api(kb_db):
    admin = add_user(kb_db)
    return as_user("admin", kb_db, admin.id), kb_db, admin


READ_ENDPOINTS = ["/api/kb/documents", "/api/kb/documents/X", "/api/kb/documents/X/access?email=a@b.vn"]


@pytest.mark.parametrize("path", READ_ENDPOINTS)
def test_chua_dang_nhap_401(path):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: StubDb()
    assert TestClient(app).get(path).status_code == 401


@pytest.mark.parametrize("role", ["staff", "manager"])
@pytest.mark.parametrize("path", READ_ENDPOINTS)
def test_khong_phai_admin_403(path, role):
    r = as_user(role, StubDb()).get(path)
    assert r.status_code == 403


def test_list_tra_camel_case_va_du_lieu(api):
    c, db, admin = api
    add_doc(db, "TEST-KB-L1", n_chunks=3, uploaded_by=admin.id, classification="Mat", quarantined=True)
    r = c.get("/api/kb/documents")
    assert r.status_code == 200
    mine = next(d for d in r.json() if d["docId"] == "TEST-KB-L1")
    assert set(mine) == KB_DOCUMENT_KEYS
    assert mine["chunkCount"] == 3 and mine["uploadedBy"] == "test.admin"
    assert mine["classified"] is True and mine["status"] == "quarantined" and mine["fileKind"] == "md"


def test_detail_404(api):
    c, _, _ = api
    r = c.get("/api/kb/documents/TEST-KB-KHONG-CO")
    assert r.status_code == 404
    assert c.get("/api/kb/documents/TEST-KB-KHONG-CO/access", params={"email": "a@b.vn"}).status_code == 404


def test_detail_tai_lieu_thuong_khong_co_dong_audit(api):
    c, db, _ = api
    add_doc(db, "TEST-KB-D1", n_chunks=2)
    before = db.execute(select(AuditLog).where(AuditLog.event == "kb_view_classified")).scalars().all()
    body = c.get("/api/kb/documents/TEST-KB-D1").json()
    assert [ch["ordinal"] for ch in body["chunks"]] == [0, 1]
    assert body["accessLogged"] is False and body["history"] == []
    after = db.execute(select(AuditLog).where(AuditLog.event == "kb_view_classified")).scalars().all()
    assert len(after) == len(before)


def test_detail_tai_lieu_mat_co_dung_mot_dong_audit(api):
    c, db, admin = api
    add_doc(db, "TEST-KB-D2", classification="Mat")
    r = c.get("/api/kb/documents/TEST-KB-D2")
    assert r.status_code == 200
    body = r.json()
    assert body["accessLogged"] is True and len(body["chunks"]) == 2
    assert body["history"][0]["by"] == "test.admin" and "Mật" in body["history"][0]["text"]
    logs = db.execute(select(AuditLog).where(AuditLog.event == "kb_view_classified")).scalars().all()
    mine = [x for x in logs if x.detail.get("doc_id") == "TEST-KB-D2"]
    assert len(mine) == 1 and mine[0].user_id == admin.id


def test_detail_mat_ghi_audit_hong_thi_500_va_khong_lo_chunk(api, monkeypatch):
    c, db, _ = api
    add_doc(db, "TEST-KB-D3", classification="Mat")
    db.commit()

    def boom(*_a, **_k):
        raise RuntimeError("audit hỏng")

    monkeypatch.setattr(db, "flush", boom)
    r = c.get("/api/kb/documents/TEST-KB-D3")
    assert r.status_code == 500
    assert "Nội dung đoạn" not in r.text  # fail closed: không chunk nào lọt ra


def test_access_endpoint(api):
    c, db, _ = api
    add_doc(db, "TEST-KB-P1", visibility="han-che", allowed_departments=["HCNS"], allowed_roles=["hr"])
    add_employee(db, "TSA01", "hr@test.invalid", department="HCNS", roles=["hr"], name="Thu Hà")
    add_employee(db, "TSA02", "kd@test.invalid", department="KD")
    ok = c.get("/api/kb/documents/TEST-KB-P1/access", params={"email": "hr@test.invalid"}).json()
    assert ok == {"allowed": True, "reason": "Thoả cả điều kiện phòng ban và vai trò", "person": "Thu Hà"}
    no = c.get("/api/kb/documents/TEST-KB-P1/access", params={"email": "kd@test.invalid"}).json()
    assert no["allowed"] is False and "thiếu" in no["reason"]
    # thiếu hoặc quá ngắn tham số email -> 422, không âm thầm coi là "không có trong danh bạ"
    assert c.get("/api/kb/documents/TEST-KB-P1/access").status_code == 422
    assert c.get("/api/kb/documents/TEST-KB-P1/access", params={"email": "a"}).status_code == 422


def test_route_da_dang_ky(api):
    c, _, _ = api
    paths = c.get("/openapi.json").json()["paths"]
    assert {"/api/kb/documents", "/api/kb/documents/{doc_id}", "/api/kb/documents/{doc_id}/access"} <= set(
        paths
    )
