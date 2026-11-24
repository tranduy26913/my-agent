"""app/rag/kb_service.py trên Postgres thật (rollback sau mỗi test, xem tests/kb_testkit.py).

Bước 2: đọc danh sách, chi tiết (kèm ngoại lệ tài liệu Mật + audit), kiểm tra quyền đọc.
"""

from datetime import date

import pytest

from app.models import AuditLog
from app.rag.kb_service import DocNotFound, check_access, get_detail, get_row, history_text, list_documents
from tests.kb_testkit import ADMIN_EMAIL, _kb_db, add_doc, add_employee, audit_since_start  # noqa: F401  (_kb_db = fixture kb_db)

TODAY = date(2026, 11, 23)


def audit_rows(db, event="kb_view_classified"):
    return audit_since_start(db, event)


# ---------------------------------------------------------------- history_text (thuần)

def test_history_text():
    assert history_text("kb_quarantine", {"on": True}) == "Cách ly tài liệu"
    assert history_text("kb_quarantine", {"on": False}) == "Bỏ cách ly tài liệu"
    assert "Mật" in history_text("kb_view_classified", {})
    assert history_text("kb_la_hoac", {}) == "kb_la_hoac"  # sự kiện lạ vẫn hiện, không giấu


# ---------------------------------------------------------------- danh sách / một dòng

def test_list_documents_co_username_va_so_chunk(kb_db):
    add_doc(kb_db, "TEST-KB-A", n_chunks=3, uploaded_by="test.lan@cty-a.example")
    add_doc(kb_db, "TEST-KB-B", n_chunks=0)
    rows = {r.document.doc_id: r for r in list_documents(kb_db)}
    assert rows["TEST-KB-A"].chunk_count == 3 and rows["TEST-KB-A"].username == "test.lan@cty-a.example"
    assert rows["TEST-KB-B"].chunk_count == 0 and rows["TEST-KB-B"].username is None


def test_list_documents_la_mot_truy_van(kb_db):
    """Không N+1: số câu SQL không tăng theo số tài liệu."""
    from sqlalchemy import event

    for i in range(5):
        add_doc(kb_db, f"TEST-KB-N{i}", n_chunks=2)
    seen = []
    engine = kb_db.get_bind().engine
    event.listen(engine, "before_cursor_execute", lambda *a: seen.append(a[2]))
    list_documents(kb_db)
    assert len([q for q in seen if q.lstrip().upper().startswith("SELECT")]) == 1  # bỏ qua SAVEPOINT


def test_get_row_khong_co_thi_not_found(kb_db):
    with pytest.raises(DocNotFound):
        get_row(kb_db, "TEST-KB-KHONG-CO")


# ---------------------------------------------------------------- chi tiết + tài liệu Mật (ADR-004 mục 4)

def test_detail_tai_lieu_thuong_khong_ghi_audit(kb_db):
    add_doc(kb_db, "TEST-KB-T", n_chunks=3)
    before = len(audit_rows(kb_db))
    d = get_detail(kb_db, "TEST-KB-T", ADMIN_EMAIL)
    assert [c.ordinal for c in d.chunks] == [0, 1, 2]
    assert d.access_logged is False and d.row.chunk_count == 3
    assert len(audit_rows(kb_db)) == before


def test_detail_tai_lieu_mat_ghi_dung_mot_dong_audit(kb_db):
    add_doc(kb_db, "TEST-KB-M", n_chunks=2, classification="Mat")
    before = len(audit_rows(kb_db))
    d = get_detail(kb_db, "TEST-KB-M", ADMIN_EMAIL)

    rows = audit_rows(kb_db)[before:]
    assert len(rows) == 1
    assert rows[0].detail["actor"] == ADMIN_EMAIL and rows[0].detail["doc_id"] == "TEST-KB-M"
    assert d.access_logged is True and len(d.chunks) == 2
    # lượt xem hiện ngay trong lịch sử của tài liệu, kèm tên người xem
    assert d.history[0].by == ADMIN_EMAIL and "Mật" in d.history[0].text

    get_detail(kb_db, "TEST-KB-M", ADMIN_EMAIL)  # mỗi lượt xem là một dòng
    assert len(audit_rows(kb_db)) == before + 2


def test_detail_mat_ghi_log_loi_thi_khong_tra_chunk(kb_db, monkeypatch):
    """Fail closed: ghi audit hỏng thì không đọc, không trả chunk nào."""
    add_doc(kb_db, "TEST-KB-F", classification="Mat")
    kb_db.commit()  # chốt dữ liệu mẫu để get_row không phải flush

    calls = []
    real_execute = kb_db.execute
    monkeypatch.setattr(kb_db, "execute", lambda *a, **k: (calls.append(1), real_execute(*a, **k))[1])

    def boom(*_a, **_k):
        raise RuntimeError("không ghi được audit")

    monkeypatch.setattr(kb_db, "flush", boom)
    with pytest.raises(RuntimeError):
        get_detail(kb_db, "TEST-KB-F", ADMIN_EMAIL)
    assert len(calls) == 1  # chỉ get_row; truy vấn chunk không bao giờ chạy


def test_history_chi_lay_su_kien_kb_cua_dung_tai_lieu(kb_db):
    add_doc(kb_db, "TEST-KB-H1")
    add_doc(kb_db, "TEST-KB-H2")
    kb_db.add_all([
        AuditLog(
            user_id=None, event="kb_quarantine",
            detail={"doc_id": "TEST-KB-H1", "on": True, "actor": ADMIN_EMAIL},
        ),
        AuditLog(user_id=None, event="kb_upload", detail={"doc_id": "TEST-KB-H1"}),
        AuditLog(user_id=None, event="kb_reindex", detail={"doc_id": "TEST-KB-H2"}),  # tài liệu khác
        AuditLog(user_id=None, event="ocr_run", detail={"doc_id": "TEST-KB-H1"}),  # không phải sự kiện kb
    ])
    kb_db.flush()
    h = get_detail(kb_db, "TEST-KB-H1", ADMIN_EMAIL).history
    assert [x.text for x in h] == ["Nạp tài liệu vào kho", "Cách ly tài liệu"]  # mới nhất trước
    assert h[0].by == "hệ thống" and h[1].by == ADMIN_EMAIL


# ---------------------------------------------------------------- kiểm tra quyền đọc (dùng lại can_read)

def who(db, email, doc_id="TEST-KB-ACC"):
    return check_access(db, doc_id, email, today=TODAY)


def test_access_email_la_va_nghi_viec(kb_db):
    add_doc(kb_db, "TEST-KB-ACC", visibility="cong-khai")
    add_employee(kb_db, "TST01", "cu@test.invalid", status="da-nghi-viec", name="Hoàng Văn Cũ")
    r = who(kb_db, "khong-co@test.invalid")
    assert (r.allowed, r.person) == (False, None) and "danh bạ" in r.reason
    r = who(kb_db, "cu@test.invalid")
    assert r.allowed is False and "nghỉ việc" in r.reason and r.person == "Hoàng Văn Cũ"


def test_access_email_khong_phan_biet_hoa_thuong(kb_db):
    add_doc(kb_db, "TEST-KB-ACC", visibility="cong-khai")
    add_employee(kb_db, "TST02", "Lan@Test.Invalid")
    assert who(kb_db, "  lan@test.invalid ").allowed is True


def test_access_phong_ban_theo_phong_hoac_vai_tro(kb_db):
    add_doc(kb_db, "TEST-KB-ACC", visibility="phong-ban", allowed_departments=["HCNS"],
            allowed_roles=["manager"])
    add_employee(kb_db, "TST03", "a@test.invalid", department="HCNS")
    add_employee(kb_db, "TST04", "b@test.invalid", department="KD", roles=["manager"])
    add_employee(kb_db, "TST05", "c@test.invalid", department="KD", roles=["employee"])
    assert "Thuộc phòng HCNS" in who(kb_db, "a@test.invalid").reason
    assert who(kb_db, "b@test.invalid").allowed is True
    r = who(kb_db, "c@test.invalid")
    assert r.allowed is False and "Phòng KD" in r.reason


def test_access_han_che_can_ca_phong_lan_vai_tro(kb_db):
    add_doc(kb_db, "TEST-KB-ACC", visibility="han-che", classification="Mat",
            allowed_departments=["HCNS", "BGD"], allowed_roles=["hr", "executive"])
    add_employee(kb_db, "TST06", "hr@test.invalid", department="HCNS", roles=["hr"])
    add_employee(kb_db, "TST07", "nv@test.invalid", department="HCNS", roles=["employee"])
    add_employee(kb_db, "TST08", "ad@test.invalid", department="CNTT", roles=["admin"])
    assert who(kb_db, "hr@test.invalid").allowed is True
    r = who(kb_db, "nv@test.invalid")  # cùng phòng nhưng thiếu vai trò
    assert r.allowed is False and "vai trò" in r.reason and "phòng ban phù hợp" not in r.reason
    r = who(kb_db, "ad@test.invalid")  # admin không có ngoại lệ (ADR-001)
    assert r.allowed is False and "phòng ban phù hợp" in r.reason and "vai trò phù hợp" in r.reason


def test_access_han_che_cau_hinh_loi(kb_db):
    add_employee(kb_db, "TST09", "x@test.invalid", roles=["executive"])
    add_doc(kb_db, "TEST-KB-ACC", visibility="han-che", allowed_departments=[], allowed_roles=[])
    assert "cấu hình lỗi" in who(kb_db, "x@test.invalid").reason


def test_access_pham_vi_la_bi_tu_choi(kb_db):
    add_doc(kb_db, "TEST-KB-ACC", visibility="gia-tri-la")
    add_employee(kb_db, "TST10", "y@test.invalid")
    r = who(kb_db, "y@test.invalid")
    assert r.allowed is False and "gia-tri-la" in r.reason


def test_access_cach_ly_va_ngay_hieu_luc(kb_db):
    add_employee(kb_db, "TST11", "z@test.invalid")
    add_doc(kb_db, "TEST-KB-Q", quarantined=True)
    add_doc(kb_db, "TEST-KB-FUT", effective_from=date(2026, 12, 1))
    assert "cách ly" in who(kb_db, "z@test.invalid", "TEST-KB-Q").reason
    assert "chưa đến ngày hiệu lực" in who(kb_db, "z@test.invalid", "TEST-KB-FUT").reason


def test_access_het_hieu_luc_dung_bien(kb_db):
    add_employee(kb_db, "TST12", "w@test.invalid")
    add_doc(kb_db, "TEST-KB-ACC", effective_from=date(2026, 1, 1), effective_to=TODAY)
    r = who(kb_db, "w@test.invalid")  # effective_to > today mới còn hiệu lực (như retriever.in_force_sql)
    assert r.allowed is False and "hết hiệu lực" in r.reason and "23/11/2026" in r.reason


def test_access_cong_khai_con_hieu_luc(kb_db):
    add_doc(kb_db, "TEST-KB-ACC", effective_from=TODAY, effective_to=date(2027, 1, 1))
    add_employee(kb_db, "TST13", "v@test.invalid", name="Võ Văn V")
    r = who(kb_db, "v@test.invalid")
    assert r.allowed is True and r.person == "Võ Văn V"


def test_access_tai_lieu_khong_co(kb_db):
    with pytest.raises(DocNotFound):
        check_access(kb_db, "TEST-KB-KHONG-CO", "a@test.invalid")
