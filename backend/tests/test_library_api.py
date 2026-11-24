"""GET /api/kb/library: chỉ thấy tài liệu MÌNH được xem (ADR-001), không rò cấu hình phân quyền.

Token Zitadel tự ký; DB thật qua transaction rollback. Tài liệu mẫu mang mã TEST-, mọi so sánh lọc theo q="TEST-"
(agent-db thật còn có tài liệu thật). Số đếm của facet được so theo mức tăng, không theo giá trị tuyệt đối.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.auth.oidc import get_verifier
from app.main import create_app
from tests.kb_testkit import _kb_db, add_doc, add_employee  # noqa: F401  (_kb_db = fixture kb_db)
from tests.oidc_testkit import Idp, bearer

TODAY = date.today()
DAY = timedelta(days=1)

KD = "test.kd@test.example"
ADM = "test.adm@test.example"


@pytest.fixture(name="env")
def _env(kb_db):
    idp = Idp()
    add_employee(kb_db, "TEST-KD", KD, department="KD", roles=["employee"])
    add_employee(kb_db, "TEST-ADM", ADM, department="CNTT", roles=["employee", "admin"])
    add_employee(kb_db, "TEST-NGHI", "test.nghi@test.example", department="KD", status="da-nghi-viec")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = idp.verifier
    c = TestClient(app, raise_server_exceptions=False)

    def get(email=KD, **params):
        r = c.get("/api/kb/library", headers=bearer(idp.token(email=email, sub=f"s-{email}")), params=params)
        return r

    return get, kb_db


def ids(r) -> list[str]:
    return [i["docId"] for i in r.json()["items"]]


def test_can_dang_nhap_va_la_nhan_vien_dang_lam(env):
    get, _ = env
    c = TestClient(create_app())
    assert c.get("/api/kb/library").status_code == 401
    assert get(email="test.la@test.example").status_code == 403  # chưa có trong danh bạ
    assert get(email="test.nghi@test.example").status_code == 403  # đã nghỉ việc


def test_chi_thay_tai_lieu_minh_duoc_xem_va_admin_khong_co_ngoai_le(env):
    get, db = env
    add_doc(db, "TEST-CK", visibility="cong-khai")
    add_doc(db, "TEST-PB-KD", visibility="phong-ban", allowed_departments=["KD"])
    add_doc(db, "TEST-PB-TC", visibility="phong-ban", allowed_departments=["TCKT"])
    add_doc(db, "TEST-HC-OK", visibility="han-che", allowed_departments=["KD"], allowed_roles=["employee"])
    add_doc(db, "TEST-HC-ROLE", visibility="han-che", allowed_departments=["KD"], allowed_roles=["hr"])
    add_doc(db, "TEST-HC-LOI", visibility="han-che")  # hạn chế mà không khai ai: cấu hình lỗi, không ai xem
    add_doc(db, "TEST-CACH-LY", visibility="cong-khai", quarantined=True)

    assert sorted(ids(get(q="TEST-"))) == ["TEST-CK", "TEST-HC-OK", "TEST-PB-KD"]
    # admin (phòng CNTT, không có vai trò hr): quyền quản trị không mở thêm tài liệu nào
    assert sorted(ids(get(email=ADM, q="TEST-"))) == ["TEST-CK"]


def test_khong_lo_cau_hinh_phan_quyen_nguon_va_noi_dung(env):
    get, db = env
    add_doc(
        db, "TEST-SECRET", visibility="phong-ban", allowed_departments=["KD"], allowed_roles=["hr"],
        source="data/uploads/abc123.pdf", uploaded_by="admin.that@saoviet.example",
    )
    r = get(q="TEST-SECRET")
    assert ids(r) == ["TEST-SECRET"]
    body = r.text
    for leaked in ("allowedDepartments", "allowedRoles", "visibility", "source", "uploadedBy", "abc123",
                   "admin.that@", "Nội dung đoạn", "chunks"):
        assert leaked not in body, leaked


def test_tai_lieu_mat_hien_kem_nhan_va_ma_thay_the_chi_hien_neu_xem_duoc(env):
    get, db = env
    add_doc(db, "TEST-MAT", visibility="cong-khai", classification="Mat")
    add_doc(db, "TEST-CU", visibility="cong-khai", superseded_by="TEST-MOI-AN")
    add_doc(db, "TEST-MOI", visibility="cong-khai", supersedes="TEST-CU")
    add_doc(db, "TEST-MOI-AN", visibility="phong-ban", allowed_departments=["TCKT"], supersedes="TEST-CU")
    by_id = {i["docId"]: i for i in get(q="TEST-").json()["items"]}
    assert by_id["TEST-MAT"]["classified"] is True and by_id["TEST-CU"]["classified"] is False
    assert by_id["TEST-MOI"]["supersedes"] == "TEST-CU"  # thấy cả hai đầu
    assert by_id["TEST-CU"]["supersededBy"] is None  # bản mới nằm ngoài quyền xem: không lộ mã
    assert "TEST-MOI-AN" not in by_id


def test_trang_thai_hieu_luc_theo_ngay_va_loc(env):
    get, db = env
    add_doc(db, "TEST-DANG", effective_from=TODAY - 30 * DAY)
    add_doc(db, "TEST-KHONG-NGAY")  # không ghi ngày: coi như đang hiệu lực
    add_doc(db, "TEST-HET", effective_from=TODAY - 90 * DAY, effective_to=TODAY - DAY)
    add_doc(db, "TEST-HET-HOM-NAY", effective_from=TODAY - 90 * DAY, effective_to=TODAY)  # hết hạn từ hôm nay
    add_doc(db, "TEST-SAP", effective_from=TODAY + 10 * DAY)
    add_doc(db, "TEST-BAT-DAU-HOM-NAY", effective_from=TODAY)
    st = {i["docId"]: i["status"] for i in get(q="TEST-").json()["items"]}
    assert st == {
        "TEST-DANG": "hieu-luc", "TEST-KHONG-NGAY": "hieu-luc", "TEST-BAT-DAU-HOM-NAY": "hieu-luc",
        "TEST-HET": "het-hieu-luc", "TEST-HET-HOM-NAY": "het-hieu-luc", "TEST-SAP": "chua-hieu-luc",
    }
    assert sorted(ids(get(q="TEST-", status="het-hieu-luc"))) == ["TEST-HET", "TEST-HET-HOM-NAY"]
    assert ids(get(q="TEST-", status="chua-hieu-luc")) == ["TEST-SAP"]
    # đang hiệu lực xếp trước, rồi chưa hiệu lực, hết hiệu lực xếp cuối
    order = ids(get(q="TEST-"))
    assert order.index("TEST-DANG") < order.index("TEST-SAP") < order.index("TEST-HET")
    assert get(status="khong-co").status_code == 422


def test_loc_theo_loai_phong_ban_va_tim_kiem(env):
    get, db = env
    add_doc(db, "TEST-A1", doc_type="quy-che", department="KD", title="Quy chế Ánh Dương", so_hieu="99/TEST-A")
    add_doc(db, "TEST-A2", doc_type="quy-trinh", department="CNTT", title="Quy trình Bình Minh")
    add_doc(db, "TESTXB", doc_type="quy-trinh", department="CNTT", title="Khác hẳn")
    assert ids(get(q="TEST-", type="quy-che")) == ["TEST-A1"]
    assert ids(get(q="TEST-", department="CNTT")) == ["TEST-A2"]
    assert ids(get(q="99/test-a")) == ["TEST-A1"]  # theo số hiệu, không phân biệt hoa thường
    assert ids(get(q="bình minh")) == ["TEST-A2"]
    assert ids(get(q="TEST_A1")) == []  # "_" là ký tự thường, không phải ký tự đại diện
    assert ids(get(q="TEST%")) == []


def test_facet_chi_tinh_tren_tap_duoc_xem(env):
    get, db = env
    before = get().json()
    add_doc(db, "TEST-F1", doc_type="loai-test-hien", department="PB-TEST-HIEN", visibility="cong-khai")
    add_doc(db, "TEST-F2", doc_type="loai-test-hien", department="PB-TEST-HIEN", visibility="cong-khai")
    add_doc(db, "TEST-F3", doc_type="loai-test-an", department="PB-TEST-AN", visibility="phong-ban",
            allowed_departments=["TCKT"])
    after = get().json()
    types = {f["value"]: f["count"] for f in after["docTypes"]}
    depts = {f["value"]: f["count"] for f in after["departments"]}
    assert types["loai-test-hien"] == 2 and depts["PB-TEST-HIEN"] == 2
    assert "loai-test-an" not in types and "PB-TEST-AN" not in depts  # không lộ rằng có tài liệu ẩn
    assert after["totalVisible"] == before["totalVisible"] + 2
    assert sum(f["count"] for f in after["statuses"]) == after["totalVisible"]
    # lọc không làm đổi facet
    filtered = get(q="TEST-F1").json()
    assert filtered["totalVisible"] == after["totalVisible"] and len(filtered["items"]) == 1
